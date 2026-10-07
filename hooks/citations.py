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
_PORTAL_DATES: dict[str, str] = {}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _nice_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"


def load_portal_dates() -> dict[str, str]:
    path = os.path.join(ROOT, "sources", "portal-issue-dates.tsv")
    out: dict[str, str] = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and parts[0].startswith("metapth") and re.match(r"\d{4}-\d{2}-\d{2}$", parts[1]):
                out[parts[0]] = parts[1]
    return out

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
    global _PORTAL_DATES
    _PORTAL_DATES = load_portal_dates()
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


def resolve_citation(m: re.Match, page_path: str):
    """Return (url, reader_label, hover_title, ok) for one citation."""
    key, locator = m.group(1), (m.group(2) or "").strip()
    if key == "wb":
        parts = locator.split(None, 2)
        if len(parts) < 2:
            log.warning("%s: bad Wayback citation %r", page_path, m.group(0))
            return None, m.group(0), "", False
        ts, url = parts[0], parts[1]
        rest = parts[2] if len(parts) > 2 else ""
        wb = f"https://web.archive.org/web/{ts}/{url}"
        short = re.sub(r"^https?://(www\.)?", "", url)
        label = f"{short}, archived {ts[:4]}-{ts[4:6]}-{ts[6:8]}" + (f", {rest}" if rest else "") + " (Wayback Machine)"
        return wb, label, f"Wayback Machine capture of {url} on {ts}", True
    if key == "portal":
        parts = locator.split(None, 1)
        if not parts:
            log.warning("%s: bad Portal citation %r", page_path, m.group(0))
            return None, m.group(0), "", False
        ark, rest = parts[0], (parts[1] if len(parts) > 1 else "")
        pm = PAGE_RE.search(rest)
        url = f"https://texashistory.unt.edu/ark:/67531/{ark}/"
        if pm:
            url += f"m1/{pm.group(1)}/"
        when = _PORTAL_DATES.get(ark)
        label = "Rice Thresher" + (f", {_nice_date(when)}" if when else "") + (f", {rest}" if rest else "")
        return url, label + " (Portal to Texas History)", f"Portal to Texas History, {ark}", True
    if key == "rhc":
        # [@rhc 2021-12-10 im-pissed-no-date comment by X, 14 Dec 2021]
        pm = re.match(r"(\d{4})-(\d{2})-(\d{2})\s+([a-z0-9-]+)\s*(.*)$", locator)
        if pm:
            y, mo, d, slug, rest = pm.groups()
            url = f"https://ricehistorycorner.com/{y}/{mo}/{d}/{slug}/"
            label = f"Rice History Corner, {y}-{mo}-{d}" + (f", {rest}" if rest else "")
            return url, label, f"Rice History Corner post {slug} ({y}-{mo}-{d})", True
        # fall through: plain [@rhc] cites the blog as a whole
    if key == "woodson":
        return "https://library.rice.edu/woodson", f"Woodson Research Center, {locator}", "Woodson Research Center, Fondren Library, Rice University", True
    e = _BIB.get(key)
    if not e:
        log.warning("%s: unknown citation key %r", page_path, key)
        return None, f"[@{key}{(' ' + locator) if locator else ''}] (unknown source key)", "unknown source key", False
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
    title = str(e.get("title", key))
    date = e.get("date", "")
    label = title + (f", {locator}" if locator else "")
    return url, label, title + (f" ({date})" if date else ""), True



def render_citation(m: re.Match, page_path: str) -> str:
    """Old inline style (kept for the bibliography page and any caller that wants it)."""
    url, label, title, _ = resolve_citation(m, page_path)
    return _link(url, label, title)


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


# ---------------------------------------------------------------------------
# Wikipedia-style citations: each [@...] becomes a superscript number that
# links to a numbered References list at the foot of the page. The same source
# and locator cited again reuses its number. Citations inside fenced code blocks
# are left alone (they are examples on the contributing pages).
# ---------------------------------------------------------------------------
FENCE_RE = re.compile(r"(^```.*?^```[^\n]*$)", re.S | re.M)
ADJ_RE = re.compile(r"(</sup>)[ \t]+(<sup class=\"cite-ref\")")


