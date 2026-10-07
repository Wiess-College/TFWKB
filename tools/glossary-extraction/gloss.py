#!/usr/bin/env python3
"""Split O-Week book glossary pages into columns and parse them into terms and definitions.

Every O-Week book ends with a glossary of Wiess words, and sources/glossaries/ keeps one TSV per year.
The glossary pages are laid out in two or three columns, and each year's book sets out a term and its
definition differently, so the text layer cannot be read straight down. These helpers do the shared
work for extract_layout.py, which imports load_pages, the three split_columns functions,
strip_furniture, the five parse functions and write_tsv:

    pages = load_pages(text_file)                    # split on form feeds
    bounds, columns = split_columns(pages[82])       # bounds = column start offsets, found if not given
    entries = parse_numbered(lines)                  # 2003-2008: term line, then "1. ..." "2. ..."
    entries = parse_plain(lines)                     # 2010 on: term line, then sentence lines
    write_tsv(tsv_file, rows)

Only write_tsv writes a file, the one it is given. Importing this file needs tools/fix_pdf_text.py on
the import path; the line below adds this repository's tools/ folder, found from this file's own place.

A text file is read as UTF-8, with bytes that are not UTF-8 replaced by "�". Text the parse functions
cannot place is dropped (lines before the first term) or added to the previous definition.
"""

import os
import re
import sys
from typing import NamedTuple

# This repository's tools/ folder, one level up from this file's folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# fix_line is not used here. The import is kept so that importing this file still needs fix_pdf_text.py,
# and fails without it, as it always has.
from fix_pdf_text import fix_line

# Ligatures and invisible characters in the text layer: each is replaced by its letters, or removed.
# "¬" is a soft-hyphen mark at a line break, and U+FEFF is a byte-order mark.
LIGATURE_REPLACEMENTS = {"ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬀ": "ff", "¬": "", "﻿": ""}

# A numbered definition: one digit, a full stop and a space or other whitespace ("1. ", "2. ").
NUMBERED_DEFINITION_PATTERN = re.compile(r"^\d\.\s")

# Small words that may be lowercase inside a term such as "Rice and Wiess".
TERM_LOWERCASE_WORDS = {"and", "of", "the", "a", "or", "to", "in", "de", "for", "at", "on", "&", "/"}

# Characters that may open a term instead of a capital or a digit: an opening quotation mark or bracket.
TERM_OPENING_CHARACTERS = "“\"'("

# Characters that end a sentence: the line after one may start a new term.
SENTENCE_ENDINGS = ".!?)”\"’"

# A segment of a line in split_columns_smart: words joined by single spaces. Two or more spaces end it.
SEGMENT_PATTERN = re.compile(r"\S+(?: \S+)*")

# parse_colon's "Term: definition": a term of 1 to 60 characters with no colon in it, then the colon.
COLON_ENTRY_PATTERN = re.compile(r"^(?P<term>[^:]{1,60}):\s*(?P<definition>.*)$")

# parse_para's inline entry: the first word is the term, and the rest is the definition.
INLINE_ENTRY_PATTERN = re.compile(r"^(?P<term>\S+)\s+(?P<definition>.*)$")

# A blank line, possibly with spaces on it: what separates paragraphs.
PARAGRAPH_BREAK_PATTERN = re.compile(r"\n\s*\n")


class GlossaryEntry(NamedTuple):
    """One glossary term and its definition, as the parse functions return them."""

    term: str  # the term as printed, stripped of surrounding space
    definition: str  # the definition's lines joined into one line, hyphenated line breaks rejoined


class Segment(NamedTuple):
    """A run of words on one line of a page, and where it starts."""

    start: int  # character offset of its first character in the line
    text: str  # the words, joined by single spaces


def load_pages(text_file: str) -> list[str]:
    """Return the file's pages, split at form feeds, with ligatures spelled out."""
    with open(text_file, encoding="utf-8", errors="replace") as text:
        extract_text = text.read()
    return [replace_ligatures(page) for page in extract_text.split("\f")]


def replace_ligatures(page_text: str) -> str:
    """Return the text with each ligature spelled out and each soft-hyphen mark and byte-order mark removed."""
    for ligature, replacement in LIGATURE_REPLACEMENTS.items():
        page_text = page_text.replace(ligature, replacement)
    return page_text


