#!/usr/bin/env python3
"""Build the glossary-by-year page and the year-to-year diff from the O-Week glossary tables.

Every O-Week book ends with a glossary of Wiess words. Editors type each book's glossary into a table
in sources/glossaries/, and this script lines the tables up by term, so a reader can follow one word
through the years and an editor can see what each book added, dropped or reworded. The page is
generated: fixing it by hand would be overwritten on the next run, so fixes go in the tables.

It reads every sources/glossaries/<source key>.tsv except files whose names start with "_". Each has a
header row and the columns term, definition, source_key and locator:

    War Pig<TAB>The Wiess mascot...<TAB>oweek-2006<TAB>p.84

A table is named for the bibliography key of its source, so the file says where its words came from:
oweek-2006.tsv, owlmanac-2016.tsv, handbook-1994.tsv. On the page each table is labelled by its year,
with the kind of source added for anything but an O-Week book: "2006", "2016-owlmanac", "1994-handbook"
(see label_glossary). Tables are put in order by year, an O-Week book before another source of the same
year; a name with no year at its end goes last, labelled by its whole name.

Terms are matched across years after normalising them: lower case, keeping only the letters a-z,
digits and spaces, with the spellings listed in TERM_ALIASES mapped to one term ("The Ubangee" and
"Ubangee" are one term; so are "War pig" and "War Pig"). A book that renamed something is grouped
under one term the same way. Each term is shown under the spelling of the first year it appears in.

It writes two files, replacing them completely:

    docs/traditions/glossary-series.md   one section per term found in two or more years, then the
                                         terms found in only one year, each definition with its citation
    sources/glossaries/_diff.md          for each pair of neighbouring years, the terms added, dropped
                                         and reworded (the raw material for the Changes pages)

Run it after editing any glossary table. CI runs it before every site build
(.github/workflows/pages.yml), so the published page always matches the tables:

    python3 tools/build_glossary_series.py

It prints one line naming both files and counting the terms. If it stops instead:

    "no sources/glossaries/*.tsv yet"    no tables were found; nothing written.
    a Python traceback                   nothing written. KeyError: 'definition' means a table has no
                                         definition column; an AttributeError on None means a row has
                                         a term but no definition (only one column). ModuleNotFoundError:
                                         markdown means MkDocs is not installed
                                         (pip install -r requirements.txt).

Some input is skipped without a message: rows with an empty term, every row of a table with no term
column, and the earlier of two rows in one table whose terms normalise the same (the later row is
used). A table with no source_key column, or a row with an empty or missing source_key, gives entries
without citations; with no locator column, or none in the row, the citation has no page ("[@oweek-2006]").
"""

import csv
import glob
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSSARIES_ROOT = os.path.join(REPO_ROOT, "sources", "glossaries")  # tools/diff_glossary.py reads it too
GLOSSARY_FILES_GLOB = os.path.join(GLOSSARIES_ROOT, "*.tsv")
SERIES_PAGE_FILE = os.path.join(REPO_ROOT, "docs", "traditions", "glossary-series.md")
DIFF_FILE = os.path.join(GLOSSARIES_ROOT, "_diff.md")

# The front matter of the generated page. last_reviewed is fixed text: running the script does not change it.
SERIES_PAGE_FRONT_MATTER = (
    "---\n"
    "title: How we described ourselves, by year\n"
    "status: generated\n"
    "last_reviewed: 2026-10-04\n"
    "reviewed_by: tools/build_glossary_series.py\n"
    "---\n"
)

# A glossary file name: a bibliography key of the kind of source, a hyphen and a year ("owlmanac-2016").
GLOSSARY_FILE_NAME_PATTERN = re.compile(r"(?P<kind>.+)-(?P<year>\d{4})")

