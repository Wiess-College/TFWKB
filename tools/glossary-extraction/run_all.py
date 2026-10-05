#!/usr/bin/env python3
"""Run every raw extraction into out/<year>.tsv (reproducible)."""
import subprocess, sys, os
here = os.path.dirname(os.path.abspath(__file__))
T = "/home/claude/corpus/teamwiess.com/oweek-books/text/"
FURN = ["EXTRA RESOURCES", "WIESS", r"WIESS COLLEGE O-WEEK \d{4} \| \d+", r"Glossary of all things Wiess\.",
        r"Don’t worry: you’ll catch up quick\.", r"Other words that are good to know\."]
jobs = [
    ["2003-oweek-80-88-conclusions.txt", "3", "7", "oweek-2003", "2003", "--smart"],
    ["2006-oweek-book.txt", "83", "87", "oweek-2006", "2006"],
    ["2007-oweek-book.txt", "83", "87", "oweek-2007", "2007"],
    ["2008-oweek-Part_7.txt", "3", "7", "oweek-2008", "2008", "--loc-prefix", "part 7 ",
     "--bounds", "4:39/73,7:33/75", "--smart-pages", "7"],
    ["2010-oweek-book.txt", "90", "94", "oweek-2010", "2010", "--mode", "indent"],
    ["2011-oweek-book.txt", "92", "96", "oweek-2011", "2011", "--mode", "indent",
     "--decode", here + "/decode2011.py", "--bounds", "94:36/82,96:35/77"],
    ["2014-oweek-book.txt", "102", "106", "oweek-2014", "2014", "--mode", "para",
     "--decode", here + "/decode2014.py", "--bounds", "102:44/90,103:62/107,104:40/78,105:56/98,106:42/82"],
    ["2015-oweek-book.txt", "118", "123", "oweek-2015", "2015", "--mode", "inline", "--ncols", "2", "--furniture", *FURN],
    ["2016-oweek-book.txt", "13", "18", "oweek-2016", "2016", "--mode", "inline", "--ncols", "2", "--bounds", "18:56", "--furniture", *FURN],
    ["2017-oweek-book.txt", "14", "19", "oweek-2017", "2017", "--mode", "inline", "--ncols", "2", "--bounds", "19:56", "--furniture", *FURN],
    ["2016-owlmanac.txt", "55", "57", "owlmanac-2016", "2016-owlmanac", "--mode", "colon", "--furniture", r"Conclusion", r"Rice speak"],
]
only = sys.argv[1:]
for j in jobs:
    year = j[4]
    if only and year not in only:
        continue
    cmd = [sys.executable, here + "/extract_layout.py", T + j[0], j[1], j[2], j[3], f"{here}/out/{year}.tsv"] + j[5:]
    r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    open(f"{here}/out/{year}.review.txt", "w").write(r.stdout)