def split_columns(
    page: str,
    bounds: list[int] | None = None,
    ncols: int = 3,
    skip_top: int = 0,
    skip_bottom: int = 0,
) -> tuple[list[int], list[str]]:
    """Return the column bounds used and the page's text cut into columns at fixed character offsets.

    Every line is cut at the same offsets, and each piece is stripped. bounds are the offsets where the
    second and later columns start; if not given they are found by detect_bounds, looking for ncols
    columns (named like extract_layout.py's --ncols). skip_top and skip_bottom drop that many lines
    first. Each column comes back as one string, one line per page line, blank
    where the column was empty, so line numbers still match between columns.
    """
    lines, bounds = trim_and_find_bounds(page, bounds, ncols, skip_top, skip_bottom)
    edges = [0, *bounds, 10**6]
    columns = [[] for _ in range(len(edges) - 1)]
    for line in lines:
        for column_number in range(len(edges) - 1):
            columns[column_number].append(line[edges[column_number] : edges[column_number + 1]].strip())
    return bounds, ["\n".join(column) for column in columns]


def split_columns_keep_indent(
    page: str,
    bounds: list[int] | None = None,
    ncols: int = 3,
    skip_top: int = 0,
    skip_bottom: int = 0,
) -> tuple[list[int], list[str]]:
    """Return the column bounds used and the page cut into columns as split_columns does, keeping indentation.

    parse_indent and decode2011.py tell a term from its definition by how far each line is indented, so
    each piece keeps its leading spaces; then each column is shifted left so its least indented line
    starts at 0.
    """
    lines, bounds = trim_and_find_bounds(page, bounds, ncols, skip_top, skip_bottom)
    edges = [0, *bounds, 10**6]
    columns = [[] for _ in range(len(edges) - 1)]
    for line in lines:
        for column_number in range(len(edges) - 1):
            columns[column_number].append(line[edges[column_number] : edges[column_number + 1]].rstrip())
    for column_number, column in enumerate(columns):
        text_indents = [indent_width(piece) for piece in column if piece.strip()]
        least_indent = min(text_indents) if text_indents else 0
        columns[column_number] = [piece[least_indent:] if piece.strip() else "" for piece in column]
    return bounds, ["\n".join(column) for column in columns]


def split_columns_smart(
    page: str,
    bounds: list[int] | None = None,
    ncols: int = 3,
    skip_top: int = 0,
    skip_bottom: int = 0,
    tolerance: int = 8,
) -> tuple[list[int], list[str]]:
    """Return the column bounds used and the page cut into columns for layouts whose columns drift.

    In some books a column's lines do not all start at the same offset, so a fixed cut slices words in
    half. Here each line is broken into segments at runs of two or more spaces. A segment that runs more
    than tolerance characters past the next column's start is split at the space nearest that start.
    Each segment then goes to the last column that starts no more than 4 characters after it. The
    arguments are as for split_columns.
    """
    lines, bounds = trim_and_find_bounds(page, bounds, ncols, skip_top, skip_bottom)
    column_starts = [0, *bounds]
    columns = [[] for _ in column_starts]
    for line in lines:
        segments = []
        for segment_match in SEGMENT_PATTERN.finditer(line.rstrip()):
            segments.extend(split_segment_at_bounds(segment_match.start(), segment_match.group(), bounds, tolerance))
        row = assign_segments_to_columns(segments, column_starts)
        for column_number in range(len(column_starts)):
            columns[column_number].append(row[column_number])
    return bounds, ["\n".join(column) for column in columns]


def split_segment_at_bounds(start: int, text: str, bounds: list[int], tolerance: int) -> list[Segment]:
    """Return the segment cut wherever it runs more than tolerance characters past a column start.

    Each cut is at the space nearest the column start, within 6 characters of it. With no space that
    close, the rest of the segment is left whole. A bound within 3 characters of the segment's start is
    the segment's own column, so it is never cut there.
    """
    pieces = []
    while True:
        end = start + len(text)
        crossed_bounds = [bound for bound in bounds if bound > start + 3 and end > bound + tolerance]
        if not crossed_bounds:
            pieces.append(Segment(start, text))
            return pieces
        bound_offset = crossed_bounds[0] - start  # where the column starts, counted within this segment
        nearby_spaces = [
            position
            for position, character in enumerate(text)
            if character == " " and abs(position - bound_offset) <= 6
        ]
        if not nearby_spaces:
            pieces.append(Segment(start, text))
            return pieces
        cut = min(nearby_spaces, key=lambda position: abs(position - bound_offset))
        pieces.append(Segment(start, text[:cut]))
        start, text = start + cut + 1, text[cut + 1 :]


