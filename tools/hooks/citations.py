"""MkDocs hook: citations, evidence tags, timelines and the generated bibliography.

Pages cite their sources with short forms instead of writing links by hand. A source's address is then
recorded once, in sources/bibliography/*.yaml, and a mistyped key fails the build instead of leaving a
dead link. This hook turns the short forms, and a few other pieces of page syntax, into HTML while MkDocs
builds the site. The short forms are (see docs/contributing/citing.md):

    [@key]                     a source from sources/bibliography/*.yaml
    [@key p.14]                with a locator (free text; "p.N" on a PDF adds #page=N)
    [@wb 20070709182921 http://teamwiess.com/x.html]   a Wayback capture
    [@portal metapth245573 p.27]                        a Portal to Texas History page (Thresher)
    [@rhc 2021-12-10 im-pissed-no-date comment by X]    a Rice History Corner post
    [@woodson UA0079 box 3 folder 12]                   Woodson Research Center item
    [@fondren <item URL> Sallyport, Spring 1995, p.12]  Fondren Digital Collections item (Sallyport, Campanile)

On each page it does the following, in this order:

    <!-- BIBLIOGRAPHY -->   replaced by every bibliography entry, grouped by type (sources/bibliography.md)
    ```timeline blocks      drawn as bar charts (the syntax is in render_timeline's docstring)
    citations               numbered superscripts, with a References list at the foot of the page
    [P] [R] [T]             evidence badges (see docs/sources/evidence-classes.md)
    outbound links          sent through the Wayback Machine, once the page has become HTML

It reads sources/bibliography/*.yaml and sources/portal-issue-dates.tsv (Thresher issue dates, so that a
Portal citation can show its date) when the build starts. It writes no files of its own; it changes each
page's Markdown and HTML on their way through MkDocs. tools/cite.py imports it to show where a citation
links.

MkDocs loads it through "hooks:" in mkdocs.yml, so it runs on every build and there is nothing to run by
hand:

    mkdocs build --strict
    mkdocs serve

A problem with one citation or timeline line is logged as a warning and the page is still built: the
citation is shown without a link, and the timeline line or segment is left out. With --strict, which the
publishing workflow uses, the build then fails at the end. The warnings:

    "bibliography entry without key in ..."   the entry is left out of the bibliography.
    "duplicate bibliography key ..."          the entry from the later file, in alphabetical order, is used.
    "bibliography entry ... has no url ..."   it needs a url, parts or held_by; it is still used, without a link.
    "<page>: unknown citation key ..."        the key is not in sources/bibliography/*.yaml.
    "<page>: bad Wayback citation ..."        [@wb] needs a timestamp and a URL.
    "<page>: bad Portal citation ..."         [@portal] needs an ARK id.
    "<page>: timeline line without ':' ..."   the line is left out of the chart.
    "<page>: bad timeline span ..."           that segment is left out of the chart.

Other mistakes stop the build with a Python traceback; fix them and build again. Among them: a YAML file
that does not parse, a bibliography entry that is not a mapping, an "evidence:" value other than P, R or
T, and a timeline "from:" or "to:" that is not a year.

Text that only looks like syntax is left as it is, with no warning: "[@ key]" with a space, a citation
inside a fenced code block, and square brackets around any letter other than P, R or T.
"""

from __future__ import annotations

import datetime
import glob
import html
import logging
import os
import re
import string
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

import yaml

if TYPE_CHECKING:
    # Only for the type hints on the MkDocs event functions, so importing this file (as tools/cite.py
    # does) needs PyYAML but not MkDocs.
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page

# A child of the "mkdocs" logger, so MkDocs prints these warnings and --strict counts them.
LOGGER = logging.getLogger("mkdocs.plugins.familykb.citations")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIBLIOGRAPHY_FILES_GLOB = os.path.join(REPO_ROOT, "sources", "bibliography", "*.yaml")
# One "<ARK id><tab><YYYY-MM-DD>" line per Thresher issue; other lines, such as the header, are skipped.
PORTAL_ISSUE_DATES_FILE = os.path.join(REPO_ROOT, "sources", "portal-issue-dates.tsv")

# Filled by load_citation_sources() when the build starts, then read by every page.
BIBLIOGRAPHY: dict[str, dict] = {}  # bibliography key -> its YAML entry
ISSUE_DATE_BY_ARK_ID: dict[str, str] = {}  # Portal ARK id -> the issue's date, "YYYY-MM-DD"

MONTH_ABBREVIATIONS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

# Hover text for each evidence badge; docs/sources/evidence-classes.md explains the classes.
EVIDENCE_CLASS_DESCRIPTIONS = {
    "P": "Primary / contemporary source, read directly",
    "R": "Retrospective account (who said it, and when)",
    "T": "Testimony / memory (who, class year, date of the comment)",
}

# The bibliography page's section heading for each entry "type:", in the order the sections appear.
# Entries of any other type follow, in sections named after the type itself.
BIBLIOGRAPHY_HEADING_BY_TYPE = {
    "oweek-book": "O-Week books and handbooks",
    "governing-document": "Constitutions, bylaws and rules",
    "website": "Wiess websites (archived)",
    "newspaper": "The Rice Thresher and other newspapers",
    "yearbook": "The Campanile",
    "blog": "Blogs and comment threads",
    "artifact": "Artifacts, photographs and documents held by the college",
    "archive": "Archives and finding aids",
    "magazine": "Magazines",
    "other": "Other",
}

BIBLIOGRAPHY_MARKER = "<!-- BIBLIOGRAPHY -->"
# Where a page's "Last reviewed" footer starts; the References list goes just above it.
REVIEWED_FOOTER_START = '<div class="reviewed"'

# A citation: "[@", a key (letters, digits and . _ : -, starting with a letter or digit), then optionally
# whitespace and a locator that runs to the first "]". The locator keeps its leading whitespace.
CITATION_PATTERN = re.compile(r"\[@(?P<key>[A-Za-z0-9][A-Za-z0-9._:-]*)(?P<locator>(?:\s+[^\]]*)?)\]")

