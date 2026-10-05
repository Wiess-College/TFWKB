#!/usr/bin/env python3
"""Extract the 2019/2021/2024/2025 glossaries from the reading-order text layer.
Term lists are given by hand (read off the pages); definitions are the text between one
term's start and the next term's start on the same page, minus running heads and footers.
Known column splits are patched in FIXES after the page text was checked by eye."""
import re, sys, csv

CORPUS = "/home/claude/corpus/historian-collection/text-raw"
OUT = "/home/claude/TFWKB/sources/glossaries"

STRIP = [r"^WIESS$", r"^SPEAK$", r"^RICE$", r"^WIESS SPEAK$", r"^RICE SPEAK$",
         r"^Glossary of all things Wiess\.$", r"^Don’t worry, you’ll catch on quick!$",
         r"^Other terms that are good to know\.$", r"^Rice terms that are good to know\.$",
         r"^Acronyms & Abbreviations:$", r"^Campus Essentials:$", r"^Campus Essentials Continued\.\.\.$",
         r"^Unique to Rice:$", r"^Events:$", r".*WIESS COLLEGE O-WEEK 20\d\d \| \d+$"]
TABLE = {"WHAT TO CALL PEOPLE FROM...", "College", "Nickname", "Baker", "Bakerite", "Will Rice", "Will Ricer",
         "Hanszen", "Hanszenite", "Jones", "Jonesian", "Brown", "Brownie", "Lovett", "Lovetteer",
         "Sid Richardson", "Sidizen", "Martel", "Martelian", "McMurtry", "Murt", "Duncan", "Duncaroo"}
TABLE_DEF = ("(table) Baker—Bakerite; Will Rice—Will Ricer; Hanszen—Hanszenite; Jones—Jonesian; Brown—Brownie; "
             "Lovett—Lovetteer; Sid Richardson—Sidizen; Martel—Martelian; McMurtry—Murt; Duncan—Duncaroo.")

