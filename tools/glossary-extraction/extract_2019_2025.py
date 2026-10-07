#!/usr/bin/env python3
"""Extract the 2019, 2021, 2024 and 2025 O-Week glossaries from the books' reading-order text layer.

These four books come from the maintainer's own collection and are not handled by run_all.py and
finalize.py. Here the terms on each page were read off the page by hand and listed in TERMS_BY_PAGE_BY_YEAR.
A term's definition is the text from the start of its entry to the start of the next listed term on the same
page, without the running heads and footers. The few entries spoiled by a column split or another extraction
artefact were checked against the page by eye and are given whole in DEFINITION_FIXES_BY_YEAR. Keeping the
lists here means the TSVs can be re-derived without reading the pages again.

It reads one text file per book, with the pages separated by form feeds:

    historian-collection/text-raw/<year>-oweek-book.txt, in the corpus folder

and writes one TSV per book, with the columns term, definition, source_key (oweek-<year>) and locator (p.N):

    sources/glossaries/<year>.tsv, in this repository

for 2019, 2021, 2024 and 2025, in that order. The output folder must already exist. tools/paths.py finds
the corpus folder (see README.md).

Run it from anywhere:

    python3 tools/glossary-extraction/extract_2019_2025.py

It prints "<year> <count>" for each file it writes. These lines on standard error are not errors, but each
one means the page should be checked:

    "  <year> p.<page>: term not found: <term>"
        no line on that page starts with the term, so it has no row. A fix for it in
        DEFINITION_FIXES_BY_YEAR is not used either.
    "  <year> p.<page>: <term> at lines [...]; taking first"
        more than one line starts with the term. The first is used, except for "Wiessmen", which takes
        the last although the message says "taking first".

If it stops with a Python traceback, the years before the one it was working on are written and the rest
are not. Fix the cause and run it again.

    FileNotFoundError: ...text-raw/<year>-oweek-book.txt    that book's text file is missing.
    FileNotFoundError: ...sources/glossaries/<year>.tsv     the output folder does not exist.
    IndexError: list index out of range                     a page number is beyond the end of that book's text.
"""

import os
import re
import sys
from typing import NamedTuple

# This repository's tools/ folder, for paths.py.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import REPOSITORY_ROOT, corpus_folder  # noqa: E402  (needs the sys.path line above)

# The book text in the corpus, and where the TSVs go; see the module docstring.
BOOK_TEXT_ROOT = f"{corpus_folder()}/historian-collection/text-raw"
GLOSSARIES_ROOT = f"{REPOSITORY_ROOT}/sources/glossaries"

# Running heads, section headings and page footers, removed before terms are looked for. Each is matched
# against a whole line, after runs of spaces and tabs in it are collapsed to one space.
PAGE_FURNITURE_PATTERNS = [
    r"^WIESS$",
    r"^SPEAK$",
    r"^RICE$",
    r"^WIESS SPEAK$",
    r"^RICE SPEAK$",
    r"^Glossary of all things Wiess\.$",
    r"^Don’t worry, you’ll catch on quick!$",
    r"^Other terms that are good to know\.$",
    r"^Rice terms that are good to know\.$",
    r"^Acronyms & Abbreviations:$",
    r"^Campus Essentials:$",
    r"^Campus Essentials Continued\.\.\.$",
    r"^Unique to Rice:$",
    r"^Events:$",
    r".*WIESS COLLEGE O-WEEK 20\d\d \| \d+$",  # the page footer, e.g. "WIESS COLLEGE O-WEEK 2019 | 14"
]

# The 2019 and 2021 glossaries have a table, "What to call people from...", on their last page. Its cells are
# removed from that page, as whole lines, and the table is written as one summary row at the end instead.
NICKNAME_TABLE_PAGE_BY_YEAR = {"2019": 19, "2021": 23}
NICKNAME_TABLE_LINES = {
    "WHAT TO CALL PEOPLE FROM...", "College", "Nickname", "Baker", "Bakerite", "Will Rice", "Will Ricer", "Hanszen",
    "Hanszenite", "Jones", "Jonesian", "Brown", "Brownie", "Lovett", "Lovetteer", "Sid Richardson", "Sidizen", "Martel",
    "Martelian", "McMurtry", "Murt", "Duncan", "Duncaroo",
}
NICKNAME_TABLE_DEFINITION = (
    "(table) Baker—Bakerite; Will Rice—Will Ricer; Hanszen—Hanszenite; Jones—Jonesian; Brown—Brownie; "
    "Lovett—Lovetteer; Sid Richardson—Sidizen; Martel—Martelian; McMurtry—Murt; Duncan—Duncaroo."
)