# Normalised spellings (see normalise_term) mapped to the one term they all mean. Every term on the right
# also lets a leading "the" be dropped from what the books print, so "the team wiess" becomes "team wiess";
# that is all an entry mapped to itself does. Keys still holding punctuation ("team wiess!",
# "nod (night of decadence)") never match, because normalising removes it first; their forms without
# punctuation are listed too.
TERM_ALIASES = {
    # same thing, different spelling / punctuation / abbreviation across the books
    "warpig": "war pig", "the war pig": "war pig",
    "the ubangee": "ubangee", "ubangeee": "ubangee",
    "team wiess": "team wiess", "team wiess!": "team wiess", "tfw": "team family wiess",
    "night of decadence": "nod", "nod (night of decadence)": "nod", "night of decadence nod": "nod",
    "nod night of decadence": "nod",
    "battle sows": "battlesows", "the battle sows": "battlesows",
    "filmfest": "filmfest", "film fest": "filmfest", "filmest": "filmfest",
    "jamfest": "jamfest", "jam fest": "jamfest", "jamfestwiess day": "jamfest",
    "tabletop": "tabletop theatre", "tabletop theater": "tabletop theatre", "table top": "tabletop theatre",
    "pumpkin caroling": "pumpkin caroling", "pumpkin carolling": "pumpkin caroling",
    "beerbike": "beer bike",
    "gofer": "gopher", "gophers": "gopher",
    "freshman oneacts": "freshmen oneacts", "freshman service points": "freshmen service points",
    "wiess house": "wiess master house", "wilson house wiess master house": "wiess master house",
    "wiess master house wilson house": "wiess master house",
    "wilson house wiess magisters house": "wiess master house",
    "backaterrace": "acaterrace",
    "club 13": "baker 13",
    "early 80s": "80s party",
    "ktru kattrue": "ktru kaytrue",
    "musi moozee": "musi", "musi myoozee": "musi",
    "campanile kampaneelee": "campanile",
    "the hoot": "hoot", "hoot the": "hoot",
    "pavillion the": "brochstein",
    "fondrenfondy": "fondren",
    "housing dining": "hd",
    "gsa graduate student association": "gsa", "mob the marching owl band": "mob", "oc off campus": "oc",
    "rems rice emergency medical service": "rems", "rmc rice memorial center": "rmc",
    "rpc rice program council": "rpc", "sa student association": "sa", "room draw jack": "room draw",
    "baker institutebaker hall": "baker institute", "screwyerroommate": "screw yer roommate",
    "passfail": "pf", "rice village": "village", "leebron": "leebron and ping",
    "bc lindsay": "bc", "doward christie": "doward", "mike denise": "mike",
    "ironmanironwoman": "ironmanironwoman",
    # 2019–2025 books (maintainer's collection)
    "acagliders": "acaglider", "acagrills": "acagrill", "afellows": "affiliates",
    "wilson house wiess magister house": "wiess master house",
    "the bookstore": "bookstore", "coffeehouse chaus": "coffeehouse", "fondren fondy": "fondren",
    "the island": "island", "jones business school": "jones school", "intramural im sports": "im",
    "tetra": "tetra points", "fellowsadvisors": "fellows", "commons culture": "commons",
    # renamed in the books, same thing: grouped so the rename shows in the series
    "housing jack": "room draw", "piggy week": "willy week", "changeover": "turnover",
}

# One row of a glossary table, keyed by the header: term, definition, source_key, locator. The hint says
# every value is a string, but csv.DictReader fills the fields missing from a short row with None, not "",
# and keeps extra columns as a list under the key None.
GlossaryEntry = dict[str, str]


