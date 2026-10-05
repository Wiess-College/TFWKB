#!/usr/bin/env python3
"""Diff two years' glossaries: added, dropped and reworded terms, with both definitions.

    python3 tools/diff_glossary.py 2011 2014
Reads sources/glossaries/<year>.tsv. For the whole series at once see build_glossary_series.py.
"""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_glossary_series import GLOSS, norm, norm_def  # noqa: E402


def load(year):
    with open(os.path.join(GLOSS, f"{year}.tsv"), encoding="utf-8", newline="") as fh:
        return {norm(r["term"]): r for r in csv.DictReader(fh, delimiter="\t") if r.get("term")}


def main():
    a, b = sys.argv[1], sys.argv[2]
    A, B = load(a), load(b)
    print(f"# {a} → {b}\n")
    print(f"## Added in {b} ({len(set(B)-set(A))})")
    for n in sorted(set(B) - set(A)):
        print(f"- **{B[n]['term']}** — {B[n]['definition']}")
    print(f"\n## Dropped after {a} ({len(set(A)-set(B))})")
    for n in sorted(set(A) - set(B)):
        print(f"- **{A[n]['term']}** — {A[n]['definition']}")
    changed = [n for n in sorted(set(A) & set(B)) if norm_def(A[n]["definition"]) != norm_def(B[n]["definition"])]
    print(f"\n## Reworded ({len(changed)})")
    for n in changed:
        print(f"- **{B[n]['term']}**\n    - {a}: {A[n]['definition']}\n    - {b}: {B[n]['definition']}")


if __name__ == "__main__":
    main()
