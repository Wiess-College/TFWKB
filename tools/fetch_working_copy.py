#!/usr/bin/env python3
"""Download the archived sources listed in sources/manifests/ from archive.org into your working copy.

The repository keeps records about the evidence, not the evidence: each manifest lists files that
contributors read, with the Wayback Machine capture each came from. To read them yourself, or to run
tools such as cite.py, convert_html_to_text.py or find_pdf_page.py on them, you need the files on your
machine. This script fetches every file in the manifests that archive.org hosts, and lays them out the
way those tools expect (docs/sources/where-to-look.md, "A layout for your working copy").

It reads every sources/manifests/**/*.tsv and fetches the files listed in two kinds of manifest:

    <site>/index.tsv         Wayback captures: timestamp, original, status, mimetype, digest, local
                             saved as <working copy>/<site>/<local>
    <folder>/manifest.tsv    two columns, file name and a web.archive.org address
                             saved as <working copy>/<folder>/<file name>

Other .tsv manifests list things archive.org doesn't host (screenshots made locally, a live blog,
private scans); they are named once as skipped. It writes only into the working copy
folder, and changes nothing in the repository.

The working copy folder is the one given with --to, else TFWKB_WORKING_COPY, else `working_copy:` in
tfwkb.config.yml (see tools/repository_folders.py). It must be outside the repository.

    python3 tools/fetch_working_copy.py --dry-run           show what would be fetched, and how long it may take
    python3 tools/fetch_working_copy.py                     fetch everything not yet in the working copy
    python3 tools/fetch_working_copy.py --only teamwiess.com --only wiess.rice.edu
    python3 tools/fetch_working_copy.py --to ~/tfwkb-working-copy --delay 6

This is a big job: about 6,000 files, up to about 2 GB, and many hours at archive.org's pace. It asks
before starting (unless --yes). It is safe to stop at any time with Ctrl-C and to run again: files
already fetched are skipped, and a file is saved under its real name only once it is complete
(<name>.part until then). Expect to run it several times.

archive.org slows down clients that ask too fast. Between files it waits --delay seconds (default 4,
about 15 a minute). When archive.org answers "too many requests" (429) or "unavailable" (503), it waits
as long as archive.org asks, or a minute and then twice as long each time, up to 15 minutes. After 5
such answers in a row it stops: wait an hour or more, then run it again.

What it prints, and its exit status:

    one line per file fetched, then a summary
    exit 0      every listed file is in the working copy
    exit 1      some files were not fetched: "not in the archive" (404 or 410), or a network error
                after 3 tries; they are listed, and the next run tries them again
    exit 2      stopped because archive.org kept throttling; run again later
    exit 130    stopped with Ctrl-C; run again to continue

It stops before fetching anything, with a message, if no working copy folder is set, or if it is
inside the repository.
"""

import argparse
import csv
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import NamedTuple

from repository_folders import REPOSITORY_ROOT, working_copy_folder

MANIFESTS_ROOT = REPOSITORY_ROOT / "sources" / "manifests"

# The header of a Wayback capture index, as its first six columns.
CAPTURE_INDEX_COLUMNS = ["timestamp", "original", "status", "mimetype", "digest", "local"]

# "id_" after the timestamp asks the Wayback Machine for the file exactly as captured, without its banner.
WAYBACK_ORIGINAL_URL = "https://web.archive.org/web/{timestamp}id_/{original}"
WAYBACK_URL_PREFIX = "https://web.archive.org/"

# archive.org asks automated clients to say who they are.
USER_AGENT = "TFWKB fetch_working_copy.py (+https://github.com/Wiess-College/TFWKB)"

DEFAULT_DELAY_SECONDS = 4.0
NETWORK_TRIES = 3
NETWORK_RETRY_WAIT_SECONDS = 30
FIRST_THROTTLE_WAIT_SECONDS = 60
LONGEST_THROTTLE_WAIT_SECONDS = 15 * 60
THROTTLES_BEFORE_STOPPING = 5
REQUEST_TIMEOUT_SECONDS = 60
DOWNLOAD_CHUNK_BYTES = 64 * 1024

# HTTP answers that mean "slow down" rather than "no such file".
THROTTLE_STATUSES = {429, 503}
NOT_ARCHIVED_STATUSES = {404, 410}


