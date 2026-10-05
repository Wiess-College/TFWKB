#!/usr/bin/env python3
"""Build docs/traditions/glossary-series.md from sources/glossaries/<year>.tsv.

Each TSV has a header and columns: term, definition, source_key, locator
(e.g. "War Pig\tThe Wiess mascot…\toweek-2006\tp.84"). Terms are matched across years
case-insensitively after light normalisation ("The Ubangee" = "Ubangee"; "War pig" = "War Pig").

Output: one section per term that appears in two or more years (the series), then a
section listing terms that appear in only one year (the one-offs), each definition cited.
Also writes sources/glossaries/_diff.md: what each year added, dropped and reworded versus
the previous one—the raw material for the Changes pages.

    python3 tools/build_glossary_series.py
"""
import csv
import glob
import os
import re
from collections import OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSS = os.path.join(ROOT, "sources", "glossaries")
OUT = os.path.join(ROOT, "docs", "traditions", "glossary-series.md")
DIFF = os.path.join(GLOSS, "_diff.md")

ALIASES = {
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
    "wiess master house wilson house": "wiess master house", "wilson house wiess magisters house": "wiess master house",
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
    # 2019–2025 books (Historian's collection)
    "acagliders": "acaglider", "acagrills": "acagrill", "afellows": "affiliates",
    "wilson house wiess magister house": "wiess master house",
    "the bookstore": "bookstore", "coffeehouse chaus": "coffeehouse", "fondren fondy": "fondren",
    "the island": "island", "jones business school": "jones school", "intramural im sports": "im",
    "tetra": "tetra points", "fellowsadvisors": "fellows", "commons culture": "commons",
    # renamed in the books, same thing: grouped so the rename shows in the series
    "housing jack": "room draw", "piggy week": "willy week", "changeover": "turnover",
}


def norm(term: str) -> str:
    t = re.sub(r"[^a-z0-9 ]+", "", term.lower()).strip()
    t = re.sub(r"\s+", " ", t)
    t = ALIASES.get(t, t)
    if t.startswith("the ") and t[4:] in ALIASES.values():
        t = t[4:]
    return t


def load():
    years = OrderedDict()
    # sort by the leading year, then by name, so "2016-owlmanac" follows "2016"
    def ykey(p):
        b = os.path.splitext(os.path.basename(p))[0]
        m = re.match(r"(\d{4})(.*)", b)
        return (int(m.group(1)), m.group(2)) if m else (9999, b)
    for path in sorted(glob.glob(os.path.join(GLOSS, "*.tsv")), key=ykey):
        year = os.path.splitext(os.path.basename(path))[0]
        if year.startswith("_"):
            continue
        rows = {}
        with open(path, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                if not r.get("term"):
                    continue
                rows[norm(r["term"])] = r
        years[year] = rows
    return years


def cite(r):
    loc = (r.get("locator") or "").strip()
    return f"[@{r['source_key']}{(' ' + loc) if loc else ''}]" if r.get("source_key") else ""


def main():
    years = load()
    if not years:
        raise SystemExit("no sources/glossaries/*.tsv yet")
    terms = defaultdict(dict)  # norm → {year: row}
    display = {}
    for y, rows in years.items():
        for n, r in rows.items():
            terms[n][y] = r
            display.setdefault(n, r["term"].strip())
    series = sorted([n for n, ys in terms.items() if len(ys) >= 2], key=lambda n: display[n].lower())
    oneoffs = sorted([n for n, ys in terms.items() if len(ys) == 1], key=lambda n: display[n].lower())
    ylist = list(years)

    out = []
    out.append("---\ntitle: How we described ourselves, by year\nstatus: generated\nlast_reviewed: 2026-10-04\nreviewed_by: tools/build_glossary_series.py\n---\n")
    out.append("# How we described ourselves, by year\n")
    out.append(
        "Every O-Week book ends with a glossary—\"Wiess Speak\", \"Conclusions\", \"the Glossary\"—written by that year's "
        "coordinators for that year's freshmen. Read in sequence, the definitions are the college's own record of what each "
        "generation thought mattered, and of drift: the War Pig is \"the Wiess mascot\" in 1994, \"**Former** Wiess mascot\" "
        "from 2006, and \"the giant wooden pig built by the Class of 2012\" from 2014.\n\n"
        f"This page is generated from `sources/glossaries/*.tsv` ({len(ylist)} glossaries: {', '.join(ylist)}) by "
        "`tools/build_glossary_series.py`; edit the TSVs, not this page. Each definition is cited to its book and page. "
        "Terms are grouped when they are plainly the same thing under different spellings, and when a book renamed "
        "the same thing (Room Draw → Housing Jack, Willy Week → Piggy Week, Turnover → Changeover, Commons → "
        "Commons Culture); the later name is shown in italics against its year.\n"
    )
    out.append(f"\n## Terms that recur ({len(series)})\n")
    out.append("\n| Term | Years present |\n|---|---|")
    for n in series:
        ys = [y for y in ylist if y in terms[n]]
        out.append(f"| [{display[n]}](#{slug(display[n])}) | {', '.join(ys)} |")
    out.append("")
    for n in series:
        out.append(f"\n### {display[n]}\n")
        for y in ylist:
            r = terms[n].get(y)
            if not r:
                continue
            d = r["definition"].strip().replace("\n", " ")
            printed = r["term"].strip()
            label = f" (*{printed}*)" if printed.lower() != display[n].lower() else ""
            out.append(f"- **{y}**{label}—{d} {cite(r)}")
    out.append(f"\n## Terms that appear in only one glossary ({len(oneoffs)})\n")
    out.append("\nThe one-year entries are often the most revealing: a joke that lasted a semester, a staff member everyone knew, a rivalry that burned out.\n")
    for y in ylist:
        ones = [n for n in oneoffs if y in terms[n]]
        if not ones:
            continue
        out.append(f"\n### {y}\n")
        for n in ones:
            r = terms[n][y]
            d = r["definition"].strip().replace("\n", " ")
            out.append(f"- **{r['term'].strip()}**—{d} {cite(r)}")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")

    # diff file
    dl = ["# Glossary diffs, year to year\n", "Generated by tools/build_glossary_series.py. Feed for the Changes pages.\n"]
    prev = None
    for y in ylist:
        if prev:
            a, b = set(years[prev]), set(years[y])
            added, dropped = sorted(b - a), sorted(a - b)
            changed = sorted(n for n in a & b if norm_def(years[prev][n]["definition"]) != norm_def(years[y][n]["definition"]))
            dl.append(f"\n## {prev} → {y}\n")
            dl.append(f"- added ({len(added)}): " + ", ".join(display[n] for n in added))
            dl.append(f"- dropped ({len(dropped)}): " + ", ".join(display[n] for n in dropped))
            dl.append(f"- reworded ({len(changed)}): " + ", ".join(display[n] for n in changed))
        prev = y
    with open(DIFF, "w", encoding="utf-8") as fh:
        fh.write("\n".join(dl) + "\n")
    print(f"wrote {OUT} ({len(series)} series terms, {len(oneoffs)} one-offs) and {DIFF}")


def norm_def(d: str) -> str:
    return re.sub(r"\W+", " ", d.lower()).strip()


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


if __name__ == "__main__":
    main()
