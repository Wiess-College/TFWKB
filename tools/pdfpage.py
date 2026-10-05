#!/usr/bin/env python3
"""Find which PDF page a phrase is on, in a text extract that uses form feeds between pages.

    python3 tools/pdfpage.py corpus/teamwiess.com/oweek-books/text/2006-oweek-book.txt "War pig"
Prints: page number (1-based), then the matching line. Case-insensitive. Also searches the
font-shift-decoded text (see fix_pdf_text.py) so garbled pages still match.
"""
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fix_pdf_text import fix_line  # noqa: E402


def main():
    path, needle = sys.argv[1], sys.argv[2].lower()
    text = open(path, encoding="utf-8", errors="replace").read()
    pages = text.split("\f")
    if len(pages) == 1:
        print("(no form feeds in this file: page numbers unavailable; showing line numbers)", file=sys.stderr)
        for i, line in enumerate(text.splitlines(), 1):
            if needle in line.lower() or needle in fix_line(line).lower():
                print(f"line {i}: {line.strip()[:160]}")
        return
    for n, page in enumerate(pages, 1):
        for line in page.splitlines():
            if needle in line.lower() or needle in fix_line(line).lower():
                print(f"p.{n}: {fix_line(line).strip()[:160]}")


if __name__ == "__main__":
    main()