TERMS = {
 "2019": {
  14: ["Cabinet", "2FK/3FK", "Commons", "Acabowl", "Acagliders", "Acagrills", "Acaterrace", "Acatramp", "A-Fellows",
       "Associates’ Night", "Bacaterrace", "Basement", "Battlesows", "College Night", "Corner", "Cozy Corner", "Fellows",
       "Freshman One-Acts", "Freshman Service Points", "Goldenrod"],
  15: ["Head Fellows", "Mentors", "NOD", "Wiess Day", "Stacks", "Summit", "OC Lounge", "Team Wiess", "PDR", "TFW",
       "Pumpkin Caroling", "TFFW", "Room Draw", "Saturday Morning Cartoons", "Servery", "Turnover", "Ubangee",
       "Upper Commons", "War Pig", "Sparky’s", "Wilson House (Wiess Magister House)", "Tabletop", "Wiessmen"],
  16: ["45, 90, 180", "Academ", "Academic Quad", "BRC", "Brochstein", "Archi (AR-kee)", "ASB", "Associate", "Autry",
       "Baker 13", "Baker Institute", "Beer Bike", "Beyond the hedges", "Big Three", "Campanile", "ChBE (“Chubby”)",
       "Coffeehouse", "Cohen House", "CTIS", "D1, D2, D3"],
  17: ["Esperanza", "Fondren", "Frog Wall", "FWIS", "GSA", "H&D", "Hedges", "The Hoot", "IM", "Inner Loop",
       "Ironman/Ironwoman", "Jack", "Jones School", "KTRU (KAY-true)", "LPAP", "Matriculation", "Media Center",
       "Mudd Lab", "MOB", "Musi (Myoo-zee)", "OC", "Outer Loop"],
  18: ["PAA", "PCA", "Private Party", "Powderpuff", "Pre-Reqs", "Pub", "Q-Card", "R2 (The Rice Review)", "The Rec",
       "The Bookstore", "REMS", "RHA", "RMC", "Rondelet", "RPC", "RSVP", "Public Party", "RUPD", "Pumpkin Grades",
       "Rustication"],
  19: ["SA", "Wiess", "Willy Week", "Sallyport", "Sammy the Owl", "Screw-Yer-Roommate", "Skyspace", "Willy’s Statue",
       "Y’all", "SMR", "Village", "Whataburger", "Tetra Points", "Thresher", "Valhalla"],
 },
 "2021": {
  18: ["2FK/3FK", "Acabowl", "Acagliders", "Acagrills", "Acaterrace", "A-Fellows", "Associates’ Night", "Bacaterrace",
       "Battlesows", "Cabinet", "Changeover", "Commons", "College Night", "Corner", "Cozy Corner", "Fellows",
       "Fourth Floor Balcony", "Freshman One-Acts", "Freshman Service Points", "Goldenrod", "Head Fellows"],
  19: ["Housing Jack", "Mentors", "Movie Room", "NOD", "OC Lounge", "Stacks", "Summit", "Team Wiess", "TFW", "PDR",
       "TFFW", "Piggy Week", "Ubangee", "Pumpkin Caroling", "Upper Commons", "Servery", "War Pig", "Sparky’s",
       "Tabletop", "Wilson House (Wiess Magister House)", "Wiessmen", "Wiess Day"],
  20: ["45, 90, 180", "Academ", "Brochstein", "Academic Quad", "Archi (AR-kee)", "ASB", "Associate", "Autry",
       "Baker 13", "Baker Institute", "Beer Bike", "Beyond the hedges", "Big Three", "BRC", "Campanile",
       "ChBE (“Chubby”)", "Coffeehouse (“Chaus”)", "Cohen House", "CTIS", "D1, D2, D3"],
  21: ["Esperanza", "Fondren (“Fondy”)", "Frog Wall", "FWIS", "GSA", "H&D", "Hedges", "Ironman/Ironwoman", "Island",
       "Jack", "Jones School", "KTRU (KAY-true)", "LPAP", "Matriculation", "The Hoot", "Media Center", "IM",
       "Inner Loop", "Mudd Lab", "MOB", "Musi (Myoo-zee)", "OC", "Outer Loop"],
  22: ["PAA", "PCA", "R2 (The Rice Review)", "The Rec", "The Bookstore", "Private Party", "Powderpuff", "Pre-Reqs", "Pub",
       "REMS", "RHA", "RMC", "Rondelet", "RPC", "RSVP", "RUPD", "Public Party", "Rustication", "Pumpkin Grades",
       "Q-Card", "SA"],
  23: ["Sallyport", "Y’all", "Sammy the Owl", "Screw-Yer-Roommate", "Skyspace", "SMR", "Tetra Points", "Thresher",
       "Valhalla", "Rice Village", "Whataburger", "Wiess"],
 },
 "2024": {
  25: ["Associates’ Night", "Housing Jack", "Piggy Week", "Pumpkin Caroling", "Servery", "Summit", "Battlesows",
       "Team Wiess", "Cabinet", "Changeover", "Commons Culture", "Corner", "Cozy Corner", "Fellows/Advisors",
       "Freshman Service Points", "Goldenrod", "Head Fellows", "TFW", "TFFW", "Ubangee", "Warpig",
       "Wilson House (Wiess Magister House)", "Wiessmen"],
  26: ["ASB", "RSVP", "CDOD", "CTIS", "FWIS", "GSA", "H&D", "KTRU (KAY-true)", "LPAP", "OC", "RUPD", "SA", "The MOB",
       "Beer Bike", "BRC", "Brochstein", "Coffeehouse (“Chaus”)", "Fondren (“Fondy”)", "Inner Loop", "REMS", "RMC",
       "RPC", "Jones Business School", "Mudd Lab", "Outer Loop"],
  27: ["Pub", "Beyond the Hedges", "Associate", "Sallyport", "Campanile", "Skyspace", "D1, D2, D3", "The Hoot",
       "The Island", "The Rec", "Rice Village", "Baker 13", "Jack", "Powderpuff", "Pumpkin Grades", "Rustication",
       "Sammy the Owl", "Esperanza", "Intramural (IM) Sports", "Matriculation", "Rondelet", "Screw-Yer-Roommate",
       "Tetra", "Thresher", "Wiess"],
 },
 "2025": {
  26: ["Associates’ Night", "Housing Jack", "Piggy Week", "Pumpkin Caroling", "Servery", "Summit", "Battlesows",
       "Team Wiess", "Cabinet", "Changeover", "Commons Culture", "Corner", "Cozy Corner", "Fellows/Advisors",
       "Freshman Service Points", "Goldenrod", "Head Fellows", "TFW", "TFFW", "Ubangee", "Warpig",
       "Wilson House (Wiess Magister House)", "Wiessmen"],
  27: ["ASB", "RUPD", "CDOD", "SA", "CTIS", "FWIS", "The MOB", "GSA", "H&D", "Beer Bike", "KTRU (KAY-true)", "LPAP",
       "OC", "BRC", "Brochstein", "Coffeehouse (“Chaus”)", "Fondren (“Fondy”)", "Inner Loop", "Jones Business School",
       "REMS", "RMC", "RPC", "Mudd Lab", "Outer Loop"],
  28: ["Pub", "Sallyport", "Skyspace", "The Hoot", "The Island", "The Rec", "Rice Village", "Campanile", "D1, D2, D3",
       "Jack", "Powderpuff", "Pumpkin Grades", "Rustication", "Sammy the Owl", "Esperanza", "Intramural (IM) Sports",
       "Matriculation", "Screw-Yer-Roommate", "Tetra", "Wiess", "Associate", "Beyond the Hedges", "Thresher"],
 },
}

