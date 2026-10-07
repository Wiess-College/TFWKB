#!/usr/bin/env python3
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

    python3 extract_layout.py <txt> <first_page> <last_page> <source_key> <out.tsv> [--smart] [--plain]
                              [--loc-prefix "part 7 "] [--skip PAGE:N,...] [--furniture REGEX ...]
    python3 extract_layout.py --help          (every option)

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
environment's (/home/claude/familykb/tools). On another machine, edit it or put tools/ on PYTHONPATH,
or it stops at once with ModuleNotFoundError.

The TSV is written only at the end, so if it stops early no TSV has been written or changed. A text
file or --decode file that cannot be read, or a malformed --skip, --bounds or --smart-pages value,
stops it with a traceback; so does a page past the end of the file, after the bounds lines for the
pages before it. A first page of 0 is not an error: it reads the last page of the file. A term whose
line cannot be found again in the column text is given the page of the line after the previous term
found (or of the last line), so check pages in the review output.
"""

import argparse
import functools
import sys
from collections.abc import Callable
from typing import NamedTuple

sys.path.insert(0, __file__.rsplit("/", 1)[0])
# The build environment's copy of tools/, for fix_pdf_text.py. Change it on another machine.
sys.path.insert(0, "/home/claude/familykb/tools")
from fix_pdf_text import fix_line
from gloss import (
    GlossaryEntry,
    load_pages,
    parse_colon,
    parse_indent,
    parse_numbered,
    parse_para,
    parse_plain,
    split_columns,
    split_columns_keep_indent,
    split_columns_smart,
    strip_furniture,
    write_tsv,
)

# Headers, footers and page furniture found in the glossaries, each matched against a whole stripped line.
# They are dropped from each page before it is split, and from each column after it is decoded.
DEFAULT_FURNITURE_PATTERNS = [
    r"\d{1,3}",  # a page number
    r"Conclusions?",
    r".*O-Week \d{4}.*",
    r"(More |Even more )?(Wiess|Rice) [Ss]peak",
    r"WIESS SPEAK",
    r"RICE SPEAK",
    r"Wi speak",
    r"When we said Wiessmen.*",
    r"(ently\. )?Enjoy this glossary.*",
    r"lem\.",
    r"this glossary of Wiess speak.*",
    r"3#\+-\"6\+\"4\$0&.*",  # "When we said..." in the 2011 book's cipher, before decode2011.py decodes it
]

# How each --mode reads a whole glossary's lines into entries.
ENTRY_PARSERS: dict[str, Callable[[list[str]], list[GlossaryEntry]]] = {
    "numbered": parse_numbered,
    "plain": parse_plain,
    "indent": parse_indent,
    "para": lambda lines: parse_para("\n".join(lines), inline=False),
    "inline": lambda lines: parse_para("\n".join(lines), inline=True),
    "colon": lambda lines: parse_colon("\n".join(lines)),
}

# Modes whose term starts a line rather than filling it, so finding the term's page matches the line's start.
TERM_STARTS_LINE_MODES = ("inline", "colon")


class PageLine(NamedTuple):
    """One line of a glossary column, and the PDF page it came from."""

    page_number: int  # counting from 1, as in the PDF
    text: str  # the line as split, decoded and stripped of furniture, with its indentation


def main(arguments: list[str]) -> None:
    """Read the glossary pages, parse their entries, print them with their pages, and write the TSV."""
    options = parse_arguments(arguments)
    pages = load_pages(options.text_file)
    page_lines = read_column_lines(pages, options)
    mode = "plain" if options.plain else options.mode
    entries = ENTRY_PARSERS[mode]([page_line.text for page_line in page_lines])
    rows = locate_entries(entries, page_lines, mode, options)
    write_tsv(options.tsv_file, rows)
    print(f"# wrote {len(rows)} entries to {options.tsv_file}", file=sys.stderr)


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    """Return the command-line options.

    The positional arguments keep their old names (txt, first, last, key, out) in the usage text. The
    help strings are unchanged too; --decode's is out of date, since the decoder files define a
    decode_column function, not a MAP dict.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("text_file", metavar="txt")
    parser.add_argument("first_page", metavar="first", type=int)
    parser.add_argument("last_page", metavar="last", type=int)
    parser.add_argument("source_key", metavar="key")
    parser.add_argument("tsv_file", metavar="out")
    parser.add_argument("--smart", action="store_true")
    parser.add_argument("--smart-pages", default="", help="comma-separated pages to split with the smart splitter")
    parser.add_argument("--plain", action="store_true", help="2010+ style (no '1.' numbering)")
    parser.add_argument(
        "--mode", default="numbered", choices=["numbered", "plain", "indent", "para", "inline", "colon"]
    )
    parser.add_argument("--decode", default="", help="python file defining MAP dict for a glyph cipher")
    parser.add_argument("--ncols", type=int, default=3)
    parser.add_argument("--loc-prefix", default="")
    parser.add_argument("--skip", default="", help="PAGE:N lines to skip at top, comma-separated")
    parser.add_argument("--bounds", default="", help="PAGE:x1/x2 fixed bounds, comma-separated")
    parser.add_argument("--furniture", nargs="*", default=[])
    parser.add_argument("--fix29", action="store_true", help="decode +29 font-shifted runs with tools/fix_pdf_text.py")
    return parser.parse_args(arguments)