def assign_segments_to_columns(segments: list[Segment], column_starts: list[int]) -> list[str]:
    """Return one line's text for each column, joining with a space the segments that land in the same column."""
    row = [""] * len(column_starts)
    for segment in segments:
        column_number = 0
        for candidate_number, column_start in enumerate(column_starts):
            if segment.start + 4 >= column_start:
                column_number = candidate_number
        if row[column_number]:
            row[column_number] = (row[column_number] + " " + segment.text).strip()
        else:
            row[column_number] = segment.text
    return row


def strip_furniture(lines: list[str], patterns: list[str]) -> list[str]:
    """Return the lines without the headers and footers: lines that, stripped, match one of the regexes whole."""
    return [line for line in lines if not any(re.fullmatch(pattern, line.strip()) for pattern in patterns)]


def parse_numbered(lines: list[str]) -> list[GlossaryEntry]:
    """Return the entries of a 2003-2008 glossary, where definitions are numbered "1.", "2.", and so on.

    A term is any unnumbered line whose next non-blank line starts with "1.". Every other non-blank line
    belongs to the definition before it; lines before the first term are dropped.
    """
    lines = [line.rstrip() for line in lines]
    entries = []
    term, definition_lines = None, []
    for position, line in enumerate(lines):
        text = line.strip()
        next_text = find_next_text_line(lines, position).strip()
        if text and not NUMBERED_DEFINITION_PATTERN.match(text) and next_text.startswith("1."):
            if term is not None:
                entries.append(GlossaryEntry(term, join_lines(definition_lines)))
            term, definition_lines = text, []
        elif text:
            definition_lines.append(text)
    if term is not None:
        entries.append(GlossaryEntry(term, join_lines(definition_lines)))
    return entries


def parse_plain(lines: list[str]) -> list[GlossaryEntry]:
    """Return the entries of a glossary set as a term on its own line, then sentence lines (2010 on).

    A line starts a new term when it looks like one (see looks_like_term), the line before it was blank
    or ended a sentence, and the previous term already has some definition. Lines before the first term
    are dropped.
    """
    entries = []
    term, definition_lines = None, []
    previous_text = ""
    for line in lines:
        text = line.strip()
        if not text:
            previous_text = ""
            continue
        previous_ended_sentence = (
            previous_text == "" or previous_text[-1] in SENTENCE_ENDINGS or previous_text.endswith("…")
        )
        if looks_like_term(text) and previous_ended_sentence and (term is None or definition_lines):
            if term is not None:
                entries.append(GlossaryEntry(term, join_lines(definition_lines)))
            term, definition_lines = text, []
        elif term is not None:
            definition_lines.append(text)
        previous_text = text
    if term is not None:
        entries.append(GlossaryEntry(term, join_lines(definition_lines)))
    return entries


def looks_like_term(text: str) -> bool:
    """Return whether a stripped line reads as a term: short, unpunctuated at the end, and in title case."""
    if not text or len(text) > 40:
        return False
    if NUMBERED_DEFINITION_PATTERN.match(text):
        return False
    if text[-1] in ".,;:!?\"”’)":
        return False
    if not (text[0].isupper() or text[0].isdigit() or text[0] in TERM_OPENING_CHARACTERS):
        return False
    words = text.split()
    title_case_words = [
        word
        for word in words
        if word[0].isupper()
        or word[0].isdigit()
        or word.lower() in TERM_LOWERCASE_WORDS
        or word[0] in TERM_OPENING_CHARACTERS
    ]
    return len(title_case_words) == len(words)