# column splits and extraction artefacts, each checked against the layout text of the page
FIXES = {
 "2019": {
  "Summit": "Weekend retreat to a body of water (pool/beach/lake/etc.) during the fall semester to discuss Wiess issues and bond with other Wiessmen.",
 },
 "2021": {
  "Wiess": "Your home and family.",
  "Academ": "Humanities or Social Sciences major. A very archaic term.",
  "BRC": "BioScience Research Collaborative, where Rice meets the Texas Medical Center for research. Also where Bioengineers spend most of their time for class starting junior year.",
  "Inner Loop": "The one-way road that loops around the center of campus.",
  "Hedges": "Extensive botanical growth that surrounds campus and the Academic Quad.",
  "Outer Loop": "The three-mile long path that encircles [the entry breaks off here in the book]",
  "Y’all": "Southern slang short for “you all.” Soon enough, y’all will be saying this too. (It’s efficient!)",
  "Sammy the Owl": "The Rice mascot.",
  "Skyspace": "The pyramidal installation located next to the Shepherd School of Music. A reat place to watch the sunrise and sunset.",
  "RPC": "Rice Program Council. The organization in charge of university-wide events such as Beer Bike, Screw-Yer-Roommate, Esperanza, and study breaks during finals.",
  "Baker Institute": "The James A. Baker III Institute for Public Policy. Holds many interesting talks and events that are typically open to undergraduates. Not to be confused with Baker College.",
 },
 "2024": {
  "ASB": "Alternative Spring Break; a service trip over spring break based on a social issue.",
  "RPC": "Rice Program Council. The organization in charge of university-wide events such as Beer Bike, Screw-Yer-Roommate, Esperanza, and study breaks during finals.",
  "Outer Loop": "The 5 kilometer loop that surrounds all of Rice University. Students often run along the path surrounding the loop.",
 },
 "2025": {
  "ASB": "Alternative Spring Break; a service trip over spring break based on a social issue.",
  "RPC": "Rice Program Council. The organization in charge of university-wide events such as Beer Bike, Screw-Yer-Roommate, Esperanza, and study breaks during finals.",
  "Outer Loop": "The 5 kilometer loop that surrounds all of Rice University. Students often run along the path surrounding the loop.",
 },
}
TABLE_PAGE = {"2019": 19, "2021": 23}


def clean_lines(text):
    out = []
    for line in text.splitlines():
        s = line.strip().replace("\t", " ")
        s = re.sub(r"\s+", " ", s).strip()
        if not s:
            out.append("")
            continue
        if any(re.match(p, s) for p in STRIP):
            continue
        out.append(s)
    return out


def extract(year):
    pages = open(f"{CORPUS}/{year}-oweek-book.txt", encoding="utf-8").read().split("\f")
    rows = []
    for pg, terms in TERMS[year].items():
        lines = clean_lines(pages[pg - 1])
        if year in TABLE_PAGE and pg == TABLE_PAGE[year]:
            lines = [l for l in lines if l not in TABLE]
        # locate each term at a line start; longest term first so "Wiess Day" beats "Wiess"
        starts = {}
        for t in sorted(terms, key=len, reverse=True):
            hits = []
            for i, l in enumerate(lines):
                dot = year in ("2024", "2025")
                if ((not dot and l.startswith(t + " ")) or (dot and (l.startswith(t + ". ") or l.startswith(t + " ")))) and i not in starts.values():
                    # reject a shorter term that is a prefix of a longer one already placed here
                    hits.append(i)
            if not hits:
                print(f"  {year} p.{pg}: term not found: {t}", file=sys.stderr)
                continue
            if len(hits) > 1:
                print(f"  {year} p.{pg}: {t} at lines {hits}; taking first", file=sys.stderr)
            starts[t] = hits[-1] if t == "Wiessmen" else hits[0]
        order = sorted(starts.items(), key=lambda kv: kv[1])
        bounds = [i for _, i in order] + [len(lines)]
        for k, (t, i) in enumerate(order):
            chunk = lines[i:bounds[k + 1]]
            first = chunk[0][len(t):].lstrip()
            if first.startswith(". "):
                first = first[2:]
            elif first.startswith("."):
                first = first[1:].lstrip()
            body = " ".join([first] + [c for c in chunk[1:] if c]).strip()
            body = body.replace("­", "")
            body = re.sub(r"\s+", " ", body)
            body = body.replace("nonmusic", "non-music")
            body = FIXES.get(year, {}).get(t, body)
            rows.append({"term": t, "definition": body, "locator": f"p.{pg}", "_pos": (pg, i)})
    rows.sort(key=lambda r: r["_pos"])
    if year in TABLE_PAGE:
        rows.append({"term": "What to call people from…", "definition": TABLE_DEF, "locator": f"p.{TABLE_PAGE[year]}"})
    return rows


for year in TERMS:
    rows = extract(year)
    with open(f"{OUT}/{year}.tsv", "w", encoding="utf-8") as fh:
        fh.write("term\tdefinition\tsource_key\tlocator\n")
        for r in rows:
            fh.write(f"{r['term']}\t{r['definition']}\toweek-{year}\t{r['locator']}\n")
    print(year, len(rows))