# In these books a term may be followed by a full stop ("Pub. The..."); in the others, only by a space.
YEARS_WITH_FULL_STOP_AFTER_TERM = ("2024", "2025")

# The terms on each glossary page (numbered as in the text file, from 1), read off the page by hand. The
# order within a page does not matter: entries are written in the order they start on the page.
TERMS_BY_PAGE_BY_YEAR = {
    "2019": {
        14: [
            "Cabinet", "2FK/3FK", "Commons", "Acabowl", "Acagliders", "Acagrills", "Acaterrace", "Acatramp",
            "A-Fellows", "Associates’ Night", "Bacaterrace", "Basement", "Battlesows", "College Night", "Corner",
            "Cozy Corner", "Fellows", "Freshman One-Acts", "Freshman Service Points", "Goldenrod",
        ],
        15: [
            "Head Fellows", "Mentors", "NOD", "Wiess Day", "Stacks", "Summit", "OC Lounge", "Team Wiess", "PDR", "TFW",
            "Pumpkin Caroling", "TFFW", "Room Draw", "Saturday Morning Cartoons", "Servery", "Turnover", "Ubangee",
            "Upper Commons", "War Pig", "Sparky’s", "Wilson House (Wiess Magister House)", "Tabletop", "Wiessmen",
        ],
        16: [
            "45, 90, 180", "Academ", "Academic Quad", "BRC", "Brochstein", "Archi (AR-kee)", "ASB", "Associate",
            "Autry", "Baker 13", "Baker Institute", "Beer Bike", "Beyond the hedges", "Big Three", "Campanile",
            "ChBE (“Chubby”)", "Coffeehouse", "Cohen House", "CTIS", "D1, D2, D3",
        ],
        17: [
            "Esperanza", "Fondren", "Frog Wall", "FWIS", "GSA", "H&D", "Hedges", "The Hoot", "IM", "Inner Loop",
            "Ironman/Ironwoman", "Jack", "Jones School", "KTRU (KAY-true)", "LPAP", "Matriculation", "Media Center",
            "Mudd Lab", "MOB", "Musi (Myoo-zee)", "OC", "Outer Loop",
        ],
        18: [
            "PAA", "PCA", "Private Party", "Powderpuff", "Pre-Reqs", "Pub", "Q-Card", "R2 (The Rice Review)", "The Rec",
            "The Bookstore", "REMS", "RHA", "RMC", "Rondelet", "RPC", "RSVP", "Public Party", "RUPD", "Pumpkin Grades",
            "Rustication",
        ],
        19: [
            "SA", "Wiess", "Willy Week", "Sallyport", "Sammy the Owl", "Screw-Yer-Roommate", "Skyspace",
            "Willy’s Statue", "Y’all", "SMR", "Village", "Whataburger", "Tetra Points", "Thresher", "Valhalla",
        ],
    },
    "2021": {
        18: [
            "2FK/3FK", "Acabowl", "Acagliders", "Acagrills", "Acaterrace", "A-Fellows", "Associates’ Night",
            "Bacaterrace", "Battlesows", "Cabinet", "Changeover", "Commons", "College Night", "Corner", "Cozy Corner",
            "Fellows", "Fourth Floor Balcony", "Freshman One-Acts", "Freshman Service Points", "Goldenrod",
            "Head Fellows",
        ],
        19: [
            "Housing Jack", "Mentors", "Movie Room", "NOD", "OC Lounge", "Stacks", "Summit", "Team Wiess", "TFW", "PDR",
            "TFFW", "Piggy Week", "Ubangee", "Pumpkin Caroling", "Upper Commons", "Servery", "War Pig", "Sparky’s",
            "Tabletop", "Wilson House (Wiess Magister House)", "Wiessmen", "Wiess Day",
        ],
        20: [
            "45, 90, 180", "Academ", "Brochstein", "Academic Quad", "Archi (AR-kee)", "ASB", "Associate", "Autry",
            "Baker 13", "Baker Institute", "Beer Bike", "Beyond the hedges", "Big Three", "BRC", "Campanile",
            "ChBE (“Chubby”)", "Coffeehouse (“Chaus”)", "Cohen House", "CTIS", "D1, D2, D3",
        ],
        21: [
            "Esperanza", "Fondren (“Fondy”)", "Frog Wall", "FWIS", "GSA", "H&D", "Hedges", "Ironman/Ironwoman",
            "Island", "Jack", "Jones School", "KTRU (KAY-true)", "LPAP", "Matriculation", "The Hoot", "Media Center",
            "IM", "Inner Loop", "Mudd Lab", "MOB", "Musi (Myoo-zee)", "OC", "Outer Loop",
        ],
        22: [
            "PAA", "PCA", "R2 (The Rice Review)", "The Rec", "The Bookstore", "Private Party", "Powderpuff", "Pre-Reqs",
            "Pub", "REMS", "RHA", "RMC", "Rondelet", "RPC", "RSVP", "RUPD", "Public Party", "Rustication",
            "Pumpkin Grades", "Q-Card", "SA",
        ],
        23: [
            "Sallyport", "Y’all", "Sammy the Owl", "Screw-Yer-Roommate", "Skyspace", "SMR", "Tetra Points", "Thresher",
            "Valhalla", "Rice Village", "Whataburger", "Wiess",
        ],
    },
    "2024": {
        25: [
            "Associates’ Night", "Housing Jack", "Piggy Week", "Pumpkin Caroling", "Servery", "Summit", "Battlesows",
            "Team Wiess", "Cabinet", "Changeover", "Commons Culture", "Corner", "Cozy Corner", "Fellows/Advisors",
            "Freshman Service Points", "Goldenrod", "Head Fellows", "TFW", "TFFW", "Ubangee", "Warpig",
            "Wilson House (Wiess Magister House)", "Wiessmen",
        ],
        26: [
            "ASB", "RSVP", "CDOD", "CTIS", "FWIS", "GSA", "H&D", "KTRU (KAY-true)", "LPAP", "OC", "RUPD", "SA",
            "The MOB", "Beer Bike", "BRC", "Brochstein", "Coffeehouse (“Chaus”)", "Fondren (“Fondy”)", "Inner Loop",
            "REMS", "RMC", "RPC", "Jones Business School", "Mudd Lab", "Outer Loop",
        ],
        27: [
            "Pub", "Beyond the Hedges", "Associate", "Sallyport", "Campanile", "Skyspace", "D1, D2, D3", "The Hoot",
            "The Island", "The Rec", "Rice Village", "Baker 13", "Jack", "Powderpuff", "Pumpkin Grades", "Rustication",
            "Sammy the Owl", "Esperanza", "Intramural (IM) Sports", "Matriculation", "Rondelet", "Screw-Yer-Roommate",
            "Tetra", "Thresher", "Wiess",
        ],
    },
    "2025": {
        26: [
            "Associates’ Night", "Housing Jack", "Piggy Week", "Pumpkin Caroling", "Servery", "Summit", "Battlesows",
            "Team Wiess", "Cabinet", "Changeover", "Commons Culture", "Corner", "Cozy Corner", "Fellows/Advisors",
            "Freshman Service Points", "Goldenrod", "Head Fellows", "TFW", "TFFW", "Ubangee", "Warpig",
            "Wilson House (Wiess Magister House)", "Wiessmen",
        ],
        27: [
            "ASB", "RUPD", "CDOD", "SA", "CTIS", "FWIS", "The MOB", "GSA", "H&D", "Beer Bike", "KTRU (KAY-true)",
            "LPAP", "OC", "BRC", "Brochstein", "Coffeehouse (“Chaus”)", "Fondren (“Fondy”)", "Inner Loop",
            "Jones Business School", "REMS", "RMC", "RPC", "Mudd Lab", "Outer Loop",
        ],
        28: [
            "Pub", "Sallyport", "Skyspace", "The Hoot", "The Island", "The Rec", "Rice Village", "Campanile",
            "D1, D2, D3", "Jack", "Powderpuff", "Pumpkin Grades", "Rustication", "Sammy the Owl", "Esperanza",
            "Intramural (IM) Sports", "Matriculation", "Screw-Yer-Roommate", "Tetra", "Wiess", "Associate",
            "Beyond the Hedges", "Thresher",
        ],
    },
}