def parse_indent(lines: list[str]) -> list[GlossaryEntry]:
    """Return the entries of a 2010 or 2011 glossary, where each definition is indented under its term.

    A line is a term when the next non-blank line is indented further, unless it reads as running text:
    a numbered line, a line over 45 characters, or one over 12 characters that ends a sentence. A line
    followed by a numbered line other than "1." is not a term either. The lines must keep their
    indentation (split_columns_keep_indent). Lines before the first term are dropped.
    """
    lines = [line.rstrip() for line in lines]
    entries = []
    term, definition_lines = None, []
    for position, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
        next_line = find_next_text_line(lines, position)
        next_text = next_line.strip()
        is_term = (
            indent_width(next_line) > indent_width(line)
            and not NUMBERED_DEFINITION_PATTERN.match(text)
            and not (NUMBERED_DEFINITION_PATTERN.match(next_text) and not next_text.startswith("1."))
            and (text[-1] not in ".!?”\"" or len(text) <= 12)
            and len(text) <= 45
        )
        if is_term:
            if term is not None:
                entries.append(GlossaryEntry(term, join_lines(definition_lines)))
            term, definition_lines = text, []
        elif term is not None:
            definition_lines.append(text)
    if term is not None:
        entries.append(GlossaryEntry(term, join_lines(definition_lines)))
    return entries


def parse_para(text: str, inline: bool = False, max_term_length: int = 45) -> list[GlossaryEntry]:
    """Return the entries of a glossary set as paragraphs separated by blank lines.

    With inline=False, a paragraph's first line is the term and the rest its definition. A first line
    longer than max_term_length, ending in ".", "," or ";", starting in lowercase, or alone in its
    paragraph reads as running text, and the paragraph is added to the previous definition.

    With inline=True, the term is the paragraph's first word and the rest is its definition; terms of
    more than one word are fixed later, by hand (finalize.py). A paragraph starting in lowercase
    continues the previous entry.
    """
    entries = []
    for paragraph in PARAGRAPH_BREAK_PATTERN.split(text):
        if not paragraph.strip():
            continue
        paragraph_lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if inline:
            add_inline_paragraph(entries, paragraph_lines)
        else:
            add_term_first_paragraph(entries, paragraph_lines, max_term_length)
    return entries


def add_inline_paragraph(entries: list[GlossaryEntry], paragraph_lines: list[str]) -> None:
    """Add a paragraph whose first word is the term to entries, or to the last entry if it starts in lowercase.

    This once also treated a paragraph as a continuation when the previous definition did not end a
    sentence, but only together with the lowercase test, so that check never changed the result and is
    left out.
    """
    first_line = paragraph_lines[0]
    paragraph_text = join_lines(paragraph_lines)
    inline_entry = INLINE_ENTRY_PATTERN.match(paragraph_text)
    if inline_entry:
        term, definition = inline_entry["term"], inline_entry["definition"]
    else:
        term, definition = paragraph_text, ""
    if first_line[0].islower() and entries:
        previous_entry = entries[-1]
        entries[-1] = GlossaryEntry(previous_entry.term, join_lines([previous_entry.definition, paragraph_text]))
    else:
        entries.append(GlossaryEntry(term, definition))


def add_term_first_paragraph(entries: list[GlossaryEntry], paragraph_lines: list[str], max_term_length: int) -> None:
    """Add a paragraph whose first line is the term to entries, or to the last entry if it reads as running text.

    A running-text paragraph before any entry becomes an entry anyway, with its first line as the term.
    """
    first_line = paragraph_lines[0]
    is_term = (
        len(first_line) <= max_term_length
        and first_line[-1] not in ".,;"
        and not first_line[0].islower()
        and len(paragraph_lines) > 1
    )
    if entries and not is_term:
        previous_entry = entries[-1]
        entries[-1] = GlossaryEntry(previous_entry.term, join_lines([previous_entry.definition, *paragraph_lines]))
    else:
        entries.append(GlossaryEntry(first_line, join_lines(paragraph_lines[1:])))


def parse_colon(text: str) -> list[GlossaryEntry]:
    """Return the entries of an Owlmanac glossary: "Term: definition" paragraphs, separated by blank lines.

    A paragraph may wrap over several lines. A paragraph that does not start with a term of 1 to 60
    characters and a colon is added to the previous definition, or dropped if no entry has started.
    """
    entries = []
    for paragraph in PARAGRAPH_BREAK_PATTERN.split(text):
        paragraph_text = join_lines(paragraph.splitlines())
        colon_entry = COLON_ENTRY_PATTERN.match(paragraph_text)
        if colon_entry:
            entries.append(GlossaryEntry(colon_entry["term"].strip(), colon_entry["definition"].strip()))
        elif entries:
            previous_entry = entries[-1]
            entries[-1] = GlossaryEntry(previous_entry.term, (previous_entry.definition + " " + paragraph_text).strip())
    return entries


