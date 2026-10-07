#!/usr/bin/env python3
"""Decode the font-shifted runs in O-Week book text extracts.

Some PDFs in the corpus embed a font whose glyph codes are offset by 29 from ASCII, so "place and"
comes out as "SODFHDQG": spaces are dropped, and the "fi" and "fl" ligatures become "À" and "Á". A
search for a word on such a page finds nothing until the run is shifted back. This filter finds those
runs and decodes them, wrapping each decoded run in "⟨" and "⟩" to mark text whose spaces are lost.
tools/pdfpage.py and tools/glossary-extraction/ import fix_line from here.

It writes no files. It reads one text file, or standard input, and prints the text with the runs
decoded:

    python3 tools/fix_pdf_text.py corpus/teamwiess.com/oweek-books/text/2014-oweek-book.txt > /tmp/2014.txt
    python3 tools/fix_pdf_text.py -        (standard input to standard output; also the default)

The file is read as UTF-8, with bytes that are not UTF-8 replaced by "�"; standard input is read in the
locale's encoding. Only the first argument is read. A file that cannot be opened stops it with a
traceback before anything is printed.

A run is decoded only when it is 8 or more characters from the shifted alphabet with no spaces, and
contains a common shifted word such as "WKH" ("the"). Four of those words are only two letters long
("RI" for "of", "WR" for "to", "LQ" for "in", "LV" for "is"), so an ordinary capitalised word of 8 or more letters that
happens to contain one, such as "AMERICAN", is decoded too, into nonsense.
"""

import re
import sys
from typing import TextIO

# The shifted font draws these ligatures from glyph codes outside the shifted ASCII range.
LIGATURE_BY_SHIFTED_GLYPH = {"À": "fi", "Á": "fl", "Â": "ffi", "¿": "ff"}

# A candidate run: 8 or more characters, each either in ASCII "!" to "]" (0x21-0x5D, where shifted
# lowercase letters land as capitals and punctuation) or one of the ligature glyphs "¿", "À", "Á", "Â"
# (U+00BF to U+00C2). Spaces are not in the set, so a run never crosses a real space.
SHIFTED_RUN_PATTERN = re.compile(r"(?:[!-\]¿-Â]){8,}")

# Common English words as the shifted font writes them: "the", "and", "of", "to", "in", "is", "for",
# "with", "Wiess", and the "fi" and "fl" ligatures. A run must contain one to count as shifted English
# rather than an ordinary ALL-CAPS heading.
SHIFTED_ENGLISH_MARKERS = ("WKH", "DQG", "RI", "WR", "LQ", "LV", "IRU", "ZLWK", ":LHVV", "À", "Á")


def main(arguments: list[str]) -> None:
    """Print the file named first in arguments, or standard input, with its shifted runs decoded."""
    text_file = arguments[0] if arguments else "-"
    if text_file == "-":
        print_fixed_lines(sys.stdin)
    else:
        with open(text_file, encoding="utf-8", errors="replace") as text:
            print_fixed_lines(text)


def print_fixed_lines(lines: TextIO) -> None:
    """Write each line to standard output with its shifted runs decoded; lines keep their own line endings."""
    for line in lines:
        sys.stdout.write(fix_line(line))


def fix_line(line: str) -> str:
    """Return the line with each run of shifted English decoded and wrapped in "⟨" and "⟩"."""
    return SHIFTED_RUN_PATTERN.sub(decode_run_if_shifted_english, line)


def decode_run_if_shifted_english(run_match: re.Match[str]) -> str:
    """Return the matched run decoded and bracketed if it reads as shifted English, or unchanged if not."""
    run = run_match.group()
    if not any(marker in run for marker in SHIFTED_ENGLISH_MARKERS):
        return run
    # Meant to leave runs of mostly lowercase text alone. SHIFTED_RUN_PATTERN admits no lowercase
    # letters, so this never returns early; it is kept so the rules read as they always have.
    if sum(character.islower() for character in run) > len(run) * 0.2:
        return run
    return "⟨" + decode_shifted_run(run) + "⟩"


def decode_shifted_run(run: str) -> str:
    """Return the run with every shifted character moved back up by 29 and each ligature glyph spelled out."""
    decoded_characters = []
    for character in run:
        if character in LIGATURE_BY_SHIFTED_GLYPH:
            decoded_characters.append(LIGATURE_BY_SHIFTED_GLYPH[character])
        elif 0x21 <= ord(character) <= 0x5D:
            decoded_characters.append(chr(ord(character) + 29))
        else:
            decoded_characters.append(character)
    return "".join(decoded_characters)


if __name__ == "__main__":
    main(sys.argv[1:])
