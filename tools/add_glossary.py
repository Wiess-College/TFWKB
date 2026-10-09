#!/usr/bin/env python3
"""Add one O-Week book's glossary to sources/glossaries/ from its PDF, as a draft to check by hand.

Every O-Week book ends with a glossary of Wiess words, and sources/glossaries/<source key>.tsv keeps one table per
book, with the columns term, definition, source_key and locator. tools/build_glossary_series.py lines the
tables up into the glossary page. When a book turns up that has no table yet, give this script its PDF and
the pages its glossary is on:

    python3 tools/add_glossary.py ~/Downloads/oweek-2026.pdf --pages 24-27 --year 2026

It walks the whole job:

    1. reads the text of those pages with pdftotext, keeping the layout
    2. if the text comes out garbled, which happens when a book's fonts are broken (the 2011 and 2014 books),
       copies the pages into a small PDF, repairs its fonts with tools/fix_pdf_fonts.py, and reads it again;
       text left in the 2014 book's shifted font is shifted back (SHIFTED_RUN_PATTERN)
    3. drops page numbers, running heads and the "Wiess speak" headings, and cuts each page into its
       columns, finding how many there are on each page
    4. reads the entries: it tries each way a book has set out its glossary (see LAYOUTS) and keeps the one
       that reads best, or the one given with --layout
    5. writes sources/glossaries/oweek-<year>.tsv, with the page each term is on, and prints every entry for
       checking against the PDF, marking the ones that look wrong
    6. prints what changed since the previous book's glossary (tools/diff_glossary.py), which also shows up
       a misread entry, and rebuilds the glossary page (tools/build_glossary_series.py)

Then open the TSV, fix what it got wrong (an entry split in two, two entries run together, a term that
took words from its definition), and run tools/build_glossary_series.py again. The TSV is the record:
fixes go there, not in this script.

How close the draft gets, tried in October 2026 on the PDFs of seven books whose tables were already
finished, counting the finished table's terms that the draft also has: 2007, 2008 (part 7) and 2010, 96-99%;
2015 and 2016, 97-99%; 2014, 95%; 2011, 74%. Most of those have the same definition word for word too.
The 2011 and 2014 books have broken fonts. The repair identifies a glyph by matching its shape against
other fonts in the PDF and fonts installed on the machine, and the test machine (Linux) lacked the Hoefler
Text and Times fonts that two of the 2011 book's fonts need; macOS has them, so on a Mac expect better. A
nickname table set as a table (2015 on) comes out as one entry per college; the finished tables keep it as
one row, "What to call people from…".

    --pages 24-27        the PDF's own page numbers, counting the cover as 1 (what a PDF viewer shows),
                         not the numbers printed on the pages; "24" alone is one page
    --year 2026          the book's year; the table is sources/glossaries/<source key>.tsv, oweek-2026.tsv
    --source-key KEY     the bibliography key each row cites, and the table's file name; oweek-<year> if not given
    --locator-prefix P   put before each "p.N", for a book in parts: --locator-prefix "part 7 "
    --layout NAME        how entries are set out, if the guess is wrong; one of the LAYOUTS names below
    --columns N          columns on every page (1, 2 or 3), if the guess is wrong
    --furniture REGEX    another heading or footer line to drop, matched against the whole line; repeatable
    --replace            overwrite a table that is already there; without it, an existing table stops it

It needs pdftotext (macOS: brew install poppler; Linux: poppler-utils). Repairing fonts also needs PyMuPDF
and fontTools: pip install -r requirements.txt. It checks for each before it needs it, and stops with a
message saying what to install.

It writes only sources/glossaries/<source key>.tsv and what tools/build_glossary_series.py writes, and only after
the entries are read, so a run that stops early changes nothing. If the source key is not in
sources/bibliography/, it says so and prints an entry to add: the site build fails on an unknown key.
Students from the 2023-24 academic year on are not named on the site (STYLE.md, rule 7), and this script
cannot tell who is a student, so check names in the newest books by hand.
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from typing import NamedTuple

from glossary_layouts import (
    GlossaryEntry,
    detect_bounds,
    parse_colon,
    parse_indent,
    parse_numbered,
    parse_para,
    parse_plain,
    replace_ligatures,
    split_columns_keep_indent,
    split_columns_smart,
    strip_furniture,
    write_tsv,
)
from build_glossary_series import find_glossary_files, label_glossary
from repository_folders import REPOSITORY_ROOT

GLOSSARIES_ROOT = os.path.join(REPOSITORY_ROOT, "sources", "glossaries")
BIBLIOGRAPHY_FILES_GLOB = os.path.join(REPOSITORY_ROOT, "sources", "bibliography", "*.yaml")
TOOLS_ROOT = os.path.join(REPOSITORY_ROOT, "tools")

# Lines dropped from every page before it is cut into columns, and from every column after: page numbers,
# running heads, the glossary's own headings, and the sentences that introduce it in the 2003-2017 books.
# Each is matched against a whole stripped line. --furniture adds more.
FURNITURE_PATTERNS = [
    r"\d{1,3}",  # a page number
    r".*O-Week \d{4}.*",  # running head
    r"Conclusions?",
    r"(More |Even more )?(Wiess|Rice|WIESS|RICE) ([Ss]peak|SPEAK)",
    r"Wi speak",
    r"When we said Wiessmen.*",
    r"(ently\. )?Enjoy this glossary.*",
    r"lem\.",
    r"this glossary of Wiess speak.*",
    r"EXTRA RESOURCES",
    r"WIESS",
    r"WIESS COLLEGE O-WEEK \d{4} \| \d+",
    r"Glossary of all things Wiess\..*",
    r"Don’t worry: you’ll catch up quick\.",
    r"Other words that are good to know\.",
]


class Layout(NamedTuple):
    """One way a book sets out its glossary: how to cut its pages into columns and read the entries."""

    description: str  # shown when the layout is chosen, so the reader can tell whether it fits the book
    split_page: Callable[..., tuple[list[int], list[str]]]  # a glossary_layouts.split_columns function
    read_entries: Callable[[list[str]], list[GlossaryEntry]]  # reads all the column lines into entries
    term_starts_line: bool  # whether the term shares its line with the definition's first words
    term_is_first_word: bool = False  # whether the reader takes only the first word as the term


# Every layout the books have used so far, by the --layout name, with the books each read best in testing.
# The order breaks ties in the guess.
LAYOUTS = {
    "plain": Layout(
        "term on its own line, definition below (best for 2007, 2008, 2011, 2014)",
        split_columns_smart,
        parse_plain,
        False,
    ),
    "numbered": Layout(
        'term on its own line, numbered senses "1." "2." below (2003-2008)', split_columns_smart, parse_numbered, False
    ),
    "indent": Layout(
        "term on its own line, definition indented below (best for 2010)",
        split_columns_keep_indent,
        parse_indent,
        False,
    ),
    "para": Layout(
        "term on its own line, entries separated by blank lines",
        split_columns_smart,
        lambda lines: parse_para("\n".join(lines), inline=False),
        False,
    ),
    "colon": Layout(
        '"Term: definition" paragraphs (2016 Owlmanac)',
        split_columns_smart,
        lambda lines: parse_colon("\n".join(lines)),
        True,
    ),
    "inline": Layout(
        "term run into its definition, entries separated by blank lines (2015-2017); a multi-word term "
        "is completed from the terms of earlier glossaries, and otherwise comes out as its first word",
        split_columns_smart,
        lambda lines: parse_para("\n".join(lines), inline=True),
        True,
        True,
    ),
}

# Text whose non-space characters are mostly letters, and whose letters are mostly lowercase, reads as
# English. Text from a broken font fails one test or the other: the 2011 book's comes out mostly punctuation
# ('3#+-"6+"4$0&' for "When we said"), the 2014 book's mostly capitals ("WKH" for "the").
LETTER_SHARE_THRESHOLD = 0.6
LOWERCASE_SHARE_THRESHOLD = 0.6

# A run of text in a font whose codes are shifted 29 below ASCII, as in the 2014 book: "the" comes out as
# "WKH" and a space as the control character U+0003, which ordinary text never has. tools/fix_pdf_fonts.py
# repairs such a font when it can identify its glyphs; this undoes the shift for any it could not. A run is
# characters from the shifted range ("!" to "]", the space, and four ligature glyphs) around at least one
# shifted space.
SHIFTED_RUN_PATTERN = re.compile(r"[\x03!-\]¿-Â]*\x03[\x03!-\]¿-Â]*")
SHIFTED_FONT_OFFSET = 29
LIGATURE_BY_SHIFTED_GLYPH = {"À": "fi", "Á": "fl", "Â": "ffi", "¿": "ff"}

# What makes an entry look misread, checked for each one and used to score each layout in the guess.
LONGEST_LIKELY_TERM = 40  # characters; longer, and the term has probably taken words from its definition
LONGEST_LIKELY_DEFINITION = 600  # characters; longer, and two entries have probably run together

# A column start is trusted when at most this share of the lines crossing it have a word cut in half there:
# a few lines of a column can run into the next column's space, but not many. A column is at least
# NARROWEST_COLUMN characters wide, and a column start is looked for up to COLUMN_START_SEARCH characters
# either side of where the most words start.
MOST_WORDS_CUT_SHARE = 0.1
WORD_START_SHARE = 0.5
NARROWEST_COLUMN = 25
COLUMN_START_SEARCH = 6


class PageLine(NamedTuple):
    """One line of a glossary column, and the PDF page it came from."""

    page_number: int  # counting from 1, as in the PDF
    text: str  # the line as cut, without furniture, keeping its indentation


class GlossaryRow(NamedTuple):
    """One row of the table to write, with the warnings about it printed for review."""

    term: str
    definition: str
    locator: str  # "p.N", after --locator-prefix
    warnings: list[str]  # why the entry looks misread, if it does


def main(arguments: list[str]) -> None:
    """Read one book's glossary pages, write its table, and show what to check."""
    options = parse_arguments(arguments)
    # The table is named for its source, so a glossary from another kind of book (--source-key
    # owlmanac-2016) sits beside the O-Week books without clashing with them.
    glossary_file = os.path.join(GLOSSARIES_ROOT, f"{options.source_key}.tsv")
    check_can_write(glossary_file, options.replace)
    check_command_installed("pdftotext", "macOS: brew install poppler; Linux: install poppler-utils")

    pages = read_glossary_pages(options.pdf_file, options.first_page, options.last_page)
    furniture_patterns = FURNITURE_PATTERNS + options.furniture
    layout_name = options.layout or guess_layout(pages, options, furniture_patterns)
    page_lines = read_column_lines(pages, options, LAYOUTS[layout_name], furniture_patterns)
    entries = read_entries(LAYOUTS[layout_name], page_lines)
    rows = locate_entries(entries, page_lines, LAYOUTS[layout_name], options.locator_prefix)
    if not rows:
        raise SystemExit("No entries found on those pages. Check --pages, or try --layout and --columns.")

    write_tsv(glossary_file, [(row.term, row.definition, options.source_key, row.locator) for row in rows])
    print_review(rows, layout_name, glossary_file)
    check_source_key(options.source_key, options.year)
    show_changes_since_previous_glossary(options.source_key)
    run_tool("build_glossary_series.py")


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    """Return the command-line options, with --pages read into first_page and last_page."""
    parser = argparse.ArgumentParser(
        description="Add one O-Week book's glossary to sources/glossaries/ from its PDF.",
        epilog="Layouts: " + "; ".join(f"{name}: {layout.description}" for name, layout in LAYOUTS.items()),
    )
    parser.add_argument("pdf_file", help="the book's PDF")
    parser.add_argument("--pages", required=True, help='PDF page numbers of the glossary, such as "24-27"')
    parser.add_argument("--year", required=True, help="the book's year; also sets the default --source-key")
    parser.add_argument("--source-key", help="bibliography key each row cites (default oweek-<year>)")
    parser.add_argument("--locator-prefix", default="", help='put before each "p.N", such as "part 7 "')
    parser.add_argument("--layout", choices=list(LAYOUTS), help="how entries are set out, if the guess is wrong")
    parser.add_argument("--columns", type=int, choices=[1, 2, 3], help="columns on every page, if the guess is wrong")
    parser.add_argument("--furniture", action="append", default=[], help="another line to drop, as a regex")
    parser.add_argument("--replace", action="store_true", help="overwrite the table if it is already there")
    options = parser.parse_args(arguments)

    page_range = re.fullmatch(r"(?P<first>\d+)(?:-(?P<last>\d+))?", options.pages)
    if not page_range:
        parser.error(f'--pages should look like "24-27" or "24", not "{options.pages}"')
    options.first_page = int(page_range["first"])
    options.last_page = int(page_range["last"] or page_range["first"])
    if options.last_page < options.first_page:
        parser.error("--pages: the last page comes before the first")
    options.source_key = options.source_key or f"oweek-{options.year}"
    return options


