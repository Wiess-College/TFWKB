#!/usr/bin/env python3
"""Check that the web addresses the site cites still answer.

Citations point at pages on other sites, and those pages move or disappear without notice. A dead
citation looks fine on the site until a reader follows it, so this script asks every cited address
whether it still answers. GitHub Actions runs it once a month (.github/workflows/check-links.yml).
That workflow uploads the report only when nothing failed, because a failing step skips the steps after it.

It reads the url and parts: of every entry in sources/bibliography/*.yaml, and every [@wb ...],
[@portal ...] and [@rhc ...] citation in the Markdown pages under docs/, and works out the address each
one points to. Each distinct address is checked once, in that order, one request a second with a
20-second timeout, and is reported under the first place it was found: "bib:<key>" for a
bibliography entry, or the page's path from the repo root. A Wayback Machine capture is checked through
the Wayback availability API, so passing means the Wayback Machine has a capture of that address, not
merely that the Wayback Machine is up. Any other address is requested with HEAD, or with GET if the host
refuses HEAD with 403 or 405, and passes if it answers below 400 after following redirects.

It writes no file unless --report names one. It prints "<n> distinct links to check" and
"<n> failures of <n>" on stderr, and one line on stdout for each address that failed:

    FAIL <status>  <where it was found>  <address, or Wayback timestamp and address>

Run it from anywhere. It needs network, and PyYAML, which requirements.txt installs for the site.

    python3 tools/check_links.py                    print failures
    python3 tools/check_links.py --report out.md    also write every result to out.md, as a Markdown table
    python3 tools/check_links.py --limit 20         check only the first 20 addresses

The status of each address is one of these:

    200, 404, 500, ...          the HTTP status after redirects; below 400 passes
    capture <timestamp>         the Wayback Machine's capture closest to the cited timestamp, which may be
                                years away from it; passes
    NO CAPTURE                  the availability API offered no capture of the address; fails
    error: <exception name>     no answer, recorded as a failure: TimeoutError or URLError (timeout,
                                unknown host, refused connection); HTTPError when the GET after a
                                refused HEAD, or the availability API itself, answers with an error

Exit status is 1 if any address failed and 0 if none did. A network failure does not stop the run; it
is recorded as a failed address. The report is written only after every address has been checked, so a
run that stops, or is interrupted, leaves no report and nothing to clean up. These, among others, stop
it with a Python traceback before anything is checked: a YAML syntax error, a bibliography entry with a
url or parts but no key (KeyError), a part with no url (TypeError), PyYAML not installed (ImportError),
or a page that is not UTF-8. A --limit that is not a whole number stops it with a usage message and exit
status 2. A --report file that cannot be written stops it with a traceback after every address has been
checked.

What this checks is not always what a reader's link opens. hooks/citations.py builds the links, and:

    the site sends a reader to the Wayback Machine (web.archive.org/web/2/<address>) for any address
    outside the archives it links directly (on_page_content in the hook); this script checks the live address.
    citations inside ``` code fences are examples, which the site leaves as text; this script checks them.
    for [@portal <ark id> ...] this script finds a page number anywhere in the citation, including the 27
    in "pp.27"; the hook reads "p.N" only as its own word after the ark id.
    for [@rhc <date> <slug>] this script takes the whole next word as the slug; the hook reads it only as
    far as its lower-case letters, digits and hyphens go, and links the blog as a whole if there are none.

Only the citations above are read. Plain links in pages, and [@woodson ...], are not checked. A
bibliography url containing "*" (a Wayback listing of many captures) is skipped, but a part's url is
not. A negative --limit drops that many addresses from the end of the list instead of checking none. A
redirect loop, or a redirect with no address to go to, shows as its 3xx status and passes.
"""

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import NamedTuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIBLIOGRAPHY_FILES_GLOB = os.path.join(REPO_ROOT, "sources", "bibliography", "*.yaml")
PAGE_FILES_GLOB = os.path.join(REPO_ROOT, "docs", "**", "*.md")

# Sent with every request, so a site's owner can see who is checking and where to find out more.
USER_AGENT = "familykb-link-check/1.0 (+https://github.com/Wiess-College/TFWKB)"
TIMEOUT_SECONDS = 20
SECONDS_BETWEEN_REQUESTS = 1.0  # one request a second, to stay polite to small sites and the Wayback Machine

WAYBACK_AVAILABILITY_API_URL = "https://archive.org/wayback/available"

# A Wayback Machine address in the bibliography: https://web.archive.org/web/<timestamp>[id_]/<original url>.
# "id_" asks for the capture's original bytes, without the Wayback toolbar; the availability check ignores it.
WAYBACK_URL_PATTERN = re.compile(r"https://web\.archive\.org/web/(?P<timestamp>\d{4,14})(?:id_)?/(?P<original_url>.*)$")