# "[P]", "[R]" or "[T]", but not a Markdown link such as "[P](page.md)".
EVIDENCE_TAG_PATTERN = re.compile(r"\[(?P<evidence_class>[PRT])\](?!\()")

# A page in a locator: "p.14", "p 14" or "p14". The "p" must start a word, so "pp.102-103" has no page.
PAGE_LOCATOR_PATTERN = re.compile(r"\bp\.?\s*(?P<page_number>\d+)")

# A Rice History Corner locator: the post's date and slug as in its address, then any further notes.
RICE_HISTORY_CORNER_POST_PATTERN = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\s+(?P<slug>[a-z0-9-]+)\s*(?P<notes>.*)$"
)

# A fenced code block: from a line starting ``` to the next line starting ```, to the end of that line.
# The whole pattern is one group because re.split then keeps each block in its result, at odd positions.
CODE_FENCE_PATTERN = re.compile(r"(?P<code_block>^```.*?^```[^\n]*$)", re.DOTALL | re.MULTILINE)

# Spaces or tabs between one footnote mark and the next, so "[1] [2]" in the text renders as "[1][2]".
SPACE_BETWEEN_FOOTNOTE_MARKS_PATTERN = re.compile(r'(?<=</sup>)[ \t]+(?=<sup class="cite-ref")')