class ArchivedFile(NamedTuple):
    """One file to fetch: where it goes in the working copy, and the archive.org address it comes from."""

    working_copy_subpath: str  # relative to the working copy folder, e.g. "teamwiess.com/mirror/..."
    archive_url: str  # a web.archive.org address that returns the file itself
    manifest_folder: str  # the manifest's folder, relative to sources/manifests/, e.g. "teamwiess.com"


class ThrottledError(Exception):
    """archive.org answered "too many requests" or "unavailable"; holds how long it asked us to wait."""

    def __init__(self, wait_seconds: float | None) -> None:
        """Keep the wait archive.org asked for (its Retry-After header), or None if it named none."""
        super().__init__(f"throttled; asked to wait {wait_seconds} s")
        self.wait_seconds = wait_seconds


class FetchTally(NamedTuple):
    """What one run did, for the summary."""

    fetched: list[str]  # working-copy subpaths saved this run
    not_archived: list[str]  # archive.org answered 404 or 410
    failed: list[str]  # network errors on every try


def main(arguments: list[str]) -> None:
    """Find the working copy, read the manifests, show the plan, and fetch what is missing."""
    options = parse_arguments(arguments)
    working_copy = choose_working_copy(options.to)
    archived_files, skipped_manifests = read_manifests(options.only)
    missing_files = [
        archived_file
        for archived_file in archived_files
        if not is_complete(working_copy / archived_file.working_copy_subpath)
    ]
    print_plan(archived_files, missing_files, skipped_manifests, working_copy, options.delay)
    if options.dry_run or not missing_files:
        return
    if not options.yes and not confirm_start():
        print("Nothing fetched.")
        return
    tally = fetch_all(missing_files, working_copy, options.delay)
    print_summary(tally)
    sys.exit(1 if tally.not_archived or tally.failed else 0)


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    """Return the command line's options."""
    parser = argparse.ArgumentParser(description="Fetch the archived sources in sources/manifests/ from archive.org.")
    parser.add_argument("--to", help="the working copy folder (else TFWKB_WORKING_COPY, else tfwkb.config.yml)")
    parser.add_argument(
        "--only", action="append", default=[], help="fetch only this manifest folder, e.g. teamwiess.com; repeatable"
    )
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="seconds to wait between files")
    parser.add_argument("--dry-run", action="store_true", help="show what would be fetched, and fetch nothing")
    parser.add_argument("--yes", action="store_true", help="start without asking")
    return parser.parse_args(arguments)


def choose_working_copy(given_folder: str | None) -> Path:
    """Return the working copy folder, creating it if needed; stop if none is set or it is inside the repo.

    Inside the repository, thousands of downloaded files would show up as changes to commit.
    """
    working_copy = working_copy_folder(given_folder)
    if working_copy is None:
        sys.exit(
            "No working copy folder is set. Give one with --to, set TFWKB_WORKING_COPY, or add\n"
            "`working_copy: ~/tfwkb-working-copy` to tfwkb.config.yml (see tfwkb.config.example.yml)."
        )
    working_copy = working_copy.resolve()
    if working_copy == REPOSITORY_ROOT or REPOSITORY_ROOT in working_copy.parents:
        sys.exit(f"The working copy folder {working_copy} is inside the repository; choose a folder outside it.")
    working_copy.mkdir(parents=True, exist_ok=True)
    return working_copy


def read_manifests(only_folders: list[str]) -> tuple[list[ArchivedFile], list[str]]:
    """Return every file archive.org hosts that the manifests list, and the manifests that list none.

    Manifests are read in alphabetical order of their paths. With only_folders, a manifest is read only if
    its folder is one of them or inside one of them.
    """
    archived_files: list[ArchivedFile] = []
    skipped_manifests = []
    for manifest_file in sorted(MANIFESTS_ROOT.rglob("*.tsv")):
        manifest_folder = manifest_file.parent.relative_to(MANIFESTS_ROOT).as_posix()
        if only_folders and not any(
            manifest_folder == folder or manifest_folder.startswith(folder + "/") for folder in only_folders
        ):
            continue
        with manifest_file.open(encoding="utf-8", newline="") as manifest:
            rows = list(csv.reader(manifest, delimiter="\t"))
        listed_files = read_capture_index(rows, manifest_folder)
        if listed_files is None:
            listed_files = read_file_list(rows, manifest_folder)
        if listed_files is None:
            skipped_manifests.append(manifest_file.relative_to(MANIFESTS_ROOT).as_posix())
        else:
            archived_files.extend(listed_files)
    return archived_files, skipped_manifests