def footnote_citations(markdown: str, page_path: str, spoiler: bool = False) -> str:
    refs: dict[tuple, dict] = {}
    order: list[tuple] = []

    def sub(m: re.Match) -> str:
        ident = (m.group(1), " ".join((m.group(2) or "").split()))
        if ident not in refs:
            url, label, title, ok = resolve_citation(m, page_path)
            refs[ident] = {"n": len(order) + 1, "url": url, "label": label, "title": title, "ok": ok, "uses": 0}
            order.append(ident)
        r = refs[ident]
        r["uses"] += 1
        n, u = r["n"], r["uses"]
        tip = html.escape(r["label"].replace("|", "·"), quote=True)
        cls = "cite-ref" if r["ok"] else "cite-ref cite-unknown"
        return f'<sup class="{cls}" id="cite-ref-{n}-{u}"><a href="#cite-{n}" title="{tip}">[{n}]</a></sup>'

    pieces = FENCE_RE.split(markdown)
    for i in range(0, len(pieces), 2):  # even pieces are outside code fences
        pieces[i] = ADJ_RE.sub(r"\1\2", CITE_RE.sub(sub, pieces[i]))
    markdown = "".join(pieces)
    if not order:
        return markdown

    items = []
    for ident in order:
        r = refs[ident]
        n, uses = r["n"], r["uses"]
        if uses == 1:
            back = f'<a class="cite-back" href="#cite-ref-{n}-1" title="Back to the text">^</a>'
        else:
            letters = "abcdefghijklmnopqrstuvwxyz"
            back = "^ " + " ".join(
                f'<a class="cite-back" href="#cite-ref-{n}-{k}">{letters[k - 1] if k <= 26 else k}</a>'
                for k in range(1, uses + 1))
        label = html.escape(r["label"])
        body = f'<a href="{html.escape(r["url"], quote=True)}">{label}</a>' if r["url"] else label
        items.append(f'<li id="cite-{n}">{back} {body}</li>')
    block = '<ol class="references">\n' + "\n".join(items) + "\n</ol>"
    if spoiler:
        section = '\n\n??? danger "References (spoilers)"\n\n' + "\n".join("    " + l for l in block.split("\n")) + "\n\n"
    else:
        section = "\n\n## References { #references }\n\n" + block + "\n\n"
    foot = markdown.rfind('<div class="reviewed"')
    if foot != -1:
        return markdown[:foot].rstrip() + section + markdown[foot:]
    return markdown.rstrip() + section


