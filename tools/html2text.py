#!/usr/bin/env python3
"""Print the readable text of archived HTML pages, without their markup (standard library only).

The corpus keeps pages from the Wayback Machine as raw HTML, with markup, scripts, style sheets and
entities such as &nbsp; around the words. That is hard to read, quote or search for a phrase. This
script prints just the words, with headings marked the Markdown way ("## Traditions") and each closed
paragraph, list item and table cell on its own line. It also reads pages saved as Windows-1252 or
Latin-1 rather than UTF-8.

It reads the files named on the command line, or standard input if there are none, and writes no
files. It prints the text of each file in turn, each followed by one newline and nothing else, so two
files' texts are not marked off from each other. A page archived from a site is at corpus/<site>/
plus the path in the "local" column of sources/manifests/<site>/index.tsv, with any backslash removed:

    python3 tools/html2text.py corpus/teamwiess.com/mirror/teamwiess.com/20010124011100__index.html
    python3 tools/html2text.py page1.html page2.html > both.txt
    curl -s <url> | python3 tools/html2text.py

With no file names, or with "-" as one, it reads HTML from standard input; run with no file names, it
waits for that input rather than printing usage.

The conversion is crude. Things a reader might expect but won't get:

    paragraphs and list items   only a closing tag (</p>, </li>) starts a new line, so older pages that
                                write <p> or <li> alone run their paragraphs or items together on one line
    <link ...> in the head      read as a list item: each leaves a stray "- " near the top of the text
    <br clear=all>              a <br> with attributes is dropped without a line break
    </p > and similar           a closing tag with a space before ">" starts no new line
    <pre> blocks                spaces are collapsed like everywhere else
    links and images            link text is kept without its address; images and their alt text vanish
    a bare "<" in the text      taken as the start of a tag: everything up to the next ">" is dropped,
                                words included

Since it writes nothing, a failed run leaves nothing to clean up. Every file decodes as something,
because Latin-1 accepts any bytes, so there is no "not recognised" output. A file that cannot be
opened stops it with a Python traceback (FileNotFoundError and the like) and exit status 1, after
printing the text of the files before it. So does printing to output whose encoding has no character
for one in the text (for example PYTHONIOENCODING=ascii, or a Latin-1 locale meeting a curly quote),
with UnicodeEncodeError, at the first such file. The plain C locale is fine, because Python treats it
as UTF-8.
"""

import html
import re
import sys


def main(arguments: list[str]) -> None:
    """Print the text of each HTML file named in the arguments, or of standard input if there are none."""
    for html_file in arguments or ["-"]:
        page_bytes = read_page_bytes(html_file)
        page_html = decode_page_bytes(page_bytes)
        print(convert_html_to_text(page_html))


def read_page_bytes(html_file: str) -> bytes:
    """Return the bytes of a file named on the command line (relative to the current folder), or of stdin for "-"."""
    if html_file == "-":
        return sys.stdin.buffer.read()
    with open(html_file, "rb") as page:
        return page.read()


def decode_page_bytes(page_bytes: bytes) -> str:
    """Return the page as text, read as UTF-8 if it is valid UTF-8, else as Windows-1252, else as Latin-1.

    Any encoding the page declares in a <meta> tag is ignored. The two fallbacks differ only in bytes
    0x80-0x9F, which Windows-1252 reads as curly quotes, dashes and the like, and Latin-1 as invisible
    control characters, so Windows-1252 is tried first. Windows-1252 leaves five of those bytes (0x81,
    0x8D, 0x8F, 0x90, 0x9D) undefined, so a page containing any of them is read entirely as Latin-1.
    The choice is made for the whole file: a UTF-8 page with one stray Windows byte is read entirely as
    Windows-1252, and its "é" comes out as "Ã©".
    """
    for encoding in ("utf-8", "cp1252"):
        try:
            return page_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    # Latin-1 maps every byte to a character, so this never fails.
    return page_bytes.decode("latin-1")


def convert_html_to_text(page_html: str) -> str:
    """Return the words of an HTML page, each closed block on its own line and headings marked with "#".

    Each step works on the output of the one before, so the order matters: invisible content goes
    first, line breaks are put in before the tags that cause them are removed, and entities are
    turned into characters only once no tags are left, so an escaped "&lt;b&gt;" survives as "<b>".
    """
    # Script, style and noscript elements with everything inside them. (?P=tag_name) makes the closing tag
    # match the opening one; (?is) ignores case and lets "." cross newlines.
    page_text = re.sub(r"(?is)<(?P<tag_name>script|style|noscript).*?</(?P=tag_name)>", " ", page_html)
    page_text = re.sub(r"(?is)<!--.*?-->", " ", page_text)
    # <br>, <br/> or <br />, with any spaces before the slash. A <br> with attributes is removed below
    # as an ordinary tag, leaving no line break.
    page_text = re.sub(r"(?i)<br\s*/?>", "\n", page_text)
    # The closing tag of a block ends its line. The tag name must be followed directly by ">".
    page_text = re.sub(r"(?i)</(?:p|div|li|tr|h[1-6]|blockquote|td|th|dt|dd|option|pre)>", "\n", page_text)
    page_text = re.sub(
        r"(?i)<h(?P<heading_level>[1-6])[^>]*>",
        lambda heading_tag: "\n" + "#" * int(heading_tag["heading_level"]) + " ",
        page_text,
    )
    # "<li" followed by anything up to ">": this also matches <link> tags, which leave a stray "- " near the top.
    page_text = re.sub(r"(?i)<li[^>]*>", "- ", page_text)
    # Every remaining tag, including ones that span lines ([^>] matches newlines). A bare "<" in the text
    # is taken for a tag too, so the words between it and the next ">" are lost.
    page_text = re.sub(r"(?s)<[^>]+>", " ", page_text)
    page_text = html.unescape(page_text)
    # Runs of spaces, tabs, carriage returns and non-breaking spaces (&nbsp;) become one space.
    page_text = re.sub(r"[ \t\r\xa0]+", " ", page_text)
    # Two or more line breaks, with only whitespace between them, become one blank line.
    page_text = re.sub(r"\n\s*\n+", "\n\n", page_text)
    return page_text.strip()


# The old name of convert_html_to_text, kept so code that does "from html2text import html2text" still works.
html2text = convert_html_to_text


if __name__ == "__main__":
    main(sys.argv[1:])