def read_capture_index(rows: list[list[str]], manifest_folder: str) -> list[ArchivedFile] | None:
    """Return the captures in a Wayback capture index (none, if it has no rows), or None if it is not one.

    Some "local" paths hold a stray backslash before a slash, left by the tool that wrote them; it is
    dropped, as tools/convert_html_to_text.py's docstring says to.
    """
    if not rows or rows[0][: len(CAPTURE_INDEX_COLUMNS)] != CAPTURE_INDEX_COLUMNS:
        return None
    captures = []
    for row in rows[1:]:
        timestamp, original, _, _, _, local_path = row[: len(CAPTURE_INDEX_COLUMNS)]
        captures.append(
            ArchivedFile(
                f"{manifest_folder}/{local_path.replace(chr(92), '')}",  # chr(92) is the backslash
                WAYBACK_ORIGINAL_URL.format(timestamp=timestamp, original=original),
                manifest_folder,
            )
        )
    return captures


def read_file_list(rows: list[list[str]], manifest_folder: str) -> list[ArchivedFile] | None:
    """Return the files in a two-column list of file names and web.archive.org addresses, or None if not one."""
    if not rows or any(len(row) != 2 or not row[1].startswith(WAYBACK_URL_PREFIX) for row in rows):
        return None
    return [
        ArchivedFile(f"{manifest_folder}/{file_name}", archive_url, manifest_folder)
        for file_name, archive_url in rows
    ]


def is_complete(target_file: Path) -> bool:
    """Return whether a file is already in the working copy (a finished download is never empty)."""
    return target_file.is_file() and target_file.stat().st_size > 0


def print_plan(
    archived_files: list[ArchivedFile],
    missing_files: list[ArchivedFile],
    skipped_manifests: list[str],
    working_copy: Path,
    delay_seconds: float,
) -> None:
    """Print, per manifest folder, how many files are listed and still to fetch, and a rough time estimate.

    The estimate allows the delay plus about one second per file, and ignores throttling, which can
    add hours.
    """
    print(f"Working copy: {working_copy}")
    for manifest_folder in sorted({archived_file.manifest_folder for archived_file in archived_files}):
        listed_count = sum(1 for archived_file in archived_files if archived_file.manifest_folder == manifest_folder)
        missing_count = sum(1 for archived_file in missing_files if archived_file.manifest_folder == manifest_folder)
        print(f"  {manifest_folder}: {listed_count} listed, {missing_count} to fetch")
    if skipped_manifests:
        print("Not on archive.org, so not fetched: " + ", ".join(skipped_manifests))
    hours = len(missing_files) * (delay_seconds + 1) / 3600
    print(f"To fetch: {len(missing_files)} files, roughly {hours:.1f} hours at --delay {delay_seconds:g}.")
    if missing_files:
        print(
            "This is a long job and can use a few GB of disk. Stop it at any time with Ctrl-C and run it again "
            "to continue.\narchive.org may slow it down; if it stops for that, wait an hour and run it again."
        )


def confirm_start() -> bool:
    """Return whether the person at the terminal wants to start; with no terminal, start without asking."""
    if not sys.stdin.isatty():
        return True
    return input("Start? [y/N] ").strip().lower() in ("y", "yes")


def fetch_all(missing_files: list[ArchivedFile], working_copy: Path, delay_seconds: float) -> FetchTally:
    """Fetch each missing file in turn, waiting between files and when throttled; return what happened.

    Ctrl-C stops the run with exit status 130 after printing the summary so far; a throttle that will not
    lift stops it with status 2. A file being written when it stops is left as <name>.part, which the
    next run overwrites.
    """
    tally = FetchTally([], [], [])
    throttle_count = 0
    position = 0
    try:
        while position < len(missing_files):
            archived_file = missing_files[position]
            try:
                outcome = fetch_with_retries(archived_file, working_copy / archived_file.working_copy_subpath)
            except ThrottledError as throttle:
                throttle_count += 1
                wait_for_throttle(throttle, throttle_count, tally)
                continue  # the same file again
            throttle_count = 0
            record_outcome(outcome, archived_file, tally, position, len(missing_files))
            position += 1
            time.sleep(delay_seconds)
    except KeyboardInterrupt:
        print("\nStopped. Run it again to continue where it left off.")
        print_summary(tally)
        sys.exit(130)
    return tally