def main() -> None:
    """Read every glossary table, then write the series page and the year-to-year diff."""
    glossaries = load_glossaries()
    if not glossaries:
        raise SystemExit("no sources/glossaries/*.tsv yet")
    years = list(glossaries)
    entries_by_term, display_name_by_term = group_entries_by_term(glossaries)
    recurring_terms, one_off_terms = sort_terms_by_recurrence(entries_by_term, display_name_by_term)

    # The whole page is rendered before anything is written, so a bad row stops the script with both
    # files untouched.
    page_lines = (
        [SERIES_PAGE_FRONT_MATTER]
        + render_introduction(years)
        + render_recurring_terms(recurring_terms, entries_by_term, display_name_by_term, years)
        + render_one_off_terms(one_off_terms, entries_by_term, years)
    )
    write_lines(SERIES_PAGE_FILE, page_lines)
    write_lines(DIFF_FILE, render_year_to_year_diff(glossaries, display_name_by_term))

    print(
        f"wrote {SERIES_PAGE_FILE} ({len(recurring_terms)} series terms, {len(one_off_terms)} one-offs) "
        f"and {DIFF_FILE}"
    )


def load_glossaries() -> dict[str, dict[str, GlossaryEntry]]:
    """Return each table's glossary entries by normalised term, keyed by its label, in order."""
    return {label: read_glossary_file(glossary_file) for label, glossary_file in find_glossary_files().items()}


def find_glossary_files() -> dict[str, str]:
    """Return every glossary table's file by its label ("2006", "2016-owlmanac"), in order of year.

    tools/diff_glossary.py and tools/add_glossary.py use this too, so they label and order the tables the
    same way as the page.
    """
    glossary_files = [
        glossary_file
        for glossary_file in glob.glob(GLOSSARY_FILES_GLOB)
        if not os.path.basename(glossary_file).startswith("_")
    ]
    return {
        label_glossary(os.path.splitext(os.path.basename(glossary_file))[0]): glossary_file
        for glossary_file in sorted(glossary_files, key=rank_glossary_file)
    }


def label_glossary(source_key: str) -> str:
    """Return a table's label: its year for an O-Week book, else year and kind ("1994-handbook")."""
    key_parts = GLOSSARY_FILE_NAME_PATTERN.fullmatch(source_key)
    if not key_parts:
        return source_key
    if key_parts["kind"] == "oweek":
        return key_parts["year"]
    return f"{key_parts['year']}-{key_parts['kind']}"


def rank_glossary_file(glossary_file: str) -> tuple[int, bool, str]:
    """Return a sort key: year, then O-Week books before other sources, then name; no year sorts last."""
    file_name = os.path.splitext(os.path.basename(glossary_file))[0]
    key_parts = GLOSSARY_FILE_NAME_PATTERN.fullmatch(file_name)
    if key_parts:
        return (int(key_parts["year"]), key_parts["kind"] != "oweek", key_parts["kind"])
    return (9999, True, file_name)


def group_entries_by_term(
    glossaries: dict[str, dict[str, GlossaryEntry]],
) -> tuple[dict[str, dict[str, GlossaryEntry]], dict[str, str]]:
    """Return each term's entry for every year it appears in, and the spelling to show it under.

    The spelling is the one printed in the first year that has the term, so a term keeps its oldest
    name and later renames appear beside their years.
    """
    entries_by_term: dict[str, dict[str, GlossaryEntry]] = {}  # term → {year: that year's entry}
    display_name_by_term: dict[str, str] = {}
    for year, entry_by_term in glossaries.items():
        for term, entry in entry_by_term.items():
            entries_by_term.setdefault(term, {})[year] = entry
            display_name_by_term.setdefault(term, entry["term"].strip())
    return entries_by_term, display_name_by_term


