#!/usr/bin/env python3
"""Extract a glossary from a layout-order text file.

    python3 extract_layout.py <txt> <first_page> <last_page> <source_key> <out.tsv> [--smart] [--plain]
                              [--loc-prefix "part 7 "] [--skip PAGE:N,...] [--furniture REGEX ...]

Pages are 1-based PDF pages. Writes a TSV with term, definition, source_key, locator (p.N).
Prints each entry with its page for review.
"""
import argparse
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
sys.path.insert(0, "/home/claude/familypedia/tools")
from gloss import (load_pages, split_columns, split_columns_smart, split_columns_keep_indent, strip_furniture,
                   parse_numbered, parse_plain, parse_indent, parse_para, parse_colon, write_tsv)

ap = argparse.ArgumentParser()
ap.add_argument("txt")
ap.add_argument("first", type=int)
ap.add_argument("last", type=int)
ap.add_argument("key")
ap.add_argument("out")
ap.add_argument("--smart", action="store_true")
ap.add_argument("--smart-pages", default="", help="comma-separated pages to split with the smart splitter")
ap.add_argument("--plain", action="store_true", help="2010+ style (no '1.' numbering)")
ap.add_argument("--mode", default="numbered", choices=["numbered","plain","indent","para","inline","colon"])
ap.add_argument("--decode", default="", help="python file defining MAP dict for a glyph cipher")
ap.add_argument("--ncols", type=int, default=3)
ap.add_argument("--loc-prefix", default="")
ap.add_argument("--skip", default="", help="PAGE:N lines to skip at top, comma-separated")
ap.add_argument("--bounds", default="", help="PAGE:x1/x2 fixed bounds, comma-separated")
ap.add_argument("--furniture", nargs="*", default=[])
ap.add_argument("--fix29", action="store_true", help="decode +29 font-shifted runs with tools/fix_pdf_text.py")
a = ap.parse_args()

pages = load_pages(a.txt)
skips = {int(k): int(v) for k, v in (x.split(":") for x in a.skip.split(",") if x)}
fixed = {int(k): [int(z) for z in v.split("/")] for k, v in (x.split(":") for x in a.bounds.split(",") if x)}
furn = [r"\d{1,3}", r"Conclusions?", r".*O-Week \d{4}.*", r"(More |Even more )?(Wiess|Rice) [Ss]peak", r"WIESS SPEAK", r"RICE SPEAK",
        r"Wi speak", r"When we said Wiessmen.*", r"(ently\. )?Enjoy this glossary.*", r"lem\.", r"this glossary of Wiess speak.*",
        r"3#\+-\"6\+\"4\$0&.*"] + a.furniture

stream = []  # (page, line)
for pn in range(a.first, a.last + 1):
    page = "\n".join(strip_furniture(pages[pn - 1].splitlines(), furn))
    smartp = {int(x) for x in a.smart_pages.split(",") if x}
    fn = split_columns_smart if (a.smart or pn in smartp) else (split_columns_keep_indent if a.mode == "indent" else split_columns)
    if a.ncols == 1:
        b, cols = [], [page]
    else:
        b, cols = fn(page, bounds=fixed.get(pn), ncols=a.ncols, skip_top=skips.get(pn, 0))
    print(f"# page {pn} bounds {b}", file=sys.stderr)
    for c in cols:
        cl = c.splitlines()
        if a.decode:
            ns = {}
            exec(open(a.decode).read(), ns)
            cl = ns["decode_column"](cl)
        if a.fix29:
            from fix_pdf_text import fix_line
            cl = [fix_line(l) for l in cl]
        for l in strip_furniture(cl, furn):
            stream.append((pn, l))

lines = [l for _, l in stream]
# parse, then recover the page of each term by locating its term line in the stream
mode = "plain" if a.plain else a.mode
if mode == "numbered":
    entries = parse_numbered(lines)
elif mode == "plain":
    entries = parse_plain(lines)
elif mode == "indent":
    entries = parse_indent(lines)
elif mode == "para":
    entries = parse_para("\n".join(lines), inline=False)
elif mode == "inline":
    entries = parse_para("\n".join(lines), inline=True)
elif mode == "colon":
    entries = parse_colon("\n".join(lines))
rows = []
pos = 0
for term, d in entries:
    pg = None
    for k in range(pos, len(stream)):
        if stream[k][1].strip() == term or (mode in ("inline", "colon") and stream[k][1].strip().startswith(term)):
            pg, pos = stream[k][0], k + 1
            break
    if pg is None:
        pg = stream[min(pos, len(stream) - 1)][0]
    rows.append((term, d, a.key, f"{a.loc_prefix}p.{pg}"))
    print(f"p.{pg} [{term}] {d}")
write_tsv(a.out, rows)
print(f"# wrote {len(rows)} entries to {a.out}", file=sys.stderr)