def fetch_with_retries(archived_file: ArchivedFile, target_file: Path) -> str:
    """Download one file, trying again after a network error; return "fetched", "not archived" or "failed".

    A throttling answer is not retried here: ThrottledError goes up to fetch_all, which waits.
    """
    for try_number in range(1, NETWORK_TRIES + 1):
        try:
            download(archived_file.archive_url, target_file)
            return "fetched"
        except urllib.error.HTTPError as http_error:
            if http_error.code in THROTTLE_STATUSES:
                raise ThrottledError(read_retry_after(http_error)) from http_error
            if http_error.code in NOT_ARCHIVED_STATUSES:
                return "not archived"
            failure = f"HTTP {http_error.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as network_error:
            failure = str(network_error)
        if try_number < NETWORK_TRIES:
            print(f"  {failure}; trying again in {NETWORK_RETRY_WAIT_SECONDS} s: {archived_file.working_copy_subpath}")
            time.sleep(NETWORK_RETRY_WAIT_SECONDS)
    return "failed"


def download(archive_url: str, target_file: Path) -> None:
    """Save the address's contents as target_file, via <name>.part so a broken download never looks finished."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    part_file = target_file.with_name(target_file.name + ".part")
    request = urllib.request.Request(archive_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response, part_file.open("wb") as part:
            while chunk := response.read(DOWNLOAD_CHUNK_BYTES):
                part.write(chunk)
        os.replace(part_file, target_file)
    finally:
        part_file.unlink(missing_ok=True)


def read_retry_after(http_error: urllib.error.HTTPError) -> float | None:
    """Return the seconds archive.org asked us to wait (its Retry-After header), or None if it gave none."""
    retry_after = http_error.headers.get("Retry-After", "") if http_error.headers else ""
    return float(retry_after) if retry_after.strip().isdigit() else None


def wait_for_throttle(throttle: ThrottledError, throttle_count: int, tally: FetchTally) -> None:
    """Wait as archive.org asked, or longer each time; stop the run with status 2 after too many in a row."""
    if throttle_count >= THROTTLES_BEFORE_STOPPING:
        print(
            f"\narchive.org has throttled this machine {throttle_count} times in a row. Stopping so as not to make "
            "it worse.\nWait an hour or more, then run this again; it continues where it left off."
        )
        print_summary(tally)
        sys.exit(2)
    doubling_wait = FIRST_THROTTLE_WAIT_SECONDS * 2 ** (throttle_count - 1)
    wait_seconds = min(throttle.wait_seconds or doubling_wait, LONGEST_THROTTLE_WAIT_SECONDS)
    print(f"  archive.org asked us to slow down; waiting {wait_seconds:.0f} s")
    time.sleep(wait_seconds)


def record_outcome(outcome: str, archived_file: ArchivedFile, tally: FetchTally, position: int, total: int) -> None:
    """Add one file's outcome to the tally and print a line for it, counting from 1."""
    subpath = archived_file.working_copy_subpath
    {"fetched": tally.fetched, "not archived": tally.not_archived, "failed": tally.failed}[outcome].append(subpath)
    print(f"[{position + 1}/{total}] {outcome}: {subpath}")


def print_summary(tally: FetchTally) -> None:
    """Print how many files were fetched this run, and list those that were not."""
    print(f"\nFetched this run: {len(tally.fetched)}")
    if tally.not_archived:
        print(f"Not in the archive (404 or 410), {len(tally.not_archived)}:")
        print("\n".join("  " + subpath for subpath in tally.not_archived))
    if tally.failed:
        print(f"Network errors after {NETWORK_TRIES} tries, {len(tally.failed)} (the next run tries again):")
        print("\n".join("  " + subpath for subpath in tally.failed))


if __name__ == "__main__":
    main(sys.argv[1:])
