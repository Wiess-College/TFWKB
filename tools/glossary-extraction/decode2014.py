"""Decode the +29 font shift in the 2014 O-Week book's glossary (pp.102-106).

The 2014 book uses the same shifted font that tools/fix_pdf_text.py handles, with glyph codes 29 below
ASCII. In this PDF, though, the shifted font keeps its spaces and punctuation as control characters
(0x03 is a space, 0x11 a ".", 0x0F a ","), so a run decodes completely, spaces included. Runs may also
contain real spaces between shifted words. This file has its own rules for finding runs to match.

extract_layout.py runs this file with exec() when given "--decode decode2014.py", then calls
decode_column on the lines of each column. decode_column is the only name it looks up. This file reads
and writes no files. Each decoded run is wrapped in "⟨" and "⟩", as fix_pdf_text.py does.
"""

import re

# The shifted font draws these ligatures from glyph codes outside the shifted ASCII range.
LIGATURE_BY_SHIFTED_GLYPH = {"À": "fi", "Á": "fl", "Â": "ffi", "¿": "ff"}

# One shifted character: a control character (0x01-0x1F), ASCII "!" to "]" (0x21-0x5D), or a ligature glyph.
SHIFTED_CHARACTER = r"[\x01-\x1f!-\]ÀÁÂ¿]"

# A run of shifted characters. It starts and ends with one, and may contain single real spaces as long as
# a shifted character follows each space ("(?=...)" looks ahead without consuming it).
SHIFTED_RUN_PATTERN = re.compile(
    SHIFTED_CHARACTER
    + r"(?:(?:" + SHIFTED_CHARACTER + r"| (?=" + SHIFTED_CHARACTER + r"))*"
    + SHIFTED_CHARACTER + r")?"
)

# Shifted characters that decode to lowercase letters: 0x44-0x5D become "a" to "z", plus the ligatures.
SHIFTED_LOWERCASE = {chr(code) for code in range(0x44, 0x5E)} | set("ÀÁÂ¿")


def decode_column(column_lines: list[str]) -> list[str]:
    """Return the column's lines with every shifted run decoded."""
    return [decode_line(line) for line in column_lines]


def decode_line(line: str) -> str:
    """Return the line with each run that looks shifted decoded and wrapped in "⟨" and "⟩"."""
    return SHIFTED_RUN_PATTERN.sub(decode_run_if_shifted, line)


def decode_run_if_shifted(run_match: re.Match[str]) -> str:
    """Return the matched run decoded and bracketed if it looks shifted, or unchanged if not."""
    run = run_match.group()
    line = run_match.string
    next_character = line[run_match.end()] if run_match.end() < len(line) else ""
    return "⟨" + decode_shifted_run(run) + "⟩" if looks_shifted(run, next_character) else run


def looks_shifted(run: str, next_character: str = "") -> bool:
    """Return whether a run is shifted text rather than ordinary capitals, digits and punctuation.

    Ordinary text has no control characters or ligature glyphs, so three or more characters with one of
    them is enough. Without one, the run must be at least six characters, at least half of them shifted
    lowercase letters, and not a parenthesised aside; and a run followed directly by a lowercase letter,
    such as the "W" of "Wiess", is the start of an ordinary capitalised word. A run of only digits,
    spaces and ",.-" is a number or a date either way.
    """
    run_characters = [character for character in run if character != " "]
    has_control_or_ligature = any(ord(character) < 0x20 for character in run_characters) or any(
        character in LIGATURE_BY_SHIFTED_GLYPH for character in run_characters
    )
    if not has_control_or_ligature and next_character.islower():
        return False
    lowercase_fraction = sum(1 for character in run_characters if character in SHIFTED_LOWERCASE) / max(
        1, len(run_characters)
    )
    if re.fullmatch(r"[\d ,.\-]+", run):
        return False
    if has_control_or_ligature and len(run_characters) >= 3:
        return True
    return len(run_characters) >= 6 and lowercase_fraction >= 0.5 and not (run.startswith("(") and run.endswith(")"))


def decode_shifted_run(run: str) -> str:
    """Return the run with every shifted character moved back up by 29, keeping real spaces.

    A "-" at the very end is a real end-of-line hyphen, not a shifted "J", so it is kept as it is.
    """
    trailing_hyphen = ""
    if run.endswith("-"):
        run, trailing_hyphen = run[:-1], "-"
    decoded_characters = []
    for character in run:
        if character in LIGATURE_BY_SHIFTED_GLYPH:
            decoded_characters.append(LIGATURE_BY_SHIFTED_GLYPH[character])
        elif character == " ":
            decoded_characters.append(" ")
        else:
            code = ord(character)
            decoded_characters.append(chr(code + 29) if 0x01 <= code <= 0x5D else character)
    return "".join(decoded_characters) + trailing_hyphen
