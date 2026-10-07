#!/usr/bin/env python3
"""Compare two years' O-Week glossaries: terms added, dropped and reworded, with both definitions.

tools/build_glossary_series.py writes sources/glossaries/_diff.md, which lists the terms that changed
between every pair of neighbouring years but not what they said. This script shows the definitions
themselves, for any two years, so an editor writing a Changes page can quote them side by side.

It reads the two tables from sources/glossaries/, matching terms the same way build_glossary_series.py
does. It writes no files; it prints a Markdown report. Give it the earlier year first, using the labels the
glossary page uses (the year for an O-Week book; year and kind for another source, such as the Owlmanac):

    python3 tools/diff_glossary.py 2011 2014
    python3 tools/diff_glossary.py 2016 2016-owlmanac

Terms are listed in order of their normalised form, and a reworded term is shown under its later
spelling. A term counts as reworded only if its definition changed by more than case, punctuation and
spacing. Any arguments after the first two are ignored.

Since it writes nothing, a failed run leaves nothing to clean up. It stops with a Python traceback,
before printing anything, if it is given fewer than two years or a year with no table
(FileNotFoundError, naming the labels there are). A row that has a term but no definition (only one column) stops it with an
AttributeError once the added and dropped lists are printed, if that term is in both years; in only
one year, the row is listed as added or dropped with its definition printed as None. A table with no
definition column stops it with KeyError: 'definition' at the first definition it needs from that
table, which may be partway through the Added or Dropped list. A table with no term column counts as
empty, so every term of the other year shows as added or dropped.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_glossary_series import find_glossary_files, normalise_definition, read_glossary_file


def main(arguments: list[str]) -> None:
    """Print the terms the second year added, the ones it dropped, and the ones it reworded."""
    earlier_year, later_year, *_ignored = arguments
    glossary_files = find_glossary_files()
    for year in (earlier_year, later_year):
        if year not in glossary_files:
            raise FileNotFoundError(f"no glossary labelled {year!r}; there are: {', '.join(glossary_files)}")
    earlier_glossary = read_glossary_file(glossary_files[earlier_year])
    later_glossary = read_glossary_file(glossary_files[later_year])
    added_terms = sorted(set(later_glossary) - set(earlier_glossary))
    dropped_terms = sorted(set(earlier_glossary) - set(later_glossary))

    print(f"# {earlier_year} → {later_year}\n")
    print(f"## Added in {later_year} ({len(added_terms)})")
    for term in added_terms:
        print(f"- **{later_glossary[term]['term']}**—{later_glossary[term]['definition']}")
    print(f"\n## Dropped after {earlier_year} ({len(dropped_terms)})")
    for term in dropped_terms:
        print(f"- **{earlier_glossary[term]['term']}**—{earlier_glossary[term]['definition']}")

    # Worked out only after the first two lists are printed: a row with a term but no definition (None)
    # stops the script here, and the lists above have still reached the editor.
    reworded_terms = [
        term
        for term in sorted(set(earlier_glossary) & set(later_glossary))
        if normalise_definition(earlier_glossary[term]["definition"])
        != normalise_definition(later_glossary[term]["definition"])
    ]
    print(f"\n## Reworded ({len(reworded_terms)})")
    for term in reworded_terms:
        print(
            f"- **{later_glossary[term]['term']}**\n"
            f"    - {earlier_year}: {earlier_glossary[term]['definition']}\n"
            f"    - {later_year}: {later_glossary[term]['definition']}"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
