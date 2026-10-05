#!/usr/bin/env python3
"""Crude but dependable HTML → text for archived pages (stdlib only).

    python3 tools/html2text.py corpus/teamwiess.com/mirror/teamwiess.com/20070720__nod.html
Drops scripts/styles, keeps headings and paragraphs on their own lines, unescapes entities.
"""
import html
import re
import sys


def html2text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<!--.*?-->", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|blockquote|td|th|dt|dd|option|pre)>", "\n", raw)
    raw = re.sub(r"(?i)<(h[1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)[1]) + " ", raw)
    raw = re.sub(r"(?i)<li[^>]*>", "- ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\r\xa0]+", " ", raw)
    raw = re.sub(r"\n\s*\n+", "\n\n", raw)
    return raw.strip()


def main():
    for path in sys.argv[1:] or ["-"]:
        data = sys.stdin.buffer.read() if path == "-" else open(path, "rb").read()
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                text = data.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        print(html2text(text))


if __name__ == "__main__":
    main()