def check_can_write(glossary_file: str, replace: bool) -> None:
    """Stop if the table is already there and --replace was not given."""
    if os.path.exists(glossary_file) and not replace:
        raise SystemExit(
            f"{os.path.relpath(glossary_file, REPOSITORY_ROOT)} is already there. To read the book again "
            "and overwrite it, losing any fixes made by hand, add --replace."
        )


def check_command_installed(command: str, how_to_install: str) -> None:
    """Stop with how to install the command if it is not on the PATH."""
    if shutil.which(command) is None:
        raise SystemExit(f"{command} is not installed. {how_to_install}")


def read_glossary_pages(pdf_file: str, first_page: int, last_page: int) -> list[str]:
    """Return the text of each glossary page in layout order, repairing the fonts first if it is garbled."""
    if not os.path.isfile(pdf_file):
        raise SystemExit(f"No such PDF: {pdf_file}")
    pages = extract_page_text(pdf_file, first_page, last_page)
    if reads_as_english("".join(pages)):
        return [SHIFTED_RUN_PATTERN.sub(unshift_run, page) for page in pages]
    print("Some text comes out garbled, so this book's fonts are broken; repairing them.", file=sys.stderr)
    with tempfile.TemporaryDirectory() as work_folder:
        repaired_file = repair_fonts(pdf_file, first_page, last_page, work_folder)
        # The repaired copy holds only the glossary pages, so it starts at its own page 1.
        pages = extract_page_text(repaired_file, 1, last_page - first_page + 1)
    pages = [SHIFTED_RUN_PATTERN.sub(unshift_run, page) for page in pages]
    if not reads_as_english("".join(pages)):
        print(
            "The text is still garbled after the repair. tools/fix_pdf_fonts.py report says which fonts it "
            "could not identify; give it a copy of the typeface with --ref.",
            file=sys.stderr,
        )
    return pages