# Students from the 2023-24 academic year on are not named on the site (STYLE.md, rule 7). In these entries
# the names are matched by the words around them, so the names themselves never appear in this file.
STUDENT_NAMES_PATTERN_BY_YEAR_AND_TERM = {
    ("2024", "Head Fellows"): r"(?<=since January: ).*?(?=\. Say hello)",
    ("2025", "Head Fellows"): r"(?<=since January: ).*?(?=\. Say hello)",
}
STUDENT_NAMES_PLACEHOLDER = "[three names omitted]"

# Column splits and extraction artefacts, each checked against the layout text of the page: the term's
# definition is replaced by this one.
DEFINITION_FIXES_BY_YEAR = {
    "2019": {
        "Summit": (
            "Weekend retreat to a body of water (pool/beach/lake/etc.) during the fall semester to discuss Wiess "
            "issues and bond with other Wiessmen."
        ),
    },
    "2021": {
        "Wiess": "Your home and family.",
        "Academ": "Humanities or Social Sciences major. A very archaic term.",
        "BRC": (
            "BioScience Research Collaborative, where Rice meets the Texas Medical Center for research. Also where "
            "Bioengineers spend most of their time for class starting junior year."
        ),
        "Inner Loop": "The one-way road that loops around the center of campus.",
        "Hedges": "Extensive botanical growth that surrounds campus and the Academic Quad.",
        "Outer Loop": "The three-mile long path that encircles [the entry breaks off here in the book]",
        "Y’all": "Southern slang short for “you all.” Soon enough, y’all will be saying this too. (It’s efficient!)",
        "Sammy the Owl": "The Rice mascot.",
        "Skyspace": (
            "The pyramidal installation located next to the Shepherd School of Music. A reat place to watch the "
            "sunrise and sunset."
        ),
        "RPC": (
            "Rice Program Council. The organization in charge of university-wide events such as Beer Bike, "
            "Screw-Yer-Roommate, Esperanza, and study breaks during finals."
        ),
        "Baker Institute": (
            "The James A. Baker III Institute for Public Policy. Holds many interesting talks and events that are "
            "typically open to undergraduates. Not to be confused with Baker College."
        ),
    },
    "2024": {
        "ASB": "Alternative Spring Break; a service trip over spring break based on a social issue.",
        "RPC": (
            "Rice Program Council. The organization in charge of university-wide events such as Beer Bike, "
            "Screw-Yer-Roommate, Esperanza, and study breaks during finals."
        ),
        "Outer Loop": (
            "The 5 kilometer loop that surrounds all of Rice University. Students often run along the path surrounding "
            "the loop."
        ),
    },
    "2025": {
        "ASB": "Alternative Spring Break; a service trip over spring break based on a social issue.",
        "RPC": (
            "Rice Program Council. The organization in charge of university-wide events such as Beer Bike, "
            "Screw-Yer-Roommate, Esperanza, and study breaks during finals."
        ),
        "Outer Loop": (
            "The 5 kilometer loop that surrounds all of Rice University. Students often run along the path surrounding "
            "the loop."
        ),
    },
}