# ---------------------------------------------------------------------------
# Timeline bars (Wikipedia "EasyTimeline" style), from a fenced block:
#
#   ```timeline
#   from: 1985
#   to: now                                (or current, or leave blank, or leave the line out)
#   Talent show in the Commons: 1987-1992
#   Acabowl concert: 1993-2001
#   Shared with Wiess Day: 2010-2011?      (? = last seen; the bar fades out)
#   Wooden War Pig: 2012-now               (still going: arrow. Also -current, -present, or just 2012-)
#   Earliest mention: ?1987-1990           (leading ? = first found; fades in)
#   * Two stages: 2005                     (a marker on its own row)
#   [Vice Presidents]                      (a group heading; or "group: Vice Presidents")
#   Internal VP: ?1993-2006 Executive; 2007-2015 Executive (Internal); 2016- Internal
#                                          (several segments on one row, each with its own label)
#   ```
#
# Rendered as plain HTML + CSS (assets/familykb.css: .tl-*), so it reflows on phones.
# ---------------------------------------------------------------------------
import datetime as _dt
ONGOING = ("now", "today", "current", "present", "ongoing", "")
TL_RE = re.compile(r"^```timeline[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)


def _year(tok: str, now: int) -> int:
    tok = tok.strip()
    return now if tok.lower() in ONGOING else int(tok)


def _parse_span(span: str, now: int):
    """'?1993-2013?' -> (y0, y1, fade_in, fade_out, open_end, is_point) or None."""
    span = span.strip()
    fade_in = span.startswith("?")
    span = span.lstrip("?")
    fade_out = span.endswith("?")
    span = span.rstrip("?").strip()
    a, dash, b = span.partition("-")
    try:
        y0 = _year(a, now)
        open_end = bool(dash) and b.strip().lower() in ONGOING
        y1 = _year(b, now) if dash else y0
    except ValueError:
        return None
    # "?2017?" (seen once, may have run longer either way) is a one-year bar with fades, not a marker
    return y0, y1, fade_in, fade_out, open_end, not dash and not (fade_in or fade_out)


SEG_RE = re.compile(r"^(\??\s*\d{4}\s*(?:-\s*(?:\d{4}|now|today|current|present|ongoing)?)?\s*\??)(?:\s+(.*))?$", re.I)


def render_timeline(body: str, page_path: str) -> str:
    now = _dt.date.today().year
    lo = hi = None
    rows = []  # each: {"group": str} or {"label", "mark", "segs": [...]}
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(from|to)\s*:\s*(\S*)$", line, re.I)
        if m:
            if m.group(1).lower() == "from":
                lo = _year(m.group(2), now)
            else:
                hi = _year(m.group(2), now)
            continue
        g = re.match(r"^(?:group\s*:\s*(.+?)|\[\s*([^\]]+?)\s*\])\s*$", line, re.I)
        if g:
            rows.append({"group": (g.group(1) or g.group(2)).strip()})
            continue
        top = bool(re.match(r"^\[\s*[^\]]+?\s*\]\s*:", line)) or not any("group" in r for r in rows)
        line = re.sub(r"^\[\s*([^\]]+?)\s*\]\s*:", r"\1:", line)  # "[Name]: 1993-" is a group-level row
        mark = line.startswith("*")
        if mark:
            line = line[1:].strip()
        if ":" not in line:
            log.warning("%s: timeline line without ':' %r", page_path, raw)
            continue
        label, spec = line.split(":", 1)
        segs = []
        for part in re.split(r";\s*|,\s*(?=\??\s*\d{4})", spec.strip()):
            part = part.strip()
            if not part:
                continue
            named = re.match(r"^(.*?):\s*(\??\s*\d{4}.*)$", part)
            if named and not re.match(r"^\??\s*\d{4}", part):
                part = f"{named.group(2)} {named.group(1)}"  # "Apprentice: 2025-now" -> "2025-now Apprentice"
            sm = SEG_RE.match(part)
            parsed = _parse_span(sm.group(1), now) if sm else None
            if not parsed:
                log.warning("%s: bad timeline span %r", page_path, raw)
                continue
            y0, y1, fi, fo, oe, point = parsed
            segs.append(dict(y0=y0, y1=y1, fade_in=fi, fade_out=fo, open_end=oe,
                             point=point or mark, text=(sm.group(2) or '').strip().strip('"')))
        if segs:
            rows.append(dict(label=label.strip(), segs=segs, top=top))
    bars = [sg for r in rows if "segs" in r for sg in r["segs"]]
    if not bars:
        return ""
    lo = lo if lo is not None else min(b["y0"] for b in bars)
    hi = hi if hi is not None else max(b["y1"] for b in bars)
    hi = max(hi, lo + 1)
    span = hi + 1 - lo

    def pct(y):
        return 100.0 * (y - lo) / span

    step = 5 if span <= 45 else 10
    first = lo if lo % step == 0 else lo + (step - lo % step)
    ticks = "".join(f'<span class="tl-tick{" tl-minor" if y % (2 * step) else ""}" style="left:{pct(y):.2f}%">{y}</span>' for y in range(first, hi + 1, step))
    grid = "".join(f'<span class="tl-grid" style="left:{pct(y):.2f}%"></span>' for y in range(first, hi + 1, step))
    out = ['<div class="tl" role="img" aria-label="Timeline chart; the same dates are in the Timeline table below">',
           f'<div class="tl-row tl-axis"><span class="tl-label"></span><span class="tl-track">{ticks}</span></div>']
    grouped = any("group" in r for r in rows)
    for r in rows:
        if "group" in r:
            out.append(f'<div class="tl-row tl-group"><span class="tl-label">{html.escape(r["group"])}</span><span class="tl-track">{grid}</span></div>')
            continue
        lab = html.escape(r["label"])
        parts, whens = [], []
        for k, sg in enumerate(r["segs"]):
            if sg["point"]:
                when = str(sg["y0"])
                tip = f'{lab}: {html.escape(sg["text"] + " " if sg["text"] else "")}{when}'
                parts.append(f'<span class="tl-mark" style="left:{pct(sg["y0"]) + 50 / span:.2f}%" title="{tip}"></span>')
            else:
                end = "now" if sg["open_end"] else str(sg["y1"])
                when = f'{sg["y0"]}–{end}' if sg["y1"] != sg["y0"] or sg["open_end"] else str(sg["y0"])
                note = (" (first found; may be older)" if sg["fade_in"] else "") + (" (last seen; may have continued)" if sg["fade_out"] else "")
                if sg["fade_in"] and sg["fade_out"] and sg["y0"] == sg["y1"]:
                    note = " (the only mention found so far)"
                cls = "tl-bar" + (" tl-alt" if k % 2 else "") + (" tl-fade-in" if sg["fade_in"] else "") \
                    + (" tl-fade-out" if sg["fade_out"] else "") + (" tl-open" if sg["open_end"] else "")
                y0c = max(sg["y0"], lo)
                if y0c > sg["y0"]:
                    cls += " tl-clipped"
                left, width = pct(y0c), pct(min(sg["y1"], hi) + 1) - pct(y0c)
                text = html.escape(sg["text"])
                tip = f'{lab}{": " + text if text else ""} {when}{note}'
                inner = f'<span class="tl-seg-text">{text}</span>' if text else ""
                parts.append(f'<span class="{cls}" style="left:{left:.2f}%;width:{width:.2f}%" title="{tip}">{inner}</span>')
            whens.append(when)
        when_all = html.escape(", ".join(whens)) if len(r["segs"]) == 1 else ""
        seg_list = ""
        if len(r["segs"]) > 1:
            seg_list = '<span class="tl-seg-list">' + " · ".join(
                html.escape(f'{w}{" " + sg["text"] if sg["text"] else ""}') for w, sg in zip(whens, r["segs"])) + "</span>"
        tight = len(r["segs"]) > 1 and any((s2["y1"] - max(s2["y0"], lo) + 1) < 4 and not s2["point"] for s2 in r["segs"])
        cls = "tl-row" + (" tl-tight" if tight else "") + (" tl-top" if r.get("top") and grouped else "") + (" tl-in-group" if grouped and not r.get("top") else "")
        out.append(f'<div class="{cls}"><span class="tl-label">{lab} <span class="tl-when">{when_all}</span>{seg_list}</span>'
                   f'<span class="tl-track">{grid}{"".join(parts)}</span></div>')
    out.append('<div class="tl-key"><span class="tl-key-solid"></span> in the sources '
               '<span class="tl-key-fade"></span> may reach further: earliest or latest mention found so far '
               '<span class="tl-key-open"></span> still going</div>')
    out.append("</div>")
    return "\n".join(out)

def on_page_markdown(markdown: str, page, config, files):
    path = page.file.src_path
    if "<!-- BIBLIOGRAPHY -->" in markdown:
        markdown = markdown.replace("<!-- BIBLIOGRAPHY -->", render_bibliography())
    markdown = TL_RE.sub(lambda m: render_timeline(m.group(1), path), markdown)
    markdown = footnote_citations(markdown, path, spoiler="??? danger" in markdown)
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
