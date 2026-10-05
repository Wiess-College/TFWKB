#!/usr/bin/env python3
"""Glossary extraction helpers for the O-Week books.

Usage (as a module from small driver scripts):
    pages = load_pages(path)                 # split on form feeds
    cols  = split_columns(pages[82], bounds) # bounds = [x1, x2] column start offsets, or None → auto
    entries = parse_numbered(lines)          # 2003–2008 style: term line, then "1. …" "2. …"
    entries = parse_plain(lines)             # 2010+ style: term line, then sentence lines
"""
import re
import sys

sys.path.insert(0, "/home/claude/familykb/tools")
from fix_pdf_text import fix_line  # noqa

LIG = {"ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬀ": "ff", "¬": "", "﻿": ""}


def clean(s: str) -> str:
    for k, v in LIG.items():
        s = s.replace(k, v)
    return s


def load_pages(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    return [clean(p) for p in t.split("\f")]


def detect_bounds(lines, ncols=3, min_sep=15):
    """Find column start offsets: the x positions where most word-starts pile up
    (every line of a column starts at the same x). Returns ncols-1 offsets > 0."""
    body = [l.rstrip("\n") for l in lines if l.strip()]
    if not body:
        return []
    width = max(len(l) for l in body)
    hist = [0] * (width + 2)
    for l in body:
        for x, ch in enumerate(l):
            if ch != " " and (x == 0 or l[x - 1] == " "):
                # weight starts preceded by 2+ spaces more (true column starts)
                w = 2 if (x >= 2 and l[x - 2] == " ") or x == 0 else 1
                hist[x] += w
    # merge near-neighbours (±1) into peaks
    peaks = []
    for x in range(len(hist)):
        if hist[x] == 0:
            continue
        s = hist[x] + (hist[x + 1] if x + 1 < len(hist) else 0)
        peaks.append((s, x))
    peaks.sort(reverse=True)
    chosen = []
    for s, x in peaks:
        if all(abs(x - c) >= min_sep for c in chosen):
            chosen.append(x)
        if len(chosen) == ncols:
            break
    chosen = sorted(chosen)
    # the first column starts at 0 (or near it); return the others
    return [c for c in chosen if c > 5][: ncols - 1]


def split_columns(page, bounds=None, ncols=3, skip_top=0, skip_bottom=0):
    lines = page.splitlines()
    if skip_top:
        lines = lines[skip_top:]
    if skip_bottom:
        lines = lines[:-skip_bottom]
    if bounds is None:
        bounds = detect_bounds(lines, ncols)
    edges = [0] + list(bounds) + [10 ** 6]
    cols = [[] for _ in range(len(edges) - 1)]
    for l in lines:
        for i in range(len(edges) - 1):
            seg = l[edges[i]: edges[i + 1]]
            cols[i].append(seg.strip())
    return bounds, ["\n".join(c) for c in cols]


def split_columns_smart(page, bounds=None, ncols=3, skip_top=0, skip_bottom=0, tol=8):
    """Segment-based column assignment for layouts whose columns drift.
    Segments are separated by 2+ spaces; a segment running far past the next column's
    start is split at the space nearest that boundary; each segment goes to the column
    whose start is nearest at or before its own start."""
    lines = page.splitlines()
    if skip_top:
        lines = lines[skip_top:]
    if skip_bottom:
        lines = lines[:-skip_bottom]
    if bounds is None:
        bounds = detect_bounds(lines, ncols)
    starts = [0] + list(bounds)
    cols = [[] for _ in starts]
    for l in lines:
        l = l.rstrip()
        segs = []
        for m in re.finditer(r"\S+(?: \S+)*", l):
            segs.append([m.start(), m.group(0)])
        # split segments that cross a column boundary by a lot
        out = []
        for s, txt in segs:
            cur_s, cur = s, txt
            while True:
                end = cur_s + len(cur)
                nb = [b for b in bounds if b > cur_s + 3 and end > b + tol]
                if not nb:
                    out.append((cur_s, cur))
                    break
                b = nb[0]
                # nearest space to b within the segment
                rel = b - cur_s
                cands = [i for i, ch in enumerate(cur) if ch == " " and abs(i - rel) <= 6]
                if not cands:
                    out.append((cur_s, cur))
                    break
                i = min(cands, key=lambda i: abs(i - rel))
                out.append((cur_s, cur[:i]))
                cur_s, cur = cur_s + i + 1, cur[i + 1:]
        # assign
        row = [""] * len(starts)
        for s, txt in out:
            ci = 0
            for k, cs in enumerate(starts):
                if s + 4 >= cs:
                    ci = k
            row[ci] = (row[ci] + " " + txt).strip() if row[ci] else txt
        for k in range(len(starts)):
            cols[k].append(row[k])
    return bounds, ["\n".join(c) for c in cols]


def strip_furniture(lines, patterns):
    """Drop header/footer lines matching any regex in patterns."""
    out = []
    for l in lines:
        s = l.strip()
        if any(re.fullmatch(p, s) for p in patterns):
            continue
        out.append(l)
    return out


def dehyphen(a: str, b: str) -> str:
    """Join line a (ending with '-') to line b."""
    first = b.split(" ")[0] if b else ""
    if a.endswith("-") and b and b[0].islower() and "-" not in first:
        return a[:-1] + b
    return a + " " + b


def join_lines(lines):
    out = ""
    for l in lines:
        l = l.strip()
        if not l:
            continue
        if not out:
            out = l
        elif out.endswith("-"):
            out = dehyphen(out, l)
        else:
            out += " " + l
    return re.sub(r"\s+", " ", out).strip()


NUM = re.compile(r"^\d\.\s")


def parse_numbered(lines):
    """Entries whose definitions start with '1.'; a term is a non-numbered line followed by a '1.' line."""
    lines = [l.rstrip() for l in lines]
    entries = []
    i = 0
    cur_term, cur_def = None, []
    n = len(lines)
    while i < n:
        l = lines[i].strip()
        nxt = lines[i + 1].strip() if i + 1 < n else ""
        # look past blank lines for the "1." check
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        nxt_ns = lines[j].strip() if j < n else ""
        if l and not NUM.match(l) and nxt_ns.startswith("1.") and not (cur_def and not l[0].isupper() and False):
            # new term
            if cur_term is not None:
                entries.append((cur_term, join_lines(cur_def)))
            cur_term, cur_def = l, []
        elif l:
            cur_def.append(l)
        i += 1
    if cur_term is not None:
        entries.append((cur_term, join_lines(cur_def)))
    return entries


def looks_like_term(l: str) -> bool:
    if not l or len(l) > 40:
        return False
    if NUM.match(l):
        return False
    if l[-1] in ".,;:!?\"”’)":
        return False
    if not (l[0].isupper() or l[0].isdigit() or l[0] in "“\"'("):
        return False
    words = l.split()
    small = {"and", "of", "the", "a", "or", "to", "in", "de", "for", "at", "on", "&", "/"}
    caps = sum(1 for w in words if w[0].isupper() or w[0].isdigit() or w.lower() in small or w[0] in "(“\"'")
    return caps == len(words)


def parse_plain(lines):
    """2010+ style: term on its own line, definition in sentence lines until the next term."""
    lines = [l.rstrip() for l in lines]
    entries = []
    cur_term, cur_def = None, []
    prev = ""
    for raw in lines:
        l = raw.strip()
        if not l:
            prev = ""
            continue
        prev_closed = (prev == "") or prev[-1] in ".!?)”\"’" or prev.endswith("…")
        if looks_like_term(l) and prev_closed and (cur_term is None or cur_def):
            if cur_term is not None:
                entries.append((cur_term, join_lines(cur_def)))
            cur_term, cur_def = l, []
        else:
            if cur_term is None:
                pass
            else:
                cur_def.append(l)
        prev = l
    if cur_term is not None:
        entries.append((cur_term, join_lines(cur_def)))
    return entries


def parse_colon(text: str):
    """Owlmanac style: 'Term: definition' paragraphs separated by blank lines; a paragraph may wrap."""
    paras = re.split(r"\n\s*\n", text)
    entries = []
    for p in paras:
        p = join_lines(p.splitlines())
        m = re.match(r"^([^:]{1,60}):\s*(.*)$", p)
        if m:
            entries.append((m.group(1).strip(), m.group(2).strip()))
        elif entries:
            entries[-1] = (entries[-1][0], (entries[-1][1] + " " + p).strip())
    return entries


def write_tsv(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("term\tdefinition\tsource_key\tlocator\n")
        for term, d, key, loc in rows:
            term = term.replace("\t", " ").strip()
            d = d.replace("\t", " ").strip()
            fh.write(f"{term}\t{d}\t{key}\t{loc}\n")


def show(entries):
    for t, d in entries:
        print(f"[{t}] {d}")


def split_columns_keep_indent(page, bounds=None, ncols=3, skip_top=0, skip_bottom=0):
    """Like split_columns but keeps each segment's indentation relative to its column start."""
    lines = page.splitlines()
    if skip_top:
        lines = lines[skip_top:]
    if skip_bottom:
        lines = lines[:-skip_bottom]
    if bounds is None:
        bounds = detect_bounds(lines, ncols)
    edges = [0] + list(bounds) + [10 ** 6]
    cols = [[] for _ in range(len(edges) - 1)]
    for l in lines:
        for i in range(len(edges) - 1):
            seg = l[edges[i]: edges[i + 1]].rstrip()
            cols[i].append(seg)
    # normalise each column so its leftmost text sits at indent 0
    for i, c in enumerate(cols):
        nb = [len(x) - len(x.lstrip()) for x in c if x.strip()]
        base = min(nb) if nb else 0
        cols[i] = [x[base:] if x.strip() else "" for x in c]
    return bounds, ["\n".join(c) for c in cols]


def parse_indent(lines):
    """2010/2011 layout: a term is a line whose next non-blank line is indented further
    (the definition), unless the line itself reads as sentence text."""
    lines = [l.rstrip() for l in lines]
    n = len(lines)
    entries = []
    cur_term, cur_def = None, []
    for i, raw in enumerate(lines):
        l = raw.strip()
        if not l:
            continue
        indent = len(raw) - len(raw.lstrip())
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        nxt = lines[j] if j < n else ""
        nxt_indent = len(nxt) - len(nxt.lstrip())
        nxt_s = nxt.strip()
        is_term = (
            nxt_indent > indent
            and not NUM.match(l)
            and not (NUM.match(nxt_s) and not nxt_s.startswith("1."))
            and (l[-1] not in ".!?”\"" or len(l) <= 12)
            and len(l) <= 45
        )
        if is_term:
            if cur_term is not None:
                entries.append((cur_term, join_lines(cur_def)))
            cur_term, cur_def = l, []
        else:
            if cur_term is not None:
                cur_def.append(l)
    if cur_term is not None:
        entries.append((cur_term, join_lines(cur_def)))
    return entries


def parse_para(text, inline=False, max_term=45):
    """Paragraphs separated by blank lines. inline=False: first line is the term.
    inline=True: the term is the first word of the paragraph (multi-word terms fixed later).
    A paragraph whose first line reads like running text continues the previous entry."""
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    entries = []
    for p in paras:
        ls = [l.strip() for l in p.splitlines() if l.strip()]
        if not ls:
            continue
        first = ls[0]
        if inline:
            body = join_lines(ls)
            m = re.match(r"^(\S+)\s+(.*)$", body)
            term, d = (m.group(1), m.group(2)) if m else (body, "")
            cont = first[0].islower() or (entries and not entries[-1][1].rstrip().endswith((".", "!", "?", "”", "\"", ")", "…")) and len(first.split()) > 1 and first[0].islower())
            if cont and entries:
                entries[-1] = (entries[-1][0], join_lines([entries[-1][1], body]))
            else:
                entries.append((term, d))
        else:
            is_term = len(first) <= max_term and not first[-1] in ".,;" and not first[0].islower() and len(ls) > 1
            if is_term:
                entries.append((first, join_lines(ls[1:])))
            elif entries:
                entries[-1] = (entries[-1][0], join_lines([entries[-1][1]] + ls))
            else:
                entries.append((first, join_lines(ls[1:])))
    return entries