# A ```timeline fenced block; "body" is everything between the fence lines.
TIMELINE_BLOCK_PATTERN = re.compile(r"^```timeline[ \t]*\n(?P<body>.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)

# Words that mean "this year" in a timeline. "" counts too, so "to:" and "2012-" are open-ended.
ONGOING_WORDS = ("now", "today", "current", "present", "ongoing", "")

# Timeline lines: "from: 1985" or "to: now"; a group heading, "group: Name" or "[Name]"; and the
# "[Name]:" that starts a group's own row.
TIMELINE_AXIS_LINE_PATTERN = re.compile(r"^(?P<setting>from|to)\s*:\s*(?P<year>\S*)$", re.IGNORECASE)
TIMELINE_GROUP_LINE_PATTERN = re.compile(
    r"^(?:group\s*:\s*(?P<after_colon>.+?)|\[\s*(?P<in_brackets>[^\]]+?)\s*\])\s*$", re.IGNORECASE
)
TIMELINE_GROUP_ROW_PATTERN = re.compile(r"^\[\s*(?P<name>[^\]]+?)\s*\]\s*:")

# Segments on one row are separated by ";", or by "," when a year (perhaps after "?") follows it.
TIMELINE_SEGMENT_SEPARATOR_PATTERN = re.compile(r";\s*|,\s*(?=\??\s*\d{4})")
# A segment written label first, "Apprentice: 2025-now"; segments that start with a year don't match.
TIMELINE_LABEL_FIRST_SEGMENT_PATTERN = re.compile(r"^(?P<label>.*?):\s*(?P<span>\??\s*\d{4}.*)$")
TIMELINE_STARTS_WITH_YEAR_PATTERN = re.compile(r"^\??\s*\d{4}")
# A segment: a span ("?1993-2013?", "2012-now", "1987") and then, after whitespace, its own label.
TIMELINE_SEGMENT_PATTERN = re.compile(
    r"^(?P<span>"
    r"\??\s*\d{4}\s*"  # optional leading "?", then the first year
    r"(?:-\s*(?:\d{4}|now|today|current|present|ongoing)?)?"  # optional "-" with a last year or ongoing word
    r"\s*\??"  # optional trailing "?"
    r")(?:\s+(?P<text>.*))?$",
    re.IGNORECASE,
)

# Links that on_page_content leaves pointing straight at their site rather than through the Wayback
# Machine. Each is matched at the start of the address, after the scheme.
DIRECT_LINK_PREFIXES = (
    "web.archive.org", "archive.org", "texashistory.unt.edu",  # archives in their own right
    "digitalcollections.rice.edu", "rice.quartexcollections.com",  # Fondren Digital Collections
    "iiif.quartexcollections.com", "hdl.handle.net",
    "github.com/Wiess-College", "wiess-college.github.io",  # our repo and site
    "squidfunk.github.io", "fonts.googleapis.com", "fonts.gstatic.com",  # theme furniture
    "creativecommons.org",
)
# An absolute link in the rendered page; "url" is the address.
EXTERNAL_LINK_PATTERN = re.compile(r'href="(?P<url>https?://[^"]+)"')


class ResolvedCitation(NamedTuple):
    """Where one citation links, and what it says to the reader."""

    url: str | None  # absolute address, or None when there is nothing to link to
    label: str  # the text in the References list, and the footnote mark's hover text
    hover_title: str  # hover text in the older inline style (render_citation)
    found: bool  # False for an unknown key or a malformed citation; the mark is then styled "cite-unknown"


@dataclass
class FootnoteReference:
    """One numbered entry in a page's References list, and how often the page has cited it so far."""

    number: int  # its number in the References list, counting from 1
    resolved: ResolvedCitation  # from the first time the page cites it
    use_count: int = 0  # each use gets its own back-link from the References list


class TimelineSpan(NamedTuple):
    """The years one timeline segment covers, and how its ends are drawn."""

    first_year: int
    last_year: int  # the same as first_year for a single year
    fades_in: bool  # written "?1987-": the earliest mention found, so it may have started earlier
    fades_out: bool  # written "-2011?": the latest mention found, so it may have continued
    is_open_ended: bool  # written "2012-now" or "2012-": still going, drawn with an arrow
    is_point: bool  # a single year with no "?", drawn as a marker rather than a bar


class TimelineSegment(NamedTuple):
    """One bar or marker on a timeline row, with its own label."""

    first_year: int
    last_year: int
    fades_in: bool
    fades_out: bool
    is_open_ended: bool
    is_point: bool  # drawn as a marker: a single year, or anything on a row starting with "*"
    text: str  # the segment's own label, shown on the bar; "" for none


class TimelineGroupHeading(NamedTuple):
    """A heading row that starts a group of timeline rows."""

    heading: str


class TimelineRow(NamedTuple):
    """One labelled row of a timeline, with its bars and markers."""

    label: str
    segments: list[TimelineSegment]
    is_top_level: bool  # not inside a group: before the first heading, or a "[Name]:" row


class TimelineAxis(NamedTuple):
    """The years a timeline chart covers, and where each year falls across it."""

    start_year: int
    end_year: int  # the last year drawn, inclusive

    @property
    def year_count(self) -> int:
        """Return how many years the chart covers, counting both ends."""
        return self.end_year + 1 - self.start_year

    def percent_across(self, year: int) -> float:
        """Return how far across the chart the start of a year is, as a percentage of its width."""
        return 100.0 * (year - self.start_year) / self.year_count


def on_config(config: MkDocsConfig) -> MkDocsConfig:
    """Load the bibliography and the Portal issue dates once, before any page is built."""
    load_citation_sources()
    LOGGER.info("familykb: %d bibliography entries", len(BIBLIOGRAPHY))
    return config


def load_citation_sources() -> None:
    """Read the bibliography and the Portal issue dates into BIBLIOGRAPHY and ISSUE_DATE_BY_ARK_ID.

    tools/cite.py calls this too, so that it answers from the same data as the site.
    """
    global BIBLIOGRAPHY, ISSUE_DATE_BY_ARK_ID
    BIBLIOGRAPHY = load_bibliography()
    ISSUE_DATE_BY_ARK_ID = load_portal_issue_dates()


def load_bibliography() -> dict[str, dict]:
    """Return every bibliography entry by its key, warning about entries with no key and keys used twice.

    Files are read in alphabetical order, so when a key is used twice the entry from the later file wins.
    It also warns about an entry with no public copy (no url or parts) that doesn't say who holds the
    source (held_by), since a reader would then have no way to check it.
    """
    bibliography: dict[str, dict] = {}
    for bibliography_file in sorted(glob.glob(BIBLIOGRAPHY_FILES_GLOB)):
        with open(bibliography_file, encoding="utf-8") as bibliography_yaml:
            entries = yaml.safe_load(bibliography_yaml) or []
        for entry in entries:
            citation_key = entry.get("key")
            if not citation_key:
                LOGGER.warning("bibliography entry without key in %s: %r", bibliography_file, entry)
                continue
            if citation_key in bibliography:
                LOGGER.warning("duplicate bibliography key %r (%s)", citation_key, bibliography_file)
            if not (entry.get("url") or entry.get("parts") or entry.get("held_by")):
                LOGGER.warning("bibliography entry %r has no url and no held_by (%s)", citation_key, bibliography_file)
            entry["_file"] = os.path.basename(bibliography_file)  # nothing reads this at present
            bibliography[citation_key] = entry
    return bibliography


def load_portal_issue_dates() -> dict[str, str]:
    """Return each Thresher issue's date by its Portal ARK id, or nothing if the file is missing."""
    issue_date_by_ark_id: dict[str, str] = {}
    if not os.path.exists(PORTAL_ISSUE_DATES_FILE):
        return issue_date_by_ark_id
    with open(PORTAL_ISSUE_DATES_FILE, encoding="utf-8") as issue_dates:
        for line in issue_dates:
            columns = line.rstrip("\n").split("\t")
            if len(columns) < 2:
                continue
            ark_id, issue_date, *_other_columns = columns
            if ark_id.startswith("metapth") and re.match(r"\d{4}-\d{2}-\d{2}$", issue_date):
                issue_date_by_ark_id[ark_id] = issue_date
    return issue_date_by_ark_id


def on_page_markdown(markdown: str, page: Page, config: MkDocsConfig, files: Files) -> str:
    """Expand the bibliography marker, timelines, citations and evidence tags in one page's Markdown.

    Citations are numbered after the bibliography and timelines are expanded, and the spoiler check runs
    on the result. A page with a collapsed "??? danger" spoiler box gets its References list in a
    collapsed box too, so the sources don't give the secret away. Evidence tags go last, over the whole
    page, code blocks included.
    """
    page_path = page.file.src_path
    if BIBLIOGRAPHY_MARKER in markdown:
        markdown = markdown.replace(BIBLIOGRAPHY_MARKER, render_bibliography())
    markdown = TIMELINE_BLOCK_PATTERN.sub(
        lambda timeline_block: render_timeline(timeline_block["body"], page_path), markdown
    )
    markdown = footnote_citations(markdown, page_path, spoiler="??? danger" in markdown)
    return EVIDENCE_TAG_PATTERN.sub(
        lambda evidence_tag: render_evidence_badge(evidence_tag["evidence_class"]), markdown
    )


def render_bibliography() -> str:
    """Return every bibliography entry as Markdown and HTML, in sections by type, each sorted by date.

    This is the body of sources/bibliography.md. An entry with no date sorts first in its section; ties
    are broken by key.
    """
    entries_by_type: dict[str, list[dict]] = defaultdict(list)
    for entry in BIBLIOGRAPHY.values():
        entries_by_type[entry.get("type", "other")].append(entry)
    lines = [
        f"*{len(BIBLIOGRAPHY)} sources, grouped by kind and sorted by date. "
        "Pages cite them by the key in `code`.*\n"
    ]
    other_types = sorted(set(entries_by_type) - set(BIBLIOGRAPHY_HEADING_BY_TYPE))
    for source_type in list(BIBLIOGRAPHY_HEADING_BY_TYPE) + other_types:
        if source_type not in entries_by_type:
            continue
        lines.append(f"\n## {BIBLIOGRAPHY_HEADING_BY_TYPE.get(source_type, source_type)}\n")
        lines.append('<dl class="bib">')
        for entry in sorted(entries_by_type[source_type], key=lambda dated: str(dated.get("date", "")) + dated["key"]):
            lines.append(render_bibliography_entry(entry))
        lines.append("</dl>")
    return "\n".join(lines)


def render_bibliography_entry(entry: dict) -> str:
    """Return one bibliography entry as a <dt> (key, linked title, date, author, evidence) and a <dd>.

    The <dt>'s id is the key, so a page can link straight to an entry. The <dd> holds the notes, then who
    holds a source with no public copy, the page count and the gaps on one line, and is left out when there
    are none. "local:" (where a file sat in one contributor's working copy) is not shown: no reader has it.
    """
    citation_key = entry["key"]
    title = html.escape(str(entry.get("title", citation_key)))
    entry_url = entry.get("url")
    heading = f'<a href="{html.escape(entry_url, quote=True)}">{title}</a>' if entry_url else title
    details = []
    if entry.get("date"):
        details.append(html.escape(str(entry["date"])))
    if entry.get("author"):
        details.append(html.escape(str(entry["author"])))
    if entry.get("evidence"):
        # Matches only "P", "R" or "T" (or a value starting "P]"); any other value stops the build here.
        evidence_tag = re.match(r"\[(?P<evidence_class>[PRT])\]", f"[{entry['evidence']}]")
        details.append(render_evidence_badge(evidence_tag["evidence_class"]))
    detail_line = " · ".join(details)
    lines = [
        f'<dt id="{html.escape(citation_key)}"><code>{html.escape(citation_key)}</code>—{heading}'
        + (f" <small>{detail_line}</small>" if detail_line else "")
        + "</dt>"
    ]

    description = []
    if entry.get("notes"):
        description.append(html.escape(str(entry["notes"]).strip()))
    holdings = []
    if entry.get("held_by"):
        holdings.append(f'held by: {html.escape(str(entry["held_by"]))}')
    if entry.get("pages"):
        holdings.append(f'{html.escape(str(entry["pages"]))} pp.')
    if entry.get("gaps"):
        holdings.append(f'gaps: {html.escape(str(entry["gaps"]))}')
    if holdings:
        description.append(" · ".join(holdings))
    if description:
        lines.append("<dd>" + "<br>".join(description) + "</dd>")
    return "\n".join(lines)


def render_timeline(body: str, page_path: str) -> str:
    """Return one ```timeline block as an HTML bar chart, or "" if it has no bars or markers.

    This is Wikipedia's "EasyTimeline" style. It is plain HTML styled by docs/assets/familykb.css (the
    .tl-* classes) rather than an image, so it reflows on phones. The block is written like this:

        ```timeline
        from: 1985
        to: now                                (or current, or leave blank, or leave the line out)
        Talent show in the Commons: 1987-1992
        Acabowl concert: 1993-2001
        Shared with Wiess Day: 2010-2011?      (? = last seen; the bar fades out)
        Wooden War Pig: 2012-now               (still going: arrow. Also -current, -present, or just 2012-)
        Earliest mention: ?1987-1990           (leading ? = first found; fades in)
        Only mention: ?2017?                   (seen once; a one-year bar that fades both ways)
        * Two stages: 2005                     (a marker on its own row)
        [Vice Presidents]                      (a group heading; or "group: Vice Presidents")
        Internal VP: ?1993-2006 Executive; 2007-2015 Executive (Internal); 2016- Internal
                                               (several segments on one row, each with its own label;
                                                also written "Executive: ?1993-2006")
        ```

    Without "from:" the chart starts at the earliest year, and without "to:" it ends at the latest; it
    always covers at least two years. A bar starting before "from:" is cut off at the left edge. Lines
    starting with "#" are comments. "now" is the year of the build.
    """
    this_year = datetime.date.today().year
    from_year, to_year, rows = parse_timeline(body, page_path, this_year)
    segments = [segment for row in rows if isinstance(row, TimelineRow) for segment in row.segments]
    if not segments:
        return ""
    start_year = from_year if from_year is not None else min(segment.first_year for segment in segments)
    end_year = to_year if to_year is not None else max(segment.last_year for segment in segments)
    axis = TimelineAxis(start_year, max(end_year, start_year + 1))

    # A tick every 5 years, or every 10 on a long chart, on years divisible by the step. Every other tick
    # is "minor", which the stylesheet can hide on narrow screens.
    tick_step = 5 if axis.year_count <= 45 else 10
    first_tick_year = axis.start_year
    if first_tick_year % tick_step:
        first_tick_year += tick_step - first_tick_year % tick_step
    tick_years = range(first_tick_year, axis.end_year + 1, tick_step)
    ticks = "".join(
        f'<span class="tl-tick{" tl-minor" if tick_year % (2 * tick_step) else ""}" '
        f'style="left:{axis.percent_across(tick_year):.2f}%">{tick_year}</span>'
        for tick_year in tick_years
    )
    grid = "".join(
        f'<span class="tl-grid" style="left:{axis.percent_across(tick_year):.2f}%"></span>' for tick_year in tick_years
    )

    lines = [
        '<div class="tl" role="img" aria-label="Timeline chart; the same dates are in the Timeline table below">',
        f'<div class="tl-row tl-axis"><span class="tl-label"></span><span class="tl-track">{ticks}</span></div>',
    ]
    has_groups = any(isinstance(row, TimelineGroupHeading) for row in rows)
    for row in rows:
        if isinstance(row, TimelineGroupHeading):
            lines.append(
                f'<div class="tl-row tl-group"><span class="tl-label">{html.escape(row.heading)}</span>'
                f'<span class="tl-track">{grid}</span></div>'
            )
        else:
            lines.append(render_timeline_row(row, axis, grid, has_groups))
    lines.append(
        '<div class="tl-key"><span class="tl-key-solid"></span> in the sources '
        '<span class="tl-key-fade"></span> may reach further: earliest or latest mention found so far '
        '<span class="tl-key-open"></span> still going</div>'
    )
    lines.append("</div>")
    return "\n".join(lines)


def parse_timeline(
    body: str,
    page_path: str,
    this_year: int,
) -> tuple[int | None, int | None, list[TimelineGroupHeading | TimelineRow]]:
    """Return a timeline block's "from:" and "to:" years (None if not given) and its rows, in order."""
    from_year = to_year = None
    rows: list[TimelineGroupHeading | TimelineRow] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        axis_line = TIMELINE_AXIS_LINE_PATTERN.match(line)
        if axis_line:
            if axis_line["setting"].lower() == "from":
                from_year = parse_timeline_year(axis_line["year"], this_year)
            else:
                to_year = parse_timeline_year(axis_line["year"], this_year)
            continue
        group_line = TIMELINE_GROUP_LINE_PATTERN.match(line)
        if group_line:
            rows.append(TimelineGroupHeading((group_line["after_colon"] or group_line["in_brackets"]).strip()))
            continue
        has_group_heading = any(isinstance(row, TimelineGroupHeading) for row in rows)
        row = parse_timeline_row(line, raw_line, has_group_heading, page_path, this_year)
        if row is not None:
            rows.append(row)
    return from_year, to_year, rows


def parse_timeline_row(
    line: str,
    raw_line: str,
    has_group_heading: bool,
    page_path: str,
    this_year: int,
) -> TimelineRow | None:
    """Return one "Label: span text; span text" line as a row, or None if it has no usable segment.

    A row is top-level, drawn outside any group, if no group heading has come before it or it is written
    "[Name]: ...". A row starting with "*" draws every segment as a marker.
    """
    is_top_level = bool(TIMELINE_GROUP_ROW_PATTERN.match(line)) or not has_group_heading
    line = TIMELINE_GROUP_ROW_PATTERN.sub(r"\g<name>:", line)
    is_marker_row = line.startswith("*")
    if is_marker_row:
        line = line[1:].strip()
    if ":" not in line:
        LOGGER.warning("%s: timeline line without ':' %r", page_path, raw_line)
        return None
    label, segment_list = line.split(":", 1)
    segments = []
    for segment_text in TIMELINE_SEGMENT_SEPARATOR_PATTERN.split(segment_list.strip()):
        segment_text = segment_text.strip()
        if not segment_text:
            continue
        segment = parse_timeline_segment(segment_text, is_marker_row, this_year)
        if segment is None:
            LOGGER.warning("%s: bad timeline span %r", page_path, raw_line)
            continue
        segments.append(segment)
    if not segments:
        return None
    return TimelineRow(label.strip(), segments, is_top_level)


def parse_timeline_segment(segment_text: str, is_marker_row: bool, this_year: int) -> TimelineSegment | None:
    """Return one segment, "1993-2006 Executive" or "Executive: 1993-2006", or None if its span is unreadable."""
    label_first = TIMELINE_LABEL_FIRST_SEGMENT_PATTERN.match(segment_text)
    if label_first and not TIMELINE_STARTS_WITH_YEAR_PATTERN.match(segment_text):
        segment_text = f"{label_first['span']} {label_first['label']}"
    segment = TIMELINE_SEGMENT_PATTERN.match(segment_text)
    span = parse_timeline_span(segment["span"], this_year) if segment else None
    if span is None:
        return None
    return TimelineSegment(
        span.first_year,
        span.last_year,
        span.fades_in,
        span.fades_out,
        span.is_open_ended,
        span.is_point or is_marker_row,
        (segment["text"] or "").strip().strip('"'),
    )


def parse_timeline_span(span_text: str, this_year: int) -> TimelineSpan | None:
    """Return the years and end styles of a span such as "?1993-2013?", or None if a year is unreadable."""
    span_text = span_text.strip()
    fades_in = span_text.startswith("?")
    span_text = span_text.lstrip("?")
    fades_out = span_text.endswith("?")
    span_text = span_text.rstrip("?").strip()
    first_word, dash, last_word = span_text.partition("-")
    try:
        first_year = parse_timeline_year(first_word, this_year)
        is_open_ended = bool(dash) and last_word.strip().lower() in ONGOING_WORDS
        last_year = parse_timeline_year(last_word, this_year) if dash else first_year
    except ValueError:
        return None
    # "?2017?" (seen once, may have run longer either way) is a one-year bar with fades, not a marker.
    is_point = not dash and not (fades_in or fades_out)
    return TimelineSpan(first_year, last_year, fades_in, fades_out, is_open_ended, is_point)


def parse_timeline_year(year_word: str, this_year: int) -> int:
    """Return a timeline year, or this year for "now" and the other ongoing words; raise ValueError otherwise."""
    year_word = year_word.strip()
    return this_year if year_word.lower() in ONGOING_WORDS else int(year_word)


def render_timeline_row(row: TimelineRow, axis: TimelineAxis, grid: str, has_groups: bool) -> str:
    """Return one timeline row: its label and dates on the left, and its bars and markers across the track.

    A row with one segment shows that segment's dates beside the label. A row with several lists each
    segment's dates and label under the label instead, since short bars have no room for their text; if
    any bar is under four years long, the row is marked "tl-tight" for the stylesheet.
    """
    label_html = html.escape(row.label)
    drawings, date_texts = [], []
    for segment_position, segment in enumerate(row.segments):
        if segment.is_point:
            drawing, date_text = render_timeline_marker(segment, label_html, axis)
        else:
            drawing, date_text = render_timeline_bar(segment, segment_position, label_html, axis)
        drawings.append(drawing)
        date_texts.append(date_text)

    single_segment_dates = html.escape(", ".join(date_texts)) if len(row.segments) == 1 else ""
    segment_list = ""
    if len(row.segments) > 1:
        segment_list = (
            '<span class="tl-seg-list">'
            + " · ".join(
                html.escape(f'{date_text}{" " + segment.text if segment.text else ""}')
                for date_text, segment in zip(date_texts, row.segments)
            )
            + "</span>"
        )
    is_tight = len(row.segments) > 1 and any(
        (segment.last_year - max(segment.first_year, axis.start_year) + 1) < 4 and not segment.is_point
        for segment in row.segments
    )
    css_classes = (
        "tl-row"
        + (" tl-tight" if is_tight else "")
        + (" tl-top" if row.is_top_level and has_groups else "")
        + (" tl-in-group" if has_groups and not row.is_top_level else "")
    )
    return (
        f'<div class="{css_classes}"><span class="tl-label">{label_html} '
        f'<span class="tl-when">{single_segment_dates}</span>{segment_list}</span>'
        f'<span class="tl-track">{grid}{"".join(drawings)}</span></div>'
    )


def render_timeline_marker(segment: TimelineSegment, label_html: str, axis: TimelineAxis) -> tuple[str, str]:
    """Return a marker in the middle of the segment's first year, and the year as text."""
    date_text = str(segment.first_year)
    hover_text = f'{label_html}: {html.escape(segment.text + " " if segment.text else "")}{date_text}'
    # Half a year's width past the year's start puts the marker in the middle of that year.
    left_percent = axis.percent_across(segment.first_year) + 50 / axis.year_count
    return f'<span class="tl-mark" style="left:{left_percent:.2f}%" title="{hover_text}"></span>', date_text


def render_timeline_bar(
    segment: TimelineSegment,
    segment_position: int,
    label_html: str,
    axis: TimelineAxis,
) -> tuple[str, str]:
    """Return a bar from the start of the segment's first year to the end of its last, and its dates as text.

    Alternate segments on a row get "tl-alt" so that neighbouring bars look different. A bar that starts
    before the chart does is cut off at the left edge and marked "tl-clipped"; its dates still say when it
    really started.
    """
    end_text = "now" if segment.is_open_ended else str(segment.last_year)
    is_one_year = segment.last_year == segment.first_year and not segment.is_open_ended
    date_text = str(segment.first_year) if is_one_year else f"{segment.first_year}–{end_text}"
    note = (" (first found; may be older)" if segment.fades_in else "") + (
        " (last seen; may have continued)" if segment.fades_out else ""
    )
    if segment.fades_in and segment.fades_out and segment.first_year == segment.last_year:
        note = " (the only mention found so far)"
    css_classes = (
        "tl-bar"
        + (" tl-alt" if segment_position % 2 else "")
        + (" tl-fade-in" if segment.fades_in else "")
        + (" tl-fade-out" if segment.fades_out else "")
        + (" tl-open" if segment.is_open_ended else "")
    )
    drawn_first_year = max(segment.first_year, axis.start_year)
    if drawn_first_year > segment.first_year:
        css_classes += " tl-clipped"
    left_percent = axis.percent_across(drawn_first_year)
    width_percent = axis.percent_across(min(segment.last_year, axis.end_year) + 1) - left_percent
    text = html.escape(segment.text)
    hover_text = f'{label_html}{": " + text if text else ""} {date_text}{note}'
    inner_text = f'<span class="tl-seg-text">{text}</span>' if text else ""
    drawing = (
        f'<span class="{css_classes}" style="left:{left_percent:.2f}%;width:{width_percent:.2f}%" '
        f'title="{hover_text}">{inner_text}</span>'
    )
    return drawing, date_text


def footnote_citations(markdown: str, page_path: str, spoiler: bool = False) -> str:
    """Replace each citation with a numbered superscript, and add the References list they point to.

    This is Wikipedia's style: "[1]" in the text, the source at the foot of the page, and a link back to
    each place it was cited. Citing the same source with the same locator again reuses its number;
    differences in spacing inside the locator don't count. Citations inside fenced code blocks are left
    alone, because the contributing pages show them there as examples.

    The References list goes just above the page's "Last reviewed" footer if it has one, otherwise at the
    end. With spoiler set, it goes in a collapsed "??? danger" box instead of under a heading.
    """
    references: dict[tuple[str, str], FootnoteReference] = {}

    def replace_citation(citation: re.Match) -> str:
        """Return the footnote mark for one citation, numbering its source if this is its first use."""
        reference_identity = (citation["key"], " ".join(citation["locator"].split()))
        if reference_identity not in references:
            references[reference_identity] = FootnoteReference(
                len(references) + 1, resolve_citation(citation, page_path)
            )
        reference = references[reference_identity]
        reference.use_count += 1
        return render_footnote_mark(reference)

    pieces = CODE_FENCE_PATTERN.split(markdown)
    for piece_position in range(0, len(pieces), 2):  # even positions are outside code fences
        with_marks = CITATION_PATTERN.sub(replace_citation, pieces[piece_position])
        pieces[piece_position] = SPACE_BETWEEN_FOOTNOTE_MARKS_PATTERN.sub("", with_marks)
    markdown = "".join(pieces)
    if not references:
        return markdown

    references_section = render_references_section(references.values(), spoiler)
    footer_position = markdown.rfind(REVIEWED_FOOTER_START)
    if footer_position != -1:
        return markdown[:footer_position].rstrip() + references_section + markdown[footer_position:]
    return markdown.rstrip() + references_section


def render_footnote_mark(reference: FootnoteReference) -> str:
    """Return the superscript "[n]" for the latest use of a reference, linking to its References entry.

    Its id ("cite-ref-<number>-<use>") is what the References entry's back-link for this use points to.
    Hovering over it shows the reference's label.
    """
    number, use_number = reference.number, reference.use_count
    hover_text = html.escape(reference.resolved.label.replace("|", "·"), quote=True)
    css_classes = "cite-ref" if reference.resolved.found else "cite-ref cite-unknown"
    return (
        f'<sup class="{css_classes}" id="cite-ref-{number}-{use_number}">'
        f'<a href="#cite-{number}" title="{hover_text}">[{number}]</a></sup>'
    )


def render_references_section(references: Iterable[FootnoteReference], spoiler: bool) -> str:
    """Return the References heading and numbered list, or with spoiler set the same list in a collapsed box.

    The collapsed box is a Material for MkDocs "???" admonition, whose content must be indented four spaces.
    """
    reference_list = (
        '<ol class="references">\n'
        + "\n".join(render_reference_item(reference) for reference in references)
        + "\n</ol>"
    )
    if spoiler:
        indented_list = "\n".join("    " + line for line in reference_list.split("\n"))
        return '\n\n??? danger "References (spoilers)"\n\n' + indented_list + "\n\n"
    return "\n\n## References { #references }\n\n" + reference_list + "\n\n"


def render_reference_item(reference: FootnoteReference) -> str:
    """Return one References entry: back-links to where it was cited, then its label, linked if it has a url.

    A source cited once gets a single "^". One cited several times gets "^ a b c", one letter per use, as on
    Wikipedia; after the 26th use the letters give way to numbers.
    """
    number, use_count = reference.number, reference.use_count
    if use_count == 1:
        back_links = f'<a class="cite-back" href="#cite-ref-{number}-1" title="Back to the text">^</a>'
    else:
        back_links = "^ " + " ".join(
            f'<a class="cite-back" href="#cite-ref-{number}-{use_number}">'
            f"{string.ascii_lowercase[use_number - 1] if use_number <= 26 else use_number}</a>"
            for use_number in range(1, use_count + 1)
        )
    label = html.escape(reference.resolved.label)
    url = reference.resolved.url
    body = f'<a href="{html.escape(url, quote=True)}">{label}</a>' if url else label
    return f'<li id="cite-{number}">{back_links} {body}</li>'


def on_page_content(page_html: str, page: Page, config: MkDocsConfig, files: Files) -> str:
    """Send each outbound link on the rendered page through the Wayback Machine, unless it is archival or ours.

    A reader then never lands on a dead or changed page. This runs on the finished HTML, so it covers
    citation links and links written by hand alike.
    """
    return EXTERNAL_LINK_PATTERN.sub(lambda link: f'href="{find_archived_link_url(link["url"])}"', page_html)


def find_archived_link_url(url: str) -> str:
    """Return the Wayback Machine address for a link, or the link itself if it starts with a direct prefix.

    The address has no timestamp ("/web/2/<url>"), which the Wayback Machine resolves to its most recent
    capture. A link with "://<prefix>" anywhere in it, such as a Wayback address for another site, is left
    alone too.
    """
    address = re.sub(r"^https?://", "", url)
    if any(address.startswith(prefix) or ("://" + prefix) in url for prefix in DIRECT_LINK_PREFIXES):
        return url
    return f"https://web.archive.org/web/2/{url}"


def resolve_citation(citation: re.Match, page_path: str) -> ResolvedCitation:
    """Return where one citation links and what it says, warning if its key is unknown or it is malformed.

    citation is a CITATION_PATTERN match. page_path is the page it is on, relative to docs/, for the
    warning. The keys in RESOLVER_BY_RULE_KEY are worked out by rule; every other key is looked up in the
    bibliography, as is "[@rhc]" when it doesn't name a post. tools/cite.py calls this for --url.
    """
    rule_resolver = RESOLVER_BY_RULE_KEY.get(citation["key"])
    resolved = rule_resolver(citation, page_path) if rule_resolver else None
    if resolved is not None:
        return resolved
    return resolve_bibliography_citation(citation["key"], citation["locator"].strip(), page_path)


def resolve_wayback_citation(citation: re.Match, page_path: str) -> ResolvedCitation:
    """Return the capture for "[@wb <timestamp> <url> <notes>]", labelled with the site and capture date."""
    locator_words = citation["locator"].strip().split(None, 2)
    if len(locator_words) < 2:
        LOGGER.warning("%s: bad Wayback citation %r", page_path, citation.group())
        return ResolvedCitation(None, citation.group(), "", False)
    timestamp, original_url, *notes = locator_words  # notes is [] or the rest of the locator as one string
    notes_text = notes[0] if notes else ""
    short_address = re.sub(r"^https?://(www\.)?", "", original_url)
    capture_date = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"  # timestamps are YYYYMMDDhhmmss
    label = (
        f"{short_address}, archived {capture_date}" + (f", {notes_text}" if notes_text else "") + " (Wayback Machine)"
    )
    return ResolvedCitation(
        f"https://web.archive.org/web/{timestamp}/{original_url}",
        label,
        f"Wayback Machine capture of {original_url} on {timestamp}",
        True,
    )


def resolve_portal_citation(citation: re.Match, page_path: str) -> ResolvedCitation:
    """Return the Thresher issue for "[@portal <ARK id> <notes>]", at page N if the notes say "p.N".

    The label gives the issue's date when sources/portal-issue-dates.tsv has it.
    """
    locator_words = citation["locator"].strip().split(None, 1)
    if not locator_words:
        LOGGER.warning("%s: bad Portal citation %r", page_path, citation.group())
        return ResolvedCitation(None, citation.group(), "", False)
    ark_id, *notes = locator_words  # notes is [] or the rest of the locator as one string
    notes_text = notes[0] if notes else ""
    page_locator = PAGE_LOCATOR_PATTERN.search(notes_text)
    url = f"https://texashistory.unt.edu/ark:/67531/{ark_id}/"
    if page_locator:
        url += f"m1/{page_locator['page_number']}/"
    issue_date = ISSUE_DATE_BY_ARK_ID.get(ark_id)
    label = (
        "Rice Thresher"
        + (f", {format_issue_date(issue_date)}" if issue_date else "")
        + (f", {notes_text}" if notes_text else "")
    )
    return ResolvedCitation(url, label + " (Portal to Texas History)", f"Portal to Texas History, {ark_id}", True)


def format_issue_date(issue_date: str) -> str:
    """Return a YYYY-MM-DD date as "5 Oct 1984"."""
    year, month, day = issue_date.split("-")
    return f"{int(day)} {MONTH_ABBREVIATIONS[int(month) - 1]} {year}"


def resolve_rice_history_corner_post(citation: re.Match, page_path: str) -> ResolvedCitation | None:
    """Return the post for "[@rhc <YYYY-MM-DD> <slug> <notes>]", or None to look "rhc" up in the bibliography.

    Example: [@rhc 2021-12-10 im-pissed-no-date comment by X, 14 Dec 2021]. A plain [@rhc] cites the blog
    as a whole, through its bibliography entry. page_path is unused; every rule resolver takes it.
    """
    post = RICE_HISTORY_CORNER_POST_PATTERN.match(citation["locator"].strip())
    if not post:
        return None
    year, month, day, slug, notes = (post[group] for group in ("year", "month", "day", "slug", "notes"))
    return ResolvedCitation(
        f"https://ricehistorycorner.com/{year}/{month}/{day}/{slug}/",
        f"Rice History Corner, {year}-{month}-{day}" + (f", {notes}" if notes else ""),
        f"Rice History Corner post {slug} ({year}-{month}-{day})",
        True,
    )


def resolve_woodson_citation(citation: re.Match, page_path: str) -> ResolvedCitation:
    """Return the Woodson Research Center's home page, labelled with the collection, box and folder cited.

    page_path is unused; every rule resolver takes it.
    """
    return ResolvedCitation(
        "https://library.rice.edu/woodson",
        f"Woodson Research Center, {citation['locator'].strip()}",
        "Woodson Research Center, Fondren Library, Rice University",
        True,
    )


def resolve_fondren_citation(citation: re.Match, page_path: str) -> ResolvedCitation:
    """Return the Fondren Digital Collections item for "[@fondren <item URL or path> <label>]".

    The item is a Sallyport issue, a Campanile volume or another scan at digitalcollections.rice.edu,
    which replaced rice.quartexcollections.com in 2026. A path without "http" is taken as relative to that
    site. The label is free text, such as "Sallyport, Spring 1995, p.12".
    """
    locator_words = citation["locator"].strip().split(None, 1)
    if not locator_words:
        LOGGER.warning("%s: bad Fondren citation %r", page_path, citation.group())
        return ResolvedCitation(None, citation.group(), "", False)
    item_address, *label_words = locator_words  # label_words is [] or the rest of the locator as one string
    url = item_address if item_address.startswith("http") else (
        "https://digitalcollections.rice.edu/" + item_address.lstrip("/")
    )
    item_label = label_words[0] if label_words else "Fondren Library Digital Collections item"
    label = item_label + " (Fondren Digital Collections)"
    return ResolvedCitation(url, label, "Fondren Library Digital Collections, Rice University", True)


# The keys resolve_citation works out by rule instead of looking up in the bibliography, and the function
# for each. A function that returns None hands the citation on to the bibliography. Defined here rather
# than with the constants at the top because it names the functions above. tools/cite.py reads it too.
RESOLVER_BY_RULE_KEY = {
    "wb": resolve_wayback_citation,
    "portal": resolve_portal_citation,
    "rhc": resolve_rice_history_corner_post,
    "woodson": resolve_woodson_citation,
    "fondren": resolve_fondren_citation,
}


def resolve_bibliography_citation(citation_key: str, locator: str, page_path: str) -> ResolvedCitation:
    """Return the bibliography entry's url and title for a citation, or warn that the key is unknown.

    An entry with "parts:" (a book split into several files) links the part the locator names, if it
    names one. A PDF link gets "#page=N" when the locator says "p.N"; an entry is a PDF if it says
    "format: pdf" or its url ends in ".pdf". The url is None when the entry has none; the label then
    says who holds the source, from held_by, so the reader knows where to look.
    """
    entry = BIBLIOGRAPHY.get(citation_key)
    if not entry:
        LOGGER.warning("%s: unknown citation key %r", page_path, citation_key)
        label = f"[@{citation_key}{(' ' + locator) if locator else ''}] (unknown source key)"
        return ResolvedCitation(None, label, "unknown source key", False)
    entry_url = entry.get("url")
    parts = entry.get("parts") or {}
    if parts and locator:
        part_name = find_named_part(parts, locator)
        if part_name is not None:
            entry_url = parts[part_name]
    if entry_url and locator and (entry.get("format") == "pdf" or str(entry_url).lower().endswith(".pdf")):
        page_locator = PAGE_LOCATOR_PATTERN.search(locator)
        if page_locator:
            entry_url = f"{entry_url}#page={page_locator['page_number']}"
    title = str(entry.get("title", citation_key))
    date = entry.get("date", "")
    label = title + (f", {locator}" if locator else "")
    if not entry_url and entry.get("held_by"):
        label += f" (held by {entry['held_by']})"
    return ResolvedCitation(entry_url, label, title + (f" ({date})" if date else ""), True)


def find_named_part(parts: dict, locator: str) -> str | None:
    """Return the name of the entry part that the locator mentions, or None if it names none.

    Names are matched as whole words, ignoring case, so "part 1" does not match "part 10". They are tried
    longest first, so when one name contains another the longer one wins.
    """
    lowercase_locator = locator.lower()
    for part_name in sorted(parts, key=len, reverse=True):
        # The lookbehind and lookahead stop the name matching inside a longer word or number.
        if re.search(r"(?<![a-z0-9])" + re.escape(str(part_name).lower()) + r"(?![a-z0-9])", lowercase_locator):
            return part_name
    return None


def render_citation(citation: re.Match, page_path: str) -> str:
    """Return a citation as an inline bracketed link, the style pages used before numbered footnotes.

    Nothing in the repository calls it at present; footnote_citations replaced it.
    """
    resolved = resolve_citation(citation, page_path)
    return render_inline_citation_link(resolved.url, resolved.label, resolved.hover_title)


def render_inline_citation_link(url: str | None, label: str, hover_title: str) -> str:
    """Return "[label]" as a link styled "cite", or as plain styled text when there is no url."""
    # '|' would split Markdown table cells, so it never appears in rendered citations.
    label = label.replace("|", "·")
    hover_title = hover_title.replace("|", "·")
    label_html, hover_title_html = html.escape(label), html.escape(hover_title, quote=True)
    if url:
        return f'<a class="cite" href="{html.escape(url, quote=True)}" title="{hover_title_html}">[{label_html}]</a>'
    return f'<span class="cite cite-nolink" title="{hover_title_html}">[{label_html}]</span>'


def render_evidence_badge(evidence_class: str) -> str:
    """Return the badge for evidence class P, R or T, with the class's description as hover text."""
    description = html.escape(EVIDENCE_CLASS_DESCRIPTIONS[evidence_class], quote=True)
    return f'<span class="ev ev-{evidence_class}" title="{description}">{evidence_class}</span>'
