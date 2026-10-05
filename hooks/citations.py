"""MkDocs hook: citations, evidence tags and the generated bibliography.

Citation short forms (see docs/contributing/citing.md):

    [@key]                     a source from sources/bibliography/*.yaml
    [@key p.14]                with a locator (free text; "p.N" on a PDF adds #page=N)
    [@wb 20070709182921 http://teamwiess.com/x.html]   a Wayback capture
    [@portal metapth245573 p.27]                        a Portal to Texas History page (Thresher)
    [@woodson UA0079 box 3 folder 12]                   Woodson Research Center item

Evidence tags [P] [R] [T] become styled badges (see docs/sources/evidence-classes.md).

Unknown keys are logged as warnings, so `mkdocs build --strict` fails on them.
The page sources/bibliography.md is generated from the YAML at build time
wherever it contains the marker <!-- BIBLIOGRAPHY -->.
"""
from __future__ import annotations

import glob
import html
import logging
import os
import re
from collections import defaultdict

import yaml

log = logging.getLogger("mkdocs.plugins.familykb.citations")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIB_DIR = os.path.join(ROOT, "sources", "bibliography")

_BIB: dict[str, dict] = {}

EVIDENCE = {
    "P": "Primary / contemporary source, read directly",
    "R": "Retrospective account (who said it, and when)",
    "T": "Testimony / memory (who, class year, date of the comment)",
}