def sort_terms_by_recurrence(
    entries_by_term: dict[str, dict[str, GlossaryEntry]],
    display_name_by_term: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Return the terms found in two or more years, and those found in one, each sorted by display name.

    Display names are compared ignoring case, so a term a book printed in lower case sorts among the rest.
    """
    recurring_terms = sorted(
        (term for term, entry_by_year in entries_by_term.items() if len(entry_by_year) >= 2),
        key=lambda term: display_name_by_term[term].lower(),
    )
    one_off_terms = sorted(
        (term for term, entry_by_year in entries_by_term.items() if len(entry_by_year) == 1),
        key=lambda term: display_name_by_term[term].lower(),
    )
    return recurring_terms, one_off_terms


def render_introduction(years: list[str]) -> list[str]:
    """Return the page's title and opening paragraphs, which name every year the page is built from."""
    return [
        "# How we described ourselves, by year\n",
        "Every O-Week book ends with a glossary of Wiess words, written by that year's O-Week team for that year's "
        "freshmen. Line them up by year and you can watch the college change its mind.\n\n"
        "!!! abstract \"TL;DR\"\n"
        "    - Every Wiess word from the O-Week glossaries, year by year, with its book and page.\n"
        "    - Watch words drift: the War Pig is \"the Wiess mascot\" in 1994, \"**Former** Wiess mascot\" from 2006, "
        "and \"the giant wooden pig built by the Class of 2012\" from 2014.\n"
        "    - Skip to the one-year wonders at the bottom for the jokes that lasted a single semester.\n\n"
        "**How it works:** This page is built by a script from "
        f"{len(years)} glossaries ({', '.join(years)}). Want to fix something? Edit `sources/glossaries/*.tsv`, "
        "then run `tools/build_glossary_series.py`. Don't edit this page by hand.\n\n"
        "**Renamed things stay together:** When a book renamed something (Room Draw → Housing Jack, Willy Week → "
        "Piggy Week, Turnover → Changeover, Commons → Commons Culture), it's grouped under one term. "
        "The newer name shows in italics next to its year.\n",
    ]


def render_recurring_terms(
    recurring_terms: list[str],
    entries_by_term: dict[str, dict[str, GlossaryEntry]],
    display_name_by_term: dict[str, str],
    years: list[str],
) -> list[str]:
    """Return the table of terms found in two or more years, then one section per term, year by year.

    Each table row links to its term's section. A year whose book printed the term differently (ignoring
    case) from the section heading shows that spelling in italics, which is how renames become visible.
    """
    lines = [f"\n## Terms that recur ({len(recurring_terms)})\n", "\n| Term | Years present |\n|---|---|"]
    for term in recurring_terms:
        display_name = display_name_by_term[term]
        years_present = [year for year in years if year in entries_by_term[term]]
        lines.append(f"| [{display_name}](#{slugify_heading(display_name)}) | {', '.join(years_present)} |")
    lines.append("")

    for term in recurring_terms:
        display_name = display_name_by_term[term]
        lines.append(f"\n### {display_name}\n")
        for year in years:
            entry = entries_by_term[term].get(year)
            if not entry:
                continue
            printed_term = entry["term"].strip()
            renamed_label = f" (*{printed_term}*)" if printed_term.lower() != display_name.lower() else ""
            lines.append(f"- **{year}**{renamed_label}—{flatten_definition(entry)} {format_citation(entry)}")
    return lines


def slugify_heading(heading: str) -> str:
    """Return the anchor MkDocs gives a heading, so the table's links land on the term's section.

    The site's toc extension uses Python-Markdown's default slugify (mkdocs.yml sets no other), so
    calling that same function gives the same anchor. This assumes every heading on the page is unique.
    If two slugify the same (or a term's name matches a year heading such as "2016"), toc adds a suffix
    such as _1 to the later one, and the link opens the first.
    """
    # Python-Markdown is installed with MkDocs (requirements.txt). It is imported only when a link is made.
    from markdown.extensions.toc import slugify

    return slugify(heading, "-")


def render_one_off_terms(
    one_off_terms: list[str],
    entries_by_term: dict[str, dict[str, GlossaryEntry]],
    years: list[str],
) -> list[str]:
    """Return the terms found in only one year, under a heading for each year that has any."""
    lines = [
        f"\n## Terms that appear in only one glossary ({len(one_off_terms)})\n",
        "\nThese are often the best ones: a joke that lasted one semester, a staff member everyone knew, "
        "a rivalry that burned out.\n",
    ]
    for year in years:
        terms_of_year = [term for term in one_off_terms if year in entries_by_term[term]]
        if not terms_of_year:
            continue
        lines.append(f"\n### {year}\n")
        for term in terms_of_year:
            entry = entries_by_term[term][year]
            lines.append(f"- **{entry['term'].strip()}**—{flatten_definition(entry)} {format_citation(entry)}")
    return lines


def write_lines(output_file: str, lines: list[str]) -> None:
    """Replace output_file with the lines, joined by newlines and ending in one."""
    with open(output_file, "w", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def render_year_to_year_diff(
    glossaries: dict[str, dict[str, GlossaryEntry]],
    display_name_by_term: dict[str, str],
) -> list[str]:
    """Return, for each year and the year before it, the terms added, dropped and reworded.

    A term counts as reworded when its definition changed by more than case, punctuation and spacing
    (see normalise_definition). Terms are listed in order of their normalised form.
    """
    lines = [
        "# Glossary diffs, year to year\n",
        "Generated by tools/build_glossary_series.py. Feed for the Changes pages.\n",
    ]
    years = list(glossaries)
    for previous_year, year in zip(years, years[1:]):
        previous_terms, terms = set(glossaries[previous_year]), set(glossaries[year])
        added, dropped = sorted(terms - previous_terms), sorted(previous_terms - terms)
        reworded = sorted(
            term
            for term in previous_terms & terms
            if normalise_definition(glossaries[previous_year][term]["definition"])
            != normalise_definition(glossaries[year][term]["definition"])
        )
        lines.append(f"\n## {previous_year} → {year}\n")
        lines.append(f"- added ({len(added)}): " + ", ".join(display_name_by_term[term] for term in added))
        lines.append(f"- dropped ({len(dropped)}): " + ", ".join(display_name_by_term[term] for term in dropped))
        lines.append(f"- reworded ({len(reworded)}): " + ", ".join(display_name_by_term[term] for term in reworded))
    return lines


def read_glossary_file(glossary_file: str) -> dict[str, GlossaryEntry]:
    """Return one glossary table's entries by normalised term, skipping rows with no term.

    Also used by tools/diff_glossary.py. When two rows normalise to the same term, the later one wins.
    """
    with open(glossary_file, encoding="utf-8", newline="") as glossary:
        return {
            normalise_term(entry["term"]): entry
            for entry in csv.DictReader(glossary, delimiter="\t")
            if entry.get("term")
        }


def normalise_term(printed_term: str) -> str:
    """Return the form of a term used to match it across years.

    The term is lower-cased, stripped of everything but the letters a-z, digits and spaces (so accented
    letters are dropped), with runs of spaces collapsed, and looked up in TERM_ALIASES. A leading "the "
    is then dropped if what follows is a term some alias maps to.
    """
    term = re.sub(r"[^a-z0-9 ]+", "", printed_term.lower()).strip()
    term = re.sub(r"\s+", " ", term)
    term = TERM_ALIASES.get(term, term)
    if term.startswith("the ") and term[len("the "):] in TERM_ALIASES.values():
        term = term[len("the "):]
    return term


def normalise_definition(definition: str) -> str:
    """Return a definition lower-cased with punctuation and spacing collapsed, to spot real rewording."""
    return re.sub(r"\W+", " ", definition.lower()).strip()


def flatten_definition(entry: GlossaryEntry) -> str:
    """Return an entry's definition on one line, so it stays inside its Markdown list item."""
    return entry["definition"].strip().replace("\n", " ")


def format_citation(entry: GlossaryEntry) -> str:
    """Return the entry's citation, such as "[@oweek-2006 p.84]", or "" if it has no source_key."""
    locator = (entry.get("locator") or "").strip()
    if not entry.get("source_key"):
        return ""
    return f"[@{entry['source_key']}{(' ' + locator) if locator else ''}]"


if __name__ == "__main__":
    main()
