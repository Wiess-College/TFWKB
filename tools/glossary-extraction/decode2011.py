"""Decode the glyph-order cipher of two subsetted fonts in the 2011 O-Week book (pp.92-96).

The glossary pages of the 2011 book embed two fonts whose glyph codes are not ASCII, so their text layer
reads as punctuation: "3#+-"6+"4$0&" is "When we said". Without decoding, those pages give no glossary
at all. The body text font and the bold heading font each have their own map below, derived by aligning
the garbled pages with the identical passages in the 2010 book.

extract_layout.py runs this file with exec() when given "--decode decode2011.py", then calls
decode_column on the lines of each column. decode_column is the only name it looks up. This file reads
and writes no files. A character missing from a map comes out as "�" followed by the character itself,
so a gap in the map shows up in the review output.

BODY_TEXT_CIPHER swaps two entries: "`" is really "!" and "a" is really ")", as the glyph outlines show
(tools/fix_pdf_fonts.py). finalize.py's correction for "Smoothie King (yummy!)" covers the one place it shows.
"""

import re

# Body text font: garbled character -> what it stands for. Some glyphs are ligatures ("ff", "fi").
BODY_TEXT_CIPHER = {
    "!": "A", '"': " ", "#": "h", "$": "a", "%": "r", "&": "d", "'": "-", "(": "t", ")": "o", "*": "g",
    "+": "e", ",": "u", "-": "n", ".": "ff", "/": "c", "0": "i", "1": "m", "2": "f", "3": "W", "4": "s",
    "5": "p", "6": "w", "7": "b", "8": "l", "9": ".", ":": ",", ";": "y", "<": "fi", "=": "x", ">": "—",
    "?": "v", "@": "T", "A": "F", "B": "fl", "C": "K", "D": "k", "E": "M", "F": "L", "G": "E", "H": "R",
    "I": "S", "J": "O", "K": "z", "L": "1", "M": "2", "N": "4", "O": "ffi", "P": "I", "Q": "N", "R": "B",
    "S": "H", "T": "V", "U": "’", "V": "C", "W": "j", "X": "U", "Y": "q", "Z": "D", "[": "P", "\\": "Y",
    "]": "3", "^": "’", "_": "(", "`": ")", "a": "!",
}

# Bold heading font: garbled character -> what it stands for.
HEADING_CIPHER = {
    "!": "C", '"': "o", "#": "ff", "$": "e", "%": "h", "&": "u", "'": "s", "(": " ", ")": "N", "*": "i",
    "+": "g", ",": "t", "-": "a", ".": "n", "/": "c", "0": "y", "1": "f", "2": "D", "3": "d", "4": "(",
    "5": "O", "6": ")", "7": "L", "8": "P", "9": "m", ":": "p", ";": "k", "<": "r", "=": "l", "?": "T",
    "@": "v", "A": "W", "B": "M", "C": "H", "F": "-", "J": "b", "K": "z",
    ">": "S", "D": "A", "E": "R", "G": "K", "H": "U", "I": "Y", "L": "q", "M": "’", "N": "Q",
}

# Punctuation that is rare in ordinary text but common in garbled body text. A run with two of these, or
# with a '"' (the body font's space), is garbled.
RARE_IN_BODY_TEXT = set('!"#$%&\'*+/;<=>?@[\\]^_`')

# Punctuation that marks a heading line as garbled. Unlike the body list it has "(" and ")", which the
# heading font uses for a space and an "N".
RARE_IN_HEADINGS = set('!"#$%&\'()*+;<=>?@[\\]^_`')

# A candidate garbled run in body text: 5 or more characters between "!" and "`" in ASCII, the range the
# body font's codes fall in. Lowercase letters are outside it, so ordinary words end a run.
BODY_RUN_PATTERN = re.compile(r"[!-`]{5,}")

# A whole heading line (already stripped) made of 3 or more characters from the same range.
HEADING_LINE_PATTERN = re.compile(r"^[!-`]{3,}$")


def decode_column(column_lines: list[str]) -> list[str]:
    """Return the column's lines decoded, treating a line as a heading when the next text line is more indented.

    The two fonts need different maps, and the text layer does not say which font a line is in. On these
    pages each term sits over its definition, which is indented further, so indentation tells them apart.
    The lines must therefore keep their indentation, as extract_layout.py's indent mode does. Blank lines
    are kept as they are.
    """
    decoded_lines = []
    for position, line in enumerate(column_lines):
        if not line.strip():
            decoded_lines.append(line)
            continue
        next_position = position + 1
        while next_position < len(column_lines) and not column_lines[next_position].strip():
            next_position += 1
        next_indent = indent_width(column_lines[next_position]) if next_position < len(column_lines) else 0
        decoded_lines.append(decode_line(line, next_indent > indent_width(line)))
    return decoded_lines


def decode_line(line: str, is_heading: bool) -> str:
    """Return the line with its garbled text decoded, using the heading map if it is a garbled heading.

    A heading is decoded only when the whole line is garbled; it keeps its indentation and loses trailing
    space. In body text, each run of garbled characters is decoded on its own and ordinary text around it
    is left alone, since a line can mix the two fonts.
    """
    stripped_line = line.strip()
    if (
        is_heading
        and HEADING_LINE_PATTERN.match(stripped_line)
        and any(character in RARE_IN_HEADINGS for character in stripped_line)
    ):
        indentation = line[: indent_width(line)]
        return indentation + decode_with_cipher(stripped_line, HEADING_CIPHER).rstrip()

    decoded_parts = []
    copied_up_to = 0
    for run_match in BODY_RUN_PATTERN.finditer(line):
        run_start, run_end = run_match.start(), run_match.end()
        run = line[run_start:run_end]
        # A plain capitalised word glued on the end ('…(#+"First') is not part of the run: the capital is
        # in the run's range but the lowercase letters after it are not, so give the capital back.
        while run and run[-1].isupper() and run_end < len(line) and line[run_end].islower():
            run = run[:-1]
            run_end -= 1
        decoded_parts.append(line[copied_up_to:run_start])
        decoded_parts.append(decode_with_cipher(run, BODY_TEXT_CIPHER) if looks_garbled(run) else run)
        copied_up_to = run_end
    decoded_parts.append(line[copied_up_to:])
    return "".join(decoded_parts)


def looks_garbled(run: str) -> bool:
    """Return whether a body-text run is garbled rather than ordinary capitals, digits and punctuation."""
    return sum(1 for character in run if character in RARE_IN_BODY_TEXT) >= 2 or '"' in run


def decode_with_cipher(garbled_text: str, cipher: dict[str, str]) -> str:
    """Return the text decoded with the cipher, writing an unknown character as "�" followed by itself."""
    return "".join(cipher.get(character, "�" + character) for character in garbled_text)


def indent_width(line: str) -> int:
    """Return how many leading spaces (or other whitespace characters) the line has."""
    return len(line) - len(line.lstrip())