def write_tsv(tsv_file: str, rows: list[tuple[str, str, str, str]]) -> None:
    """Write the rows to a UTF-8 TSV with a header line, replacing any file already there.

    Each row is (term, definition, source_key, locator), as in sources/glossaries/. Tabs inside a term or
    definition become spaces, and both are stripped, so every row keeps four columns.
    """
    with open(tsv_file, "w", encoding="utf-8") as tsv:
        tsv.write("term\tdefinition\tsource_key\tlocator\n")
        for term, definition, source_key, locator in rows:
            term = term.replace("\t", " ").strip()
            definition = definition.replace("\t", " ").strip()
            tsv.write(f"{term}\t{definition}\t{source_key}\t{locator}\n")


def show(entries: list[GlossaryEntry]) -> None:
    """Print each entry as "[term] definition", for checking a parse by eye from a driver script."""
    for term, definition in entries:
        print(f"[{term}] {definition}")


def trim_and_find_bounds(
    page: str,
    bounds: list[int] | None,
    ncols: int,
    skip_top: int,
    skip_bottom: int,
) -> tuple[list[str], list[int]]:
    """Return the page's lines without the skipped top and bottom lines, and the bounds, found if not given."""
    lines = page.splitlines()
    if skip_top:
        lines = lines[skip_top:]
    if skip_bottom:
        lines = lines[:-skip_bottom]
    if bounds is None:
        bounds = detect_bounds(lines, ncols)
    return lines, bounds


def detect_bounds(lines: list[str], ncols: int = 3, min_separation: int = 15) -> list[int]:
    """Return where the second and later columns start: the offsets at which most words start.

    Every line of a column starts at the same offset, so counting word starts at each offset gives a
    peak per column. A word start after two or more spaces, or at the start of the line, counts double,
    since it is more likely a column start than the next word of a sentence. Each offset's count is
    counted together with the next offset's, so a column a character out of line still makes one peak. The ncols
    highest peaks at least min_separation apart are the columns, and the ones more than 5 characters in
    are returned, at most ncols - 1 of them, left to right. Ties go to the offset further right.
    """
    text_lines = [line.rstrip("\n") for line in lines if line.strip()]
    if not text_lines:
        return []
    width = max(len(line) for line in text_lines)
    word_starts = [0] * (width + 2)
    for line in text_lines:
        for offset, character in enumerate(line):
            if character != " " and (offset == 0 or line[offset - 1] == " "):
                word_starts[offset] += 2 if (offset >= 2 and line[offset - 2] == " ") or offset == 0 else 1
    peaks = []
    for offset, count in enumerate(word_starts):
        if count == 0:
            continue
        next_count = word_starts[offset + 1] if offset + 1 < len(word_starts) else 0
        peaks.append((count + next_count, offset))
    peaks.sort(reverse=True)
    chosen_offsets = []
    for _, offset in peaks:
        if all(abs(offset - chosen) >= min_separation for chosen in chosen_offsets):
            chosen_offsets.append(offset)
        if len(chosen_offsets) == ncols:
            break
    return [offset for offset in sorted(chosen_offsets) if offset > 5][: ncols - 1]


def find_next_text_line(lines: list[str], position: int) -> str:
    """Return the first non-blank line after lines[position], or "" if there is none."""
    for next_line in lines[position + 1 :]:
        if next_line.strip():
            return next_line
    return ""


def indent_width(line: str) -> int:
    """Return how many leading spaces (or other whitespace characters) the line has."""
    return len(line) - len(line.lstrip())


def join_lines(lines: list[str]) -> str:
    """Return the lines joined into one, with blank lines dropped, runs of space collapsed and hyphens mended."""
    joined = ""
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if not joined:
            joined = text
        elif joined.endswith("-"):
            joined = dehyphen(joined, text)
        else:
            joined += " " + text
    return re.sub(r"\s+", " ", joined).strip()


def dehyphen(text: str, next_text: str) -> str:
    """Join text that ends in "-" to the next line's text, dropping the hyphen if it broke a word.

    The hyphen is dropped when the next line starts in lowercase and its first word has no hyphen of its
    own, so "Wiess-" and "men" make "Wiessmen". A compound broken at its own hyphen loses it the same
    way: "self-" and "made" make "selfmade".
    """
    first_word = next_text.split(" ")[0] if next_text else ""
    if text.endswith("-") and next_text and next_text[0].islower() and "-" not in first_word:
        return text[:-1] + next_text
    return text + " " + next_text