# A short-form citation in a page: "[@", the prefix, whitespace, then everything up to the closing "]".
# The locator may run over several lines.
SHORT_CITATION_PATTERN = re.compile(r"\[@(?P<prefix>wb|portal|rhc)\s+(?P<locator>[^\]]+)\]")

# A page locator such as "p.84", "p 84" or "p84", searched for anywhere in a Portal citation.
PAGE_LOCATOR_PATTERN = re.compile(r"p\.?\s*(?P<page_number>\d+)")

# The date that starts a Rice History Corner citation, [@rhc YYYY-MM-DD <slug>].
POST_DATE_PATTERN = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})$")


class WaybackCapture(NamedTuple):
    """One cited Wayback Machine capture: when it was taken, and of what address."""

    timestamp: str  # as cited, normally 4 to 14 digits of YYYYMMDDhhmmss
    original_url: str  # the address on the live web that was captured


class LinkToCheck(NamedTuple):
    """One distinct cited address, and the first place it was found."""

    cited_in: str  # "bib:<key>" for a bibliography entry, or the page's path from the repo root, "docs/..."
    target: str | WaybackCapture  # a capture is checked through the Wayback API; a plain address directly


class CheckResult(NamedTuple):
    """What checking one address found."""

    link: LinkToCheck
    passed: bool  # the address answered below 400, or the Wayback Machine has a capture of it
    status: str  # as printed: "200", "404", "capture 20020107020729", "NO CAPTURE", "error: URLError", ...


def main(arguments: list[str]) -> None:
    """Check every cited address, print the failures, write the report if asked, and exit 1 if any failed."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--report")
    parser.add_argument("--limit", type=int, default=0)
    options = parser.parse_args(arguments)

    links = collect_links_to_check()
    if options.limit:
        links = links[: options.limit]
    print(f"{len(links)} distinct links to check", file=sys.stderr)

    results = check_every_link(links)
    if options.report:
        write_report(options.report, results)

    failure_count = count_failures(results)
    print(f"{failure_count} failures of {len(links)}", file=sys.stderr)
    sys.exit(1 if failure_count else 0)


def collect_links_to_check() -> list[LinkToCheck]:
    """Return every distinct cited address, bibliography entries first, each with where it was first found."""
    links = collect_bibliography_links() + collect_page_links()
    return remove_repeated_targets(links)


def collect_bibliography_links() -> list[LinkToCheck]:
    """Return the url and every part's url of each bibliography entry, in file-name order."""
    # Imported here rather than at the top so that --help and argument errors work without PyYAML.
    import yaml

    links = []
    for bibliography_file in sorted(glob.glob(BIBLIOGRAPHY_FILES_GLOB)):
        with open(bibliography_file) as bibliography:  # locale encoding; UTF-8 would be a separate fix
            entries = yaml.safe_load(bibliography) or []
        for entry in entries:
            entry_url = entry.get("url")
            if entry_url and "*" not in entry_url:
                target = find_url_target(entry_url)
                links.append(LinkToCheck(f"bib:{entry['key']}", target))
            for part_url in (entry.get("parts") or {}).values():
                target = find_url_target(part_url)
                links.append(LinkToCheck(f"bib:{entry['key']}", target))
    return links


def find_url_target(url: str) -> str | WaybackCapture:
    """Return the capture a Wayback Machine address points to, or any other address unchanged."""
    wayback_url = WAYBACK_URL_PATTERN.match(url)
    if wayback_url:
        return WaybackCapture(wayback_url["timestamp"], wayback_url["original_url"])
    return url


def collect_page_links() -> list[LinkToCheck]:
    """Return the address of every [@wb], [@portal] and [@rhc] citation in docs/, page by page in path order.

    Citations missing their parts, such as "[@wb" with a timestamp but no address, are skipped.
    """
    links = []
    for page_file in sorted(glob.glob(PAGE_FILES_GLOB, recursive=True)):
        page_repo_path = os.path.relpath(page_file, REPO_ROOT)
        with open(page_file, encoding="utf-8") as page:
            page_text = page.read()
        for citation in SHORT_CITATION_PATTERN.finditer(page_text):
            target = find_citation_target(citation["prefix"], citation["locator"])
            if target is not None:
                links.append(LinkToCheck(page_repo_path, target))
    return links


def find_citation_target(prefix: str, locator: str) -> str | WaybackCapture | None:
    """Return the address or capture a short-form citation points to, or None if it is missing parts."""
    locator_words = locator.split()
    if prefix == "wb" and len(locator_words) >= 2:
        timestamp, original_url, *_notes = locator_words
        return WaybackCapture(timestamp, original_url)
    if prefix == "portal" and locator_words:
        return build_portal_url(locator)
    if prefix == "rhc" and len(locator_words) >= 2:
        return build_history_corner_url(locator_words)
    return None


