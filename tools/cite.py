#!/usr/bin/env python3
"""Turn a corpus path into a citation, or a citation into a URL.

Pages cite the archived web corpus with short forms such as [@wb timestamp url], which
hooks/citations.py turns into links at build time. Working the timestamp and original URL out of a
mirrored file name by hand is slow and easy to get wrong, and so is checking where a citation will
link. This script does both. It works citations out from corpus paths by their names alone (the
files need not be present). For --url it reads what the hook reads, sources/bibliography/*.yaml and
sources/portal-issue-dates.tsv. It writes no files; each result is printed on its own line.

Give it one or more corpus paths to get the citation for each:

    python3 tools/cite.py teamwiess.com/mirror/teamwiess.com/traditions/20140711230531__index.html
      → [@wb 20140711230531 http://teamwiess.com/traditions/index.html]
    python3 tools/cite.py riceinfo.rice.edu-wiess/text/traditions__ubangee.html__20020107020729.md
      → [@wb 20020107020729 http://riceinfo.rice.edu/projects/colleges/wiess/traditions/ubangee.html]

Give it --url and one citation to get the address its link opens:

    python3 tools/cite.py --url "[@wb 20020107020729 http://riceinfo.rice.edu/...]"
      → https://web.archive.org/web/20020107020729/http://riceinfo.rice.edu/...
    python3 tools/cite.py --url "[@oweek-2006 p.84]"       (looks the key up in sources/bibliography/)

--url gives exactly the address the citation links to on the site, because it imports
hooks/citations.py and uses the hook's own rules and data rather than a copy of them. Change the rules
there. (The site then sends every link outside an archive through the Wayback Machine, as
https://web.archive.org/web/2/<address>; the address printed here is the one before that step.)

Corpus paths are relative to the corpus folder. Anything up to and including "/corpus/" or
"wiess-archive/" is dropped, so a full path on disk works too; a path that starts with "corpus/" is not
trimmed, so write "./corpus/". Mirrored pages are <site>/mirror/<host>/<folders>/<timestamp>__<file name>;
riceinfo text files are <section>__<page>.html__<timestamp>.md under riceinfo.rice.edu-wiess/text/ (or
rice.edu-projects-wiess/text/).

Since it writes nothing, a failed run leaves nothing to clean up. A path or key it does not recognise
is not an error: that line of output reads "(no rule for ...)" or "(unknown key ...)". A bibliography
entry with no url reads "(no url; local: ...)", naming its copy in the corpus. A citation the site
would warn about, such as "@wb" with a timestamp but no URL, prints the site's warning and stops with
exit status 1; so does --url with no citation, or with text that is not one ("not a citation: ...").
--url needs PyYAML, which requirements.txt installs for the site; corpus paths need nothing beyond
Python.
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIBLIOGRAPHY_FILES_GLOB = os.path.join(REPO_ROOT, "sources", "bibliography", "*.yaml")

# Where each riceinfo text folder's pages lived on the live web, before the section and page name.
RICEINFO_BASE_URL_BY_SITE = {
    "riceinfo.rice.edu-wiess": "http://riceinfo.rice.edu/projects/colleges/wiess",
    "rice.edu-projects-wiess": "http://www.rice.edu/projects/colleges/wiess",
}

# A Wayback mirror file: <site>/mirror/<host>/<folders>/<14-digit timestamp>__<file name>.
MIRROR_FILE_PATTERN = re.compile(
    r"^(?P<site>[^/]+)/mirror/"
    r"(?P<host>[^/]+)/"
    r"(?P<folders>.*?)"  # zero or more "folder/" parts, kept with their slashes
    r"(?P<timestamp>\d{14})__"
    r"(?P<file_name>[^/]+)$"
)

# A riceinfo text file: <site>/text/<section>__<page>.html__<timestamp>.md. "__" separates folders in
# the page name; the timestamp is always the last "__" part, just before ".md".
RICEINFO_TEXT_PATTERN = re.compile(
    r"^(?P<site>riceinfo\.rice\.edu-wiess|rice\.edu-projects-wiess)/text/"
    r"(?P<page_name>.+?)__"
    r"(?P<timestamp>\d{14})\.md$"
)

# An O-Week book page or text file, whose year is all a citation can be built from.
OWEEK_BOOK_PATTERN = re.compile(r"^teamwiess\.com/oweek-books/(?:text(?:-raw)?/)?(?P<year>\d{4})-oweek")

# A saved Rice History Corner post: posts/YYYY-MM-DD_<slug>.md.
RICE_HISTORY_CORNER_PATTERN = re.compile(
    r"^ricehistorycorner\.com/posts/(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})_(?P<slug>.+?)\.md$"
)

# A page locator such as "p.84", "p 84" or "p84", searched for anywhere in the citation.
PAGE_LOCATOR_PATTERN = re.compile(r"p\.?\s*(?P<page_number>\d+)")


def main(arguments: list[str]) -> None:
    """Print the usage, the URL for one citation, or a citation for each corpus path."""
    if not arguments:
        print(__doc__)
        sys.exit(0)
    if arguments[0] == "--url":
        print(find_citation_url(" ".join(arguments[1:])))
    else:
        for corpus_path in arguments:
            print(cite_corpus_path(corpus_path))


def find_citation_url(citation: str) -> str:
    """Return the address a citation links to on the site, or "(unknown key ...)" if nothing defines its key.

    The citation may leave out its square brackets and its "@". The address comes from
    hooks/citations.py's resolve_citation, with the bibliography and Portal issue dates loaded the way
    the hook loads them when the site builds. A bibliography entry with no url gives
    "(no url; local: ...)", naming its copy in the corpus.
    """
    # Imported here so that corpus paths work without PyYAML, which the hook needs.
    sys.path.insert(0, os.path.join(REPO_ROOT, "hooks"))
    import citations

    citation_body = citation.strip().strip("[]")
    if not citation_body.startswith("@"):
        citation_body = "@" + citation_body
    citation_match = citations.CITATION_PATTERN.fullmatch(f"[{citation_body}]")
    if citation_match is None:
        sys.exit(f"not a citation: {citation!r}")
    citation_key = citation_match["key"]

    citations.load_citation_sources()
    if citation_key not in citations.BIBLIOGRAPHY and citation_key not in citations.RESOLVER_BY_RULE_KEY:
        return f"(unknown key {citation_key})"
    resolved = citations.resolve_citation(citation_match, "cite.py --url")
    if not resolved.found:
        sys.exit(1)  # malformed; the hook has printed its warning, such as "bad Wayback citation ..."
    if resolved.url:
        return resolved.url
    return f"(no url; local: {citations.BIBLIOGRAPHY[citation_key].get('local')})"


def cite_corpus_path(corpus_path: str) -> str:
    """Return the citation for a corpus file, or "(no rule for ...)" if its folder has no rule here.

    A Rice History Corner post gets its citation followed by the post's live address, since those
    posts are cited by date and slug rather than by a Wayback capture. An O-Week book gets "p.N" for
    the editor to replace with the page number.
    """
    corpus_path = corpus_path.replace("\\", "/")
    corpus_path = re.sub(r"^.*?/corpus/", "", corpus_path)
    corpus_path = re.sub(r"^.*?wiess-archive/", "", corpus_path)

    mirror_file = MIRROR_FILE_PATTERN.match(corpus_path)
    if mirror_file:
        original_url = f"http://{mirror_file['host']}/{mirror_file['folders']}{mirror_file['file_name']}"
        return f"[@wb {mirror_file['timestamp']} {original_url}]"

    riceinfo_text = RICEINFO_TEXT_PATTERN.match(corpus_path)
    if riceinfo_text:
        page_subpath = riceinfo_text["page_name"].replace("__", "/")  # relative to the site's base URL
        base_url = RICEINFO_BASE_URL_BY_SITE[riceinfo_text["site"]]
        return f"[@wb {riceinfo_text['timestamp']} {base_url}/{page_subpath}]"

    oweek_book = OWEEK_BOOK_PATTERN.match(corpus_path)
    if oweek_book:
        return f"[@oweek-{oweek_book['year']} p.N]"

    history_corner_post = RICE_HISTORY_CORNER_PATTERN.match(corpus_path)
    if history_corner_post:
        year, month, day, slug = (history_corner_post[group] for group in ("year", "month", "day", "slug"))
        return f"[@rhc {year}-{month}-{day} {slug}]  → https://ricehistorycorner.com/{year}/{month}/{day}/{slug}/"

    return f"(no rule for {corpus_path})"


if __name__ == "__main__":
    main(sys.argv[1:])