class GlossaryEntry(NamedTuple):
    """One term of a book's glossary, as written to its TSV."""

    term: str  # as listed in TERMS_BY_PAGE_BY_YEAR
    definition: str
    locator: str  # "p.N", the page in the text file


def main() -> None:
    """Extract and write each year's glossary in turn, printing the number of entries in each."""
    for year in TERMS_BY_PAGE_BY_YEAR:
        entries = extract_glossary(year)
        write_glossary(year, entries)
        print(year, len(entries))


def extract_glossary(year: str) -> list[GlossaryEntry]:
    """Return one year's glossary entries in page order, with the nickname table's summary row last."""
    with open(f"{BOOK_TEXT_ROOT}/{year}-oweek-book.txt", encoding="utf-8") as book_text:
        pages = book_text.read().split("\f")

    entries_by_page: dict[int, list[GlossaryEntry]] = {}
    for page_number, terms in TERMS_BY_PAGE_BY_YEAR[year].items():
        lines = remove_page_furniture(pages[page_number - 1])
        if year in NICKNAME_TABLE_PAGE_BY_YEAR and page_number == NICKNAME_TABLE_PAGE_BY_YEAR[year]:
            lines = [line for line in lines if line not in NICKNAME_TABLE_LINES]
        first_line_by_term = find_entry_starts(year, page_number, terms, lines)
        entries_by_page[page_number] = split_entries(year, page_number, first_line_by_term, lines)

    # Sorted, so the file is in page order even if TERMS_BY_PAGE_BY_YEAR lists a page out of order.
    entries = [entry for page_number in sorted(entries_by_page) for entry in entries_by_page[page_number]]
    if year in NICKNAME_TABLE_PAGE_BY_YEAR:
        table_locator = f"p.{NICKNAME_TABLE_PAGE_BY_YEAR[year]}"
        entries.append(GlossaryEntry("What to call people from…", NICKNAME_TABLE_DEFINITION, table_locator))
    return entries