def build_portal_url(locator: str) -> str:
    """Return the Portal to Texas History address for "<ark id> [p.N]", at page N if one is given."""
    ark_id, *_rest = locator.split()
    page_locator = PAGE_LOCATOR_PATTERN.search(locator)
    page_suffix = f"m1/{page_locator['page_number']}/" if page_locator else ""
    return f"https://texashistory.unt.edu/ark:/67531/{ark_id}/" + page_suffix


def build_history_corner_url(locator_words: list[str]) -> str | None:
    """Return the Rice History Corner post address for "<YYYY-MM-DD> <slug> ...", or None if there is no date."""
    date_word, slug, *_notes = locator_words
    post_date = POST_DATE_PATTERN.match(date_word)
    if not post_date:
        return None
    return f"https://ricehistorycorner.com/{post_date['year']}/{post_date['month']}/{post_date['day']}/{slug}/"


def remove_repeated_targets(links: list[LinkToCheck]) -> list[LinkToCheck]:
    """Return the links with each address or capture kept only where it was first found."""
    seen_targets = set()
    distinct_links = []
    for link in links:
        if link.target not in seen_targets:
            seen_targets.add(link.target)
            distinct_links.append(link)
    return distinct_links


def check_every_link(links: list[LinkToCheck]) -> list[CheckResult]:
    """Check each address in turn, printing each failure as it is found, and return the results in order."""
    results = []
    for link in links:
        passed, status = check_link(link.target)
        results.append(CheckResult(link, passed, status))
        if not passed:
            print(f"FAIL {status:14} {link.cited_in}  {format_target(link.target)}")
        time.sleep(SECONDS_BETWEEN_REQUESTS)
    return results


def check_link(target: str | WaybackCapture) -> tuple[bool, str]:
    """Return whether one address or capture passes, and the status to show for it."""
    # Anything that goes wrong, including an answer that is not the JSON expected, is recorded as a
    # failure with the exception's name, so one bad address cannot stop the run.
    try:
        if isinstance(target, WaybackCapture):
            capture_exists, closest_timestamp = find_closest_capture(target)
            return capture_exists, f"capture {closest_timestamp}" if capture_exists else "NO CAPTURE"
        status_code = fetch_status_code(target)
        return status_code < 400, str(status_code)
    except Exception as error:
        return False, f"error: {error.__class__.__name__}"


def find_closest_capture(capture: WaybackCapture) -> tuple[bool, str | None]:
    """Ask the Wayback availability API for a capture near the cited one; return whether there is one, and its time.

    The API answers with the single capture closest to the timestamp, which need not be the cited
    capture itself.
    """
    api_url = (
        f"{WAYBACK_AVAILABILITY_API_URL}?url={urllib.parse.quote(capture.original_url, safe='')}"
        f"&timestamp={capture.timestamp}"
    )
    request = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        availability = json.load(response)
    closest = availability.get("archived_snapshots", {}).get("closest")
    return bool(closest and closest.get("available")), (closest or {}).get("timestamp")


def fetch_status_code(url: str) -> int:
    """Return the HTTP status a HEAD request for the address gets, after following redirects.

    Some hosts refuse HEAD with 403 or 405, so those are asked again with GET. An error status from
    that GET is not returned; it raises HTTPError, which shows as "error: HTTPError".
    """
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status
    except urllib.error.HTTPError as error:
        if error.code in (403, 405):
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return response.status
        return error.code


def write_report(report_file: str, results: list[CheckResult]) -> None:
    """Write every result to the report file as a Markdown table, under today's date and a count of failures.

    report_file is the path given to --report, relative to the folder the script is run from. An
    existing file is replaced.
    """
    rows = [
        f"| {'ok' if result.passed else 'FAIL'} | {result.status} | `{result.link.cited_in}` |"
        f" {format_target(result.link.target)} |"
        for result in results
    ]
    with open(report_file, "w") as report:  # locale encoding; UTF-8 would be a separate fix
        report.write(
            f"# Link check {time.strftime('%Y-%m-%d')}\n\n{len(results)} links, {count_failures(results)} failures\n\n"
        )
        report.write("| result | status | cited in | target |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")


def format_target(target: str | WaybackCapture) -> str:
    """Return an address as it is, or a capture as "<timestamp> <address>", for the failure lines and the report."""
    if isinstance(target, WaybackCapture):
        return f"{target.timestamp} {target.original_url}"
    return target


def count_failures(results: list[CheckResult]) -> int:
    """Return how many of the results failed."""
    return sum(1 for result in results if not result.passed)


if __name__ == "__main__":
    main(sys.argv[1:])