def extract_page_text(pdf_file: str, first_page: int, last_page: int) -> list[str]:
    """Return the text of each page in the range, in layout order, with ligatures spelled out."""
    extraction = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", "-f", str(first_page), "-l", str(last_page), pdf_file, "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if extraction.returncode != 0:
        raise SystemExit(f"pdftotext could not read {pdf_file}:\n{extraction.stderr}")
    # pdftotext ends every page with a form feed, so the piece after the last one is empty.
    pages = extraction.stdout.split("\f")[: last_page - first_page + 1]
    return [replace_ligatures(page) for page in pages]


def unshift_run(shifted_run: re.Match) -> str:
    """Return a run of shifted-font text (see SHIFTED_RUN_PATTERN) as the letters it draws."""
    return "".join(
        LIGATURE_BY_SHIFTED_GLYPH.get(character) or chr(ord(character) + SHIFTED_FONT_OFFSET)
        for character in shifted_run.group()
    )


def reads_as_english(text: str) -> bool:
    """Return whether the text reads as English rather than as a broken font's codes.

    Text with any shifted-font space in it (see SHIFTED_RUN_PATTERN) does not, however little; otherwise
    see the thresholds.
    """
    if "\x03" in text:
        return False
    visible_characters = [character for character in text if not character.isspace()]
    letters = [character for character in visible_characters if character.isalpha()]
    if not letters:
        return False
    letter_share = len(letters) / len(visible_characters)
    lowercase_share = sum(letter.islower() for letter in letters) / len(letters)
    return letter_share >= LETTER_SHARE_THRESHOLD and lowercase_share >= LOWERCASE_SHARE_THRESHOLD