def read_column_lines(pages: list[str], options: argparse.Namespace) -> list[PageLine]:
    """Return the lines of every column of the glossary pages in reading order, each with its page.

    Columns are read top to bottom, left to right, page after page, so a definition that runs on into
    the next column or page follows on. The furniture is dropped from the whole page before it is
    split, then again from each column after decoding, since a decoded column can reveal more.
    """
    lines_to_skip_by_page = {
        int(page_number): int(line_count) for page_number, line_count in read_page_settings(options.skip)
    }
    bounds_by_page = {
        int(page_number): [int(bound) for bound in bounds.split("/")]
        for page_number, bounds in read_page_settings(options.bounds)
    }
    furniture_patterns = DEFAULT_FURNITURE_PATTERNS + options.furniture

    page_lines = []
    for page_number in range(options.first_page, options.last_page + 1):
        page = "\n".join(strip_furniture(pages[page_number - 1].splitlines(), furniture_patterns))
        split_page = choose_column_splitter(page_number, options)
        if options.ncols == 1:
            bounds, columns = [], [page]
        else:
            bounds, columns = split_page(
                page,
                bounds=bounds_by_page.get(page_number),
                ncols=options.ncols,
                skip_top=lines_to_skip_by_page.get(page_number, 0),
            )
        print(f"# page {page_number} bounds {bounds}", file=sys.stderr)
        for column in columns:
            column_lines = column.splitlines()
            if options.decode:
                column_lines = load_decoder(options.decode)(column_lines)
            if options.fix29:
                column_lines = [fix_line(line) for line in column_lines]
            page_lines.extend(PageLine(page_number, line) for line in strip_furniture(column_lines, furniture_patterns))
    return page_lines


def read_page_settings(setting_text: str) -> list[tuple[str, str]]:
    """Return the (page, value) pairs of a "PAGE:value,PAGE:value" option, unconverted.

    An item without exactly one colon stops the run with a ValueError traceback.
    """
    page_settings = []
    for item in setting_text.split(","):
        if item:
            page_number, value = item.split(":")
            page_settings.append((page_number, value))
    return page_settings


def choose_column_splitter(page_number: int, options: argparse.Namespace) -> Callable[..., tuple[list[int], list[str]]]:
    """Return the gloss.py function that splits this page into columns.

    The smart splitter is for pages named by --smart-pages, or every page with --smart. Otherwise
    --mode indent keeps each line's indentation, which parse_indent and decode2011.py need. The page
    list is read here, for each page (even with --ncols 1, which then ignores the choice), so a malformed
    --smart-pages stops the run only once a page is read.
    """
    smart_pages = {int(smart_page) for smart_page in options.smart_pages.split(",") if smart_page}
    if options.smart or page_number in smart_pages:
        return split_columns_smart
    if options.mode == "indent":
        return split_columns_keep_indent
    return split_columns


@functools.cache
def load_decoder(decoder_file: str) -> Callable[[list[str]], list[str]]:
    """Return the decode_column function of a decoder file such as decode2011.py, run with exec().

    The file is read in the locale's encoding, not UTF-8, so the "⟨" and "’" in the decoders need a
    UTF-8 locale. It is run the first time a column needs it, then reused.
    """
    with open(decoder_file) as decoder:
        decoder_source = decoder.read()
    decoder_namespace = {}
    exec(decoder_source, decoder_namespace)
    return decoder_namespace["decode_column"]


def locate_entries(
    entries: list[GlossaryEntry],
    page_lines: list[PageLine],
    mode: str,
    options: argparse.Namespace,
) -> list[tuple[str, str, str, str]]:
    """Return a TSV row for each entry with the page its term is on, printing each one for review.

    The parse functions return terms without pages, so each term is looked for again in the column
    lines, searching on from just after the previous term found. A term not found takes the page of the
    line where the search would have started.
    """
    rows = []
    search_from = 0
    for term, definition in entries:
        page_number = None
        for position in range(search_from, len(page_lines)):
            line_text = page_lines[position].text.strip()
            if line_text == term or (mode in TERM_STARTS_LINE_MODES and line_text.startswith(term)):
                page_number, search_from = page_lines[position].page_number, position + 1
                break
        if page_number is None:
            page_number = page_lines[min(search_from, len(page_lines) - 1)].page_number
        rows.append((term, definition, options.source_key, f"{options.loc_prefix}p.{page_number}"))
        print(f"p.{page_number} [{term}] {definition}")
    return rows


if __name__ == "__main__":
    main(sys.argv[1:])
