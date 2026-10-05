#!/usr/bin/env python3
"""Decode the font-shifted runs in O-Week book text extracts.

Some PDFs in the corpus embed a font whose glyph codes are offset by 29 from ASCII, so
"place and" comes out as "SODFHDQG" (spaces are dropped; "fi"/"fl" ligatures become À/Á).
This filter detects such runs and shifts them back. It never touches normal text.

    python3 tools/fix_pdf_text.py corpus/teamwiess.com/oweek-books/text/2014-oweek-book.txt > /tmp/2014.txt
    python3 tools/fix_pdf_text.py -                                   # stdin → stdout
"""
import re
import sys

LIG = {"À": "fi", "Á": "fl", "Â": "ffi", "¿": "ff"}
# A garbled run: 8+ consecutive chars drawn from the shifted alphabet (ASCII 0x21–0x5D, i.e.
# letters shift to uppercase/punctuation) with few lowercase letters, often containing
# shifted-space-free uppercase runs like WKH ("the"), DQG ("and"), RI ("of").
RUN = re.compile(r"(?:[!-\]¿-Â]){8,}")
MARKERS = ("WKH", "DQG", "RI", "WR", "LQ", "LV", "IRU", "ZLWK", ":LHVV", "À", "Á")


def shift(run: str) -> str:
    out = []
    for ch in run:
        if ch in LIG:
            out.append(LIG[ch])
        else:
            o = ord(ch)
            if 0x21 <= o <= 0x5D:
                out.append(chr(o + 29))
            else:
                out.append(ch)
    return "".join(out)


def fix_line(line: str) -> str:
    def repl(m):
        run = m.group(0)
        # must look like shifted English, not an ordinary ALL-CAPS heading
        if not any(k in run for k in MARKERS):
            return run
        if sum(c.islower() for c in run) > len(run) * 0.2:
            return run
        return "⟨" + shift(run) + "⟩"  # brackets mark decoded, space-less text

    return RUN.sub(repl, line)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    fh = sys.stdin if src == "-" else open(src, encoding="utf-8", errors="replace")
    for line in fh:
        sys.stdout.write(fix_line(line))


if __name__ == "__main__":
    main()