def repair_fonts(pdf_file: str, first_page: int, last_page: int, work_folder: str) -> str:
    """Return a copy of the glossary pages with its fonts repaired by tools/fix_pdf_fonts.py.

    Only the glossary pages are copied, so the repair takes a second rather than reading the whole book.
    The repair report is passed on to standard error.
    """
    try:
        import pymupdf  # noqa: PLC0415  (only a garbled book needs it, and requirements.txt does not install it)
    except ImportError:
        raise SystemExit(
            "Repairing the fonts needs PyMuPDF and fontTools: pip install -r requirements.txt"
        ) from None
    pages_file = os.path.join(work_folder, "glossary-pages.pdf")
    repaired_file = os.path.join(work_folder, "glossary-pages-repaired.pdf")
    with pymupdf.open(pdf_file) as book, pymupdf.open() as glossary_pages:
        glossary_pages.insert_pdf(book, from_page=first_page - 1, to_page=last_page - 1)
        glossary_pages.save(pages_file)
    repair = subprocess.run(
        [sys.executable, os.path.join(TOOLS_ROOT, "fix_pdf_fonts.py"), "repair", pages_file, repaired_file],
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(repair.stdout + repair.stderr)
    if repair.returncode != 0:
        raise SystemExit("tools/fix_pdf_fonts.py could not repair the fonts; its messages are above.")
    return repaired_file


def guess_layout(pages: list[str], options: argparse.Namespace, furniture_patterns: list[str]) -> str:
    """Return the name of the layout whose reading has the most entries that look right.

    Each layout's entries are scored: one point for an entry that looks right, minus two for one that looks
    misread (see find_entry_warnings). The scores are printed, so a close call is plain to see.
    """
    scores = {}
    for layout_name, layout in LAYOUTS.items():
        page_lines = read_column_lines(pages, options, layout, furniture_patterns)
        entries = read_entries(layout, page_lines)
        misread_count = sum(1 for entry in entries if find_entry_warnings(entry))
        scores[layout_name] = (len(entries) - misread_count) - 2 * misread_count
    best_layout = max(scores, key=scores.get)
    ranking = ", ".join(f"{name} {score}" for name, score in sorted(scores.items(), key=lambda item: -item[1]))
    print(f"Layout scores: {ranking}", file=sys.stderr)
    return best_layout


def read_column_lines(
    pages: list[str], options: argparse.Namespace, layout: Layout, furniture_patterns: list[str]
) -> list[PageLine]:
    """Return the lines of every column of the glossary pages in reading order, each with its page.

    Columns are read top to bottom, left to right, page after page, so a definition that runs on into the
    next column or page follows on.
    """
    page_lines = []
    for page_offset, page in enumerate(pages):
        page_number = options.first_page + page_offset
        lines = strip_furniture(page.splitlines(), furniture_patterns)
        column_starts = find_column_starts(lines, options.columns)
        if column_starts:
            _, columns = layout.split_page("\n".join(lines), bounds=column_starts, ncols=len(column_starts) + 1)
        else:
            columns = ["\n".join(lines)]
        for column in columns:
            column_lines = strip_furniture(column.splitlines(), furniture_patterns)
            page_lines.extend(PageLine(page_number, line) for line in column_lines)
    return page_lines


def read_entries(layout: Layout, page_lines: list[PageLine]) -> list[GlossaryEntry]:
    """Return the entries read from the column lines, completing first-word terms from earlier glossaries."""
    entries = layout.read_entries([page_line.text for page_line in page_lines])
    if layout.term_is_first_word:
        known_terms = read_known_terms()
        entries = [complete_term(entry, known_terms) for entry in entries]
    return entries


def read_known_terms() -> list[str]:
    """Return every term in sources/glossaries/, longest first, without the [Rice speak] marks."""
    known_terms = set()
    for glossary_file in glob.glob(os.path.join(GLOSSARIES_ROOT, "*.tsv")):
        with open(glossary_file, encoding="utf-8") as glossary:
            next(glossary, None)  # the header row
            for row in glossary:
                term = row.split("\t", 1)[0].replace(" [Rice speak]", "").strip()
                if " " in term:
                    known_terms.add(term)
    return sorted(known_terms, key=len, reverse=True)


def complete_term(entry: GlossaryEntry, known_terms: list[str]) -> GlossaryEntry:
    """Return the entry with its term made the longest earlier term its text starts with, if one is longer.

    The inline layout takes a term's first word only, so "Room Draw Process used to assign rooms" comes
    out as "Room" and "Draw Process used...". Terms of more than one word from the earlier glossaries are
    tried against the start of the text, ignoring case, and a match must end at a space.
    """
    full_text = f"{entry.term} {entry.definition}"
    for known_term in known_terms:
        if full_text.lower().startswith(known_term.lower() + " "):
            return GlossaryEntry(full_text[: len(known_term)], full_text[len(known_term) + 1 :].strip())
    return entry


def find_column_starts(lines: list[str], column_count: int | None) -> list[int]:
    """Return where the page's second and later columns start, as character offsets; empty for one column.

    Candidates come two ways: the offsets glossary_layouts.detect_bounds finds, where the most words start,
    and every offset where at least half the lines reaching past it have a word starting there or just
    after (WORD_START_SHARE), which finds a column of short lines that detect_bounds can miss. Each is moved
    by up to COLUMN_START_SEARCH characters to where the fewest words are cut and the most start. An offset
    is a column start when it cuts few words (MOST_WORDS_CUT_SHARE) and is at least NARROWEST_COLUMN
    characters from the column before: an indented line inside a column also lines words up, but too close
    to the column's start. With --columns, the first column_count - 1 offsets detect_bounds finds are used
    without those checks.
    """
    if column_count is not None:
        return detect_bounds(lines, column_count) if column_count > 1 else []
    width = max((len(line) for line in lines), default=0)
    candidate_starts = set(detect_bounds(lines, ncols=6, min_separation=10))
    candidate_starts |= {
        offset
        for offset in range(NARROWEST_COLUMN, width)
        if share_of_lines_with_word_start(lines, offset, 3) >= WORD_START_SHARE
    }
    nudged_starts = sorted({find_cleanest_cut_near(lines, start) for start in candidate_starts})
    column_starts = []
    for start in nudged_starts:
        previous_start = column_starts[-1] if column_starts else 0
        if share_of_words_cut(lines, start) <= MOST_WORDS_CUT_SHARE and start - previous_start >= NARROWEST_COLUMN:
            column_starts.append(start)
    return column_starts[:2]


def find_cleanest_cut_near(lines: list[str], start: int) -> int:
    """Return the offset near start that cuts the fewest words, then has the most words starting exactly there."""
    nearby_offsets = range(max(1, start - COLUMN_START_SEARCH), start + COLUMN_START_SEARCH + 1)
    return min(
        nearby_offsets,
        key=lambda offset: (
            share_of_words_cut(lines, offset),
            -share_of_lines_with_word_start(lines, offset, 1),
            abs(offset - start),
        ),
    )


def share_of_words_cut(lines: list[str], offset: int) -> float:
    """Return the share of lines reaching past the offset that have no space in the 3 characters ending there.

    A line with no space there has a word running across the cut. Fewer than 5 such lines are too few
    to judge by, and count as every word cut.
    """
    crossing_lines = [line for line in lines if len(line.rstrip()) > offset]
    if len(crossing_lines) < 5:
        return 1.0
    cut_lines = [line for line in crossing_lines if " " not in line[max(0, offset - 2) : offset + 1]]
    return len(cut_lines) / len(crossing_lines)


def share_of_lines_with_word_start(lines: list[str], offset: int, window: int) -> float:
    """Return the share of lines reaching past the offset with a word starting in the window characters from it."""
    crossing_lines = [line for line in lines if len(line.rstrip()) > offset]
    if len(crossing_lines) < 5:
        return 0.0
    starting_lines = [
        line
        for line in crossing_lines
        if any(
            line[position] != " " and line[position - 1] == " "
            for position in range(offset, min(offset + window, len(line)))
        )
    ]
    return len(starting_lines) / len(crossing_lines)


def locate_entries(
    entries: list[GlossaryEntry], page_lines: list[PageLine], layout: Layout, locator_prefix: str
) -> list[GlossaryRow]:
    """Return a row for each entry, with the page its term is on and any warnings about it.

    The layouts' readers return entries without pages, so each term is looked for again in the column
    lines, searching on from just after the previous term found. A term not found takes the page of the
    line where the search would have started, and a warning says so.
    """
    rows = []
    search_from = 0
    for entry in entries:
        warnings = find_entry_warnings(entry)
        page_number = None
        for position in range(search_from, len(page_lines)):
            line_text = page_lines[position].text.strip()
            if line_text == entry.term or (layout.term_starts_line and line_text.startswith(entry.term)):
                page_number, search_from = page_lines[position].page_number, position + 1
                break
        if page_number is None:
            page_number = page_lines[min(search_from, len(page_lines) - 1)].page_number
            warnings.append("page not certain")
        rows.append(GlossaryRow(entry.term, entry.definition, f"{locator_prefix}p.{page_number}", warnings))
    return rows


def find_entry_warnings(entry: GlossaryEntry) -> list[str]:
    """Return why the entry looks misread, if it does: the patterns past books' mistakes have followed."""
    warnings = []
    if not entry.definition:
        warnings.append("no definition")
    if len(entry.term) > LONGEST_LIKELY_TERM:
        warnings.append("long term: words from the definition?")
    if entry.term[:1].islower():
        warnings.append("term starts in lowercase: part of the previous definition?")
    if entry.term[-1:] in ".,;:" and len(entry.term) > 3:
        warnings.append("term ends in punctuation: a sentence, not a term?")
    if len(entry.definition) > LONGEST_LIKELY_DEFINITION:
        warnings.append("long definition: two entries run together?")
    if entry.definition[:1].islower():
        warnings.append("definition starts in lowercase: term cut short?")
    return warnings


def print_review(rows: list[GlossaryRow], layout_name: str, glossary_file: str) -> None:
    """Print every entry with its page, the ones to look at marked "!!", and a summary."""
    print(f"Layout: {layout_name} ({LAYOUTS[layout_name].description})\n")
    for row in rows:
        marker = "!!" if row.warnings else "  "
        print(f"{marker} {row.locator:<8} {row.term}: {shorten(row.definition, 110)}")
        for warning in row.warnings:
            print(f"{'':12}^ {warning}")
    flagged_count = sum(1 for row in rows if row.warnings)
    glossary_path = os.path.relpath(glossary_file, REPOSITORY_ROOT)
    print(f"\nWrote {len(rows)} entries to {glossary_path}; {flagged_count} marked !!.")
    print("Check them against the PDF and fix the TSV by hand. Wrong layout? Run again with --layout and --replace.")


def shorten(text: str, width: int) -> str:
    """Return the text cut to width characters, ending in "…" if it was cut."""
    return text if len(text) <= width else text[: width - 1] + "…"


def check_source_key(source_key: str, year: str) -> None:
    """Print an entry to add to the bibliography if no bibliography file has the source key."""
    key_pattern = re.compile(rf"^- key: {re.escape(source_key)}\s*$", re.MULTILINE)
    for bibliography_file in glob.glob(BIBLIOGRAPHY_FILES_GLOB):
        with open(bibliography_file, encoding="utf-8") as bibliography:
            if key_pattern.search(bibliography.read()):
                return
    print(
        f"\n{source_key} is not in sources/bibliography/, and the site build fails on an unknown key. "
        "Add an entry like this to sources/bibliography/oweek-books.yaml, with the book's real details:\n\n"
        f"- key: {source_key}\n  title: Wiess O-Week Book {year}\n  type: oweek-book\n  format: pdf\n"
        f"  date: {year}\n  url: <where the PDF can be found>\n"
    )


def show_changes_since_previous_glossary(source_key: str) -> None:
    """Print what the new glossary added, dropped and reworded since the table before it, if there is one.

    Tables are labelled and ordered as the glossary page orders them (build_glossary_series.py).
    """
    labels = list(find_glossary_files())
    label = label_glossary(source_key)
    position = labels.index(label)
    if position > 0:
        print()
        run_tool("diff_glossary.py", labels[position - 1], label)


def run_tool(tool_name: str, *arguments: str) -> None:
    """Run another script in tools/ with this Python, letting it print as it goes."""
    subprocess.run([sys.executable, os.path.join(TOOLS_ROOT, tool_name), *arguments], check=False)


if __name__ == "__main__":
    main(sys.argv[1:])