def remove_page_furniture(page_text: str) -> list[str]:
    """Return the page's lines with spacing collapsed and running heads and footers removed.

    Blank lines are kept, as empty strings. The line numbers in the warnings count from 0 in this list, so
    they count blank lines but not removed ones.
    """
    lines = []
    for raw_line in page_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line.strip().replace("\t", " ")).strip()
        if not line:
            lines.append("")
            continue
        if any(re.match(furniture_pattern, line) for furniture_pattern in PAGE_FURNITURE_PATTERNS):
            continue
        lines.append(line)
    return lines


def find_entry_starts(year: str, page_number: int, terms: list[str], lines: list[str]) -> dict[str, int]:
    """Return the line on which each term's entry starts, warning about terms found nowhere or more than once.

    An entry starts at a line beginning with its term and a space (or a full stop, in some years). Terms are
    placed longest first, and a line already taken is skipped, so "Wiess Day" takes its line before "Wiess"
    can match it.
    """
    allow_full_stop = year in YEARS_WITH_FULL_STOP_AFTER_TERM
    first_line_by_term: dict[str, int] = {}
    for term in sorted(terms, key=len, reverse=True):
        matching_lines = [
            line_number
            for line_number, line in enumerate(lines)
            if starts_with_term(line, term, allow_full_stop) and line_number not in first_line_by_term.values()
        ]
        if not matching_lines:
            print(f"  {year} p.{page_number}: term not found: {term}", file=sys.stderr)
            continue
        if len(matching_lines) > 1:
            print(f"  {year} p.{page_number}: {term} at lines {matching_lines}; taking first", file=sys.stderr)
        first_line_by_term[term] = matching_lines[-1] if term == "Wiessmen" else matching_lines[0]
    return first_line_by_term


def starts_with_term(line: str, term: str, allow_full_stop: bool) -> bool:
    """Return whether the line begins with the term followed by a space, or by ". " when allow_full_stop is set."""
    return line.startswith(term + " ") or (allow_full_stop and line.startswith(term + ". "))


def split_entries(
    year: str,
    page_number: int,
    first_line_by_term: dict[str, int],
    lines: list[str],
) -> list[GlossaryEntry]:
    """Return the page's entries in the order they start, each running up to the next entry's start.

    The last entry on the page runs to the end of the page. A term in DEFINITION_FIXES_BY_YEAR gets the
    definition given there instead of the extracted one.
    """
    terms_in_page_order = sorted(first_line_by_term, key=first_line_by_term.get)
    first_lines = [first_line_by_term[term] for term in terms_in_page_order]
    end_lines = [*first_lines[1:], len(lines)]
    entries = []
    for term, first_line, end_line in zip(terms_in_page_order, first_lines, end_lines):
        definition = read_definition(term, lines[first_line:end_line])
        definition = DEFINITION_FIXES_BY_YEAR.get(year, {}).get(term, definition)
        definition = withhold_student_names(year, term, definition)
        entries.append(GlossaryEntry(term, definition, f"p.{page_number}"))
    return entries


def withhold_student_names(year: str, term: str, definition: str) -> str:
    """Return the definition with any current students' names replaced, per STUDENT_NAMES_PATTERN_BY_YEAR_AND_TERM."""
    names_pattern = STUDENT_NAMES_PATTERN_BY_YEAR_AND_TERM.get((year, term))
    if names_pattern is None:
        return definition
    return re.sub(names_pattern, STUDENT_NAMES_PLACEHOLDER, definition, count=1)


def read_definition(term: str, entry_lines: list[str]) -> str:
    """Return the text of an entry after its term and any full stop, as one line."""
    first_line_rest = entry_lines[0][len(term):].lstrip()
    if first_line_rest.startswith(". "):
        first_line_rest = first_line_rest[2:]
    elif first_line_rest.startswith("."):
        first_line_rest = first_line_rest[1:].lstrip()
    definition = " ".join([first_line_rest] + [line for line in entry_lines[1:] if line]).strip()
    definition = definition.replace("­", "")  # soft hyphens
    definition = re.sub(r"\s+", " ", definition)
    return definition.replace("nonmusic", "non-music")


def write_glossary(year: str, entries: list[GlossaryEntry]) -> None:
    """Write sources/glossaries/<year>.tsv, without quoting, with oweek-<year> as every row's source_key."""
    with open(f"{GLOSSARIES_ROOT}/{year}.tsv", "w", encoding="utf-8") as glossary:
        glossary.write("term\tdefinition\tsource_key\tlocator\n")
        for entry in entries:
            glossary.write(f"{entry.term}\t{entry.definition}\toweek-{year}\t{entry.locator}\n")


if __name__ == "__main__":
    main()
