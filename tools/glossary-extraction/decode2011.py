<<<<<<< Updated upstream
"""Glyph-order cipher used by two subsetted fonts in the 2011 O-Week book (pp.92-96).
Maps derived by aligning with the 2010 book's identical passages."""
=======
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

>>>>>>> Stashed changes
import re

A = {  # body text font
    "!": "A", '"': " ", "#": "h", "$": "a", "%": "r", "&": "d", "'": "-", "(": "t", ")": "o", "*": "g",
    "+": "e", ",": "u", "-": "n", ".": "ff", "/": "c", "0": "i", "1": "m", "2": "f", "3": "W", "4": "s",
    "5": "p", "6": "w", "7": "b", "8": "l", "9": ".", ":": ",", ";": "y", "<": "fi", "=": "x", ">": "—",
    "?": "v", "@": "T", "A": "F", "B": "fl", "C": "K", "D": "k", "E": "M", "F": "L", "G": "E", "H": "R",
    "I": "S", "J": "O", "K": "z", "L": "1", "M": "2", "N": "4", "O": "ffi", "P": "I", "Q": "N", "R": "B",
    "S": "H", "T": "V", "U": "’", "V": "C", "W": "j", "X": "U", "Y": "q", "Z": "D", "[": "P", "\\": "Y",
    "]": "3", "^": "’", "_": "(", "`": ")", "a": "!",
}
B = {  # bold heading font
    "!": "C", '"': "o", "#": "ff", "$": "e", "%": "h", "&": "u", "'": "s", "(": " ", ")": "N", "*": "i",
    "+": "g", ",": "t", "-": "a", ".": "n", "/": "c", "0": "y", "1": "f", "2": "D", "3": "d", "4": "(",
    "5": "O", "6": ")", "7": "L", "8": "P", "9": "m", ":": "p", ";": "k", "<": "r", "=": "l", "?": "T",
    "@": "v", "A": "W", "B": "M", "C": "H", "F": "-", "J": "b", "K": "z",
    ">": "S", "D": "A", "E": "R", "G": "K", "H": "U", "I": "Y", "L": "q", "M": "’", "N": "Q",
}
RARE = set('!"#$%&\'*+/;<=>?@[\\]^_`')
RUN = re.compile(r"[!-`]{5,}")
HRUN = re.compile(r"^[!-`]{3,}$")
HRARE = set('!"#$%&\'()*+;<=>?@[\\]^_`')


def is_garbled(s: str) -> bool:
    return sum(1 for c in s if c in RARE) >= 2 or '"' in s


def dec(s: str, m: dict) -> str:
    return "".join(m.get(c, "�" + c) for c in s)


def decode_line(line: str, heading: bool) -> str:
    st = line.strip()
    if heading and HRUN.match(st) and any(c in HRARE for c in st):
        ind = line[: len(line) - len(line.lstrip())]
        return ind + dec(st, B).rstrip()

    out = []
    pos = 0
    for mt in RUN.finditer(line):
        s, e = mt.start(), mt.end()
        run = line[s:e]
        # a plain capitalised word glued on the end ("…(#+"First") is not part of the run
        while run and run[-1].isupper() and e < len(line) and line[e].islower():
            run = run[:-1]
            e -= 1
        out.append(line[pos:s])
        out.append(dec(run, A) if is_garbled(run) else run)
        pos = e
    out.append(line[pos:])
    return "".join(out)


def decode_column(lines):
    """lines keep indentation; a flush line followed by an indented line is a heading."""
    out = []
    n = len(lines)
    for i, raw in enumerate(lines):
        if not raw.strip():
            out.append(raw)
            continue
        indent = len(raw) - len(raw.lstrip())
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        nxt_indent = (len(lines[j]) - len(lines[j].lstrip())) if j < n else 0
        heading = nxt_indent > indent
        out.append(decode_line(raw, heading))
    return out