TYPE_LABELS = {
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


def load_bibliography() -> dict[str, dict]:
    bib: dict[str, dict] = {}
    for path in sorted(glob.glob(os.path.join(BIB_DIR, "*.yaml"))):
        with open(path, encoding="utf-8") as fh:
            entries = yaml.safe_load(fh) or []
        for e in entries:
            key = e.get("key")
            if not key:
                log.warning("bibliography entry without key in %s: %r", path, e)
                continue
            if key in bib:
                log.warning("duplicate bibliography key %r (%s)", key, path)
            e["_file"] = os.path.basename(path)
            bib[key] = e
    return bib


def on_config(config):
    global _BIB
    _BIB = load_bibliography()
    log.info("familykb: %d bibliography entries", len(_BIB))
    return config


CITE_RE = re.compile(r"\[@([A-Za-z0-9][A-Za-z0-9._:-]*)((?:\s+[^\]]*)?)\]")
EVID_RE = re.compile(r"\[([PRT])\](?!\()")
PAGE_RE = re.compile(r"\bp\.?\s*(\d+)")


def _link(url: str | None, label: str, title: str) -> str:
    # '|' would split Markdown table cells, so it never appears in rendered citations
    label = label.replace("|", "·")
    title = title.replace("|", "·")
    label_h, title_h = html.escape(label), html.escape(title, quote=True)
    if url:
        return f'<a class="cite" href="{html.escape(url, quote=True)}" title="{title_h}">[{label_h}]</a>'
    return f'<span class="cite cite-nolink" title="{title_h}">[{label_h}]</span>'


def render_citation(m: re.Match, page_path: str) -> str:
    key, locator = m.group(1), (m.group(2) or "").strip()
    if key == "wb":
        parts = locator.split(None, 2)
        if len(parts) < 2:
            log.warning("%s: bad Wayback citation %r", page_path, m.group(0))
            return m.group(0)
        ts, url = parts[0], parts[1]
        rest = parts[2] if len(parts) > 2 else ""
        wb = f"https://web.archive.org/web/{ts}/{url}"
        short = re.sub(r"^https?://(www\.)?", "", url)
        label = f"{short} · {ts[:4]}-{ts[4:6]}-{ts[6:8]}" + (f" · {rest}" if rest else "")
        return _link(wb, label, f"Wayback Machine capture of {url} on {ts}")
    if key == "portal":
        parts = locator.split(None, 1)
        if not parts:
            log.warning("%s: bad Portal citation %r", page_path, m.group(0))
            return m.group(0)
        ark, rest = parts[0], (parts[1] if len(parts) > 1 else "")
        pm = PAGE_RE.search(rest)
        url = f"https://texashistory.unt.edu/ark:/67531/{ark}/"
        if pm:
            url += f"m1/{pm.group(1)}/"
        return _link(url, f"Portal {ark}" + (f" {rest}" if rest else ""), "The Portal to Texas History (UNT)")
    if key == "rhc":
        # [@rhc 2021-12-10 im-pissed-no-date comment by X, 14 Dec 2021]
        pm = re.match(r"(\d{4})-(\d{2})-(\d{2})\s+([a-z0-9-]+)\s*(.*)$", locator)
        if pm:
            y, mo, d, slug, rest = pm.groups()
            url = f"https://ricehistorycorner.com/{y}/{mo}/{d}/{slug}/"
            label = f"Rice History Corner {y}-{mo}-{d}" + (f" · {rest}" if rest else "")
            return _link(url, label, f"Rice History Corner post {slug} ({y}-{mo}-{d})")
        # fall through: plain [@rhc] cites the blog as a whole
    if key == "woodson":
        return _link("https://library.rice.edu/woodson", f"Woodson {locator}", "Woodson Research Center, Fondren Library, Rice University")
    e = _BIB.get(key)
    if not e:
        log.warning("%s: unknown citation key %r", page_path, key)
        return f'<span class="cite cite-unknown" title="unknown source key">[@{html.escape(key)}{(" " + html.escape(locator)) if locator else ""}]</span>'
    url = e.get("url")
    parts = e.get("parts") or {}
    if parts and locator:
        low = locator.lower()
        # longest matching part name wins ("part 1" must not match "part 10")
        for name in sorted(parts, key=len, reverse=True):
            if re.search(r"(?<![a-z0-9])" + re.escape(str(name).lower()) + r"(?![a-z0-9])", low):
                url = parts[name]
                break
    if url and locator and (e.get("format") == "pdf" or str(url).lower().endswith(".pdf")):
        pm = PAGE_RE.search(locator)
        if pm:
            url = f"{url}#page={pm.group(1)}"
    title = e.get("title", key)
    date = e.get("date", "")
    label = key + (f" {locator}" if locator else "")
    return _link(url, label, f"{title}" + (f" ({date})" if date else ""))


def render_evidence(m: re.Match) -> str:
    c = m.group(1)
    return f'<span class="ev ev-{c}" title="{html.escape(EVIDENCE[c], quote=True)}">{c}</span>'


def _fmt_entry(e: dict) -> str:
    key = e["key"]
    title = html.escape(str(e.get("title", key)))
    url = e.get("url")
    head = f'<a href="{html.escape(url, quote=True)}">{title}</a>' if url else title
    bits = []
    if e.get("date"):
        bits.append(html.escape(str(e["date"])))
    if e.get("author"):
        bits.append(html.escape(str(e["author"])))
    if e.get("evidence"):
        bits.append(render_evidence(re.match(r"\[([PRT])\]", f"[{e['evidence']}]")))
    meta = " · ".join(bits)
    lines = [f'<dt id="{html.escape(key)}"><code>{html.escape(key)}</code>—{head}' + (f' <small>{meta}</small>' if meta else "") + "</dt>"]
    dd = []
    if e.get("notes"):
        dd.append(html.escape(str(e["notes"]).strip()))
    extra = []
    if e.get("local"):
        extra.append(f'corpus: <code>{html.escape(str(e["local"]))}</code>')
    if e.get("pages"):
        extra.append(f'{html.escape(str(e["pages"]))} pp.')
    if e.get("gaps"):
        extra.append(f'gaps: {html.escape(str(e["gaps"]))}')
    if extra:
        dd.append(" · ".join(extra))
    if dd:
        lines.append("<dd>" + "<br>".join(dd) + "</dd>")
    return "\n".join(lines)


def render_bibliography() -> str:
    by_type: dict[str, list] = defaultdict(list)
    for e in _BIB.values():
        by_type[e.get("type", "other")].append(e)
    out = [f"*{len(_BIB)} sources, grouped by kind and sorted by date. Pages cite them by the key in `code`.*\n"]
    order = list(TYPE_LABELS) + sorted(set(by_type) - set(TYPE_LABELS))
    for t in order:
        if t not in by_type:
            continue
        out.append(f"\n## {TYPE_LABELS.get(t, t)}\n")
        out.append("<dl class=\"bib\">")
        for e in sorted(by_type[t], key=lambda x: str(x.get("date", "")) + x["key"]):
            out.append(_fmt_entry(e))
        out.append("</dl>")
    return "\n".join(out)


def on_page_markdown(markdown: str, page, config, files):
    path = page.file.src_path
    if "<!-- BIBLIOGRAPHY -->" in markdown:
        markdown = markdown.replace("<!-- BIBLIOGRAPHY -->", render_bibliography())
    markdown = CITE_RE.sub(lambda m: render_citation(m, path), markdown)
    markdown = EVID_RE.sub(render_evidence, markdown)
    return markdown


# ---------------------------------------------------------------------------
# Every outbound link goes to the Wayback Machine, so a reader never lands on a
# dead or changed page. Links that are already archival, or to our own repo/site,
# are left alone. A link with no timestamp goes to /web/2/<url>, which the
# Wayback Machine resolves to its most recent capture.
# ---------------------------------------------------------------------------
KEEP_DIRECT = (
    "web.archive.org", "archive.org", "texashistory.unt.edu",  # archives in their own right
    "github.com/Wiess-College", "wiess-college.github.io",      # our repo and site
    "squidfunk.github.io", "fonts.googleapis.com", "fonts.gstatic.com",  # theme furniture
    "creativecommons.org",
)
HREF_RE = re.compile(r'href="(https?://[^"]+)"')


def _archive(url: str) -> str:
    bare = re.sub(r"^https?://", "", url)
    if any(bare.startswith(k) or ("://" + k) in url for k in KEEP_DIRECT):
        return url
    return f"https://web.archive.org/web/2/{url}"


def on_page_content(html_out: str, page, config, files):
    return HREF_RE.sub(lambda m: f'href="{_archive(m.group(1))}"', html_out)
