#!/usr/bin/env python3
<<<<<<< Updated upstream
"""Extract a glossary from a layout-order text file.
=======
"""Extract a glossary from a layout-order text file, writing one TSV row per term with its page.

sources/glossaries/<year>.tsv holds each source's glossary, and every row must say which page its
term is on so it can be cited. Some glossary pages are in two or three columns, so the text extract,
which keeps the layout, has to be cut into columns and parsed in that source's style before the terms
can be read. This script does that for one source, using the helpers in gloss.py. run_all.py runs it for
every source with the options that suit each one; its output then goes through finalize.py.

It reads the text file (pages separated by form feeds, numbered from 1 as in the PDF) and writes one
TSV, replacing any file already there, with the columns term, definition, source_key and locator
("p.N", after --loc-prefix if given). It prints each entry with its page on standard output, for
review, and on standard error one "# page N bounds [...]" line per page (the column starts used)
and a last "# wrote N entries to ..." line.
>>>>>>> Stashed changes

    python3 extract_layout.py <txt> <first_page> <last_page> <source_key> <out.tsv> [--smart] [--plain]
                              [--loc-prefix "part 7 "] [--skip PAGE:N,...] [--furniture REGEX ...]

<<<<<<< Updated upstream
Pages are 1-based PDF pages. Writes a TSV with term, definition, source_key, locator (p.N).
Prints each entry with its page for review.
=======
The options (run_all.py shows which book uses which):

    --mode          numbered (2003-2008), plain, indent (2010, 2011), para (2014), inline (2015-2017),
                    colon (2016 Owlmanac); --plain parses as plain, while --mode still picks the splitter
    --ncols N       columns per page (default 3); 1 reads the page whole and ignores --skip and --bounds
    --bounds        fixed column starts for some pages, "PAGE:x1/x2,..."; other pages find their own
    --smart, --smart-pages
                    split all, or the listed, pages with split_columns_smart, for columns that drift
    --skip          lines to drop at the top of some pages, "PAGE:N,..."
    --furniture     more header and footer lines to drop, as regexes matched against the whole line
    --decode FILE   undo a cipher with decode2011.py or decode2014.py, column by column
    --fix29         decode +29 font-shifted runs with tools/fix_pdf_text.py

Importing gloss.py needs tools/fix_pdf_text.py, and the path added for it below is the build
environment's. On another machine, edit it or put tools/ on PYTHONPATH,
or it stops at once with ModuleNotFoundError.

The TSV is written only at the end, so if it stops early no TSV has been written or changed. A text
file or --decode file that cannot be read, or a malformed --skip, --bounds or --smart-pages value,
stops it with a traceback; so does a page past the end of the file, after the bounds lines for the
pages before it. A first page of 0 is not an error: it reads the last page of the file. A term whose
line cannot be found again in the column text is given the page of the line after the previous term
found (or of the last line), so check pages in the review output.
>>>>>>> Stashed changes
"""
import argparse
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
sys.path.insert(0, "/home/claude/familykb/tools")
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
