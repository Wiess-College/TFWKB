#!/usr/bin/env python3
"""Find which PDF page a phrase is on, in a text extract that has form feeds between pages.

Pages cite the O-Week books by page ("[@oweek-2006 p.84]"), but a book's text extract is one long file,
and counting pages in it by hand is slow and easy to get wrong. When the extract has a form feed between
pages, this script counts them for you. It also searches the decoded form of each line (see
tools/fix_pdf_text.py), so a phrase on a page whose font is shifted still matches.

It writes no files. Give it the text file and the phrase:

    python3 tools/pdfpage.py corpus/teamwiess.com/oweek-books/text/2006-oweek-book.txt "War pig"

It prints one line for each matching line, the page number (counting from 1, the first page of the PDF)
and then the line, decoded, trimmed and cut to 160 characters:

    p.84: War pig ...

The match ignores case. If the file has no form feeds, it says so on standard error and gives line
numbers instead ("line 1203: ..."), and those lines are printed as they are in the file, not decoded.
No match prints nothing. A missing argument or a file that cannot be opened stops it with a traceback.
The file is read as UTF-8, with bytes that are not UTF-8 replaced by "�".
"""

import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fix_pdf_text import fix_line


def main(arguments: list[str]) -> None:
    """Print each line of the text file that contains the phrase, with its page or line number."""
    text_file, phrase, *_ = arguments
    phrase = phrase.lower()
    with open(text_file, encoding="utf-8", errors="replace") as text:
        extract_text = text.read()

    pages = extract_text.split("\f")
    if len(pages) == 1:
        print("(no form feeds in this file: page numbers unavailable; showing line numbers)", file=sys.stderr)
        for line_number, line in enumerate(extract_text.splitlines(), 1):
            if line_contains(line, phrase):
                print(f"line {line_number}: {line.strip()[:160]}")
        return
    for page_number, page in enumerate(pages, 1):
        for line in page.splitlines():
            if line_contains(line, phrase):
                print(f"p.{page_number}: {fix_line(line).strip()[:160]}")


def line_contains(line: str, phrase: str) -> bool:
    """Return whether the line, as it is or with its shifted runs decoded, contains the lowercase phrase."""
    return phrase in line.lower() or phrase in fix_line(line).lower()


if __name__ == "__main__":
    main(sys.argv[1:])
