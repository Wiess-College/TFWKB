#!/usr/bin/env python3
"""Run every raw glossary extraction again, writing out/<year>.tsv and out/<year>.review.txt.

Each O-Week book needs extract_layout.py run with its own pages and options. This script holds every
book's command line, so the raw extractions that finalize.py corrects can be rebuilt exactly when a
rule changes, or a book added when a missing one turns up.

For each book it runs extract_layout.py on the book's text file in OWEEK_TEXT_ROOT and writes two files
in out/ next to this script (the folder must already exist):

    out/<year>.tsv           the raw glossary, written by extract_layout.py
    out/<year>.review.txt    what extract_layout.py printed: each entry with its page, for checking by eye

<year> is the last label in each EXTRACTION_JOBS row, such as "2011" or "2016-owlmanac". Run it with no
arguments for every book, or with labels for only those books:

    python3 run_all.py
    python3 run_all.py 2011 2014

extract_layout.py's messages are passed on to standard error. OWEEK_TEXT_ROOT is
teamwiess.com/oweek-books/text/ in the corpus folder, which tools/paths.py finds (see README.md). A label that matches no row runs
nothing and prints nothing.

The exit status of each extraction is not checked. If one fails, its traceback appears on standard error,
its out/<year>.tsv is left as it was (possibly from an earlier run), and its review file holds whatever it
printed before failing; the remaining books still run. If out/ does not exist, the first book's review
file cannot be written and the run stops there with a traceback. Review files are written in the locale's
encoding.
"""

import os
import subprocess
import sys
from typing import NamedTuple

GLOSSARY_EXTRACTION_ROOT = os.path.dirname(os.path.abspath(__file__))

# This repository's tools/ folder, for paths.py.
sys.path.insert(0, os.path.dirname(GLOSSARY_EXTRACTION_ROOT))
from paths import corpus_folder  # noqa: E402  (needs the sys.path line above)

# The corpus folder of O-Week book text extracts, with its trailing slash.
OWEEK_TEXT_ROOT = f"{corpus_folder()}/teamwiess.com/oweek-books/text/"

# Header and footer lines of the 2015-2017 books, given to extract_layout.py's --furniture.
FURNITURE_2015_TO_2017 = [
    "EXTRA RESOURCES",
    "WIESS",
    r"WIESS COLLEGE O-WEEK \d{4} \| \d+",
    r"Glossary of all things Wiess\.",
    r"Don’t worry: you’ll catch up quick\.",
    r"Other words that are good to know\.",
]

# One row per book: text file, first and last glossary page, source key, output label, other options.
EXTRACTION_JOBS = [
    ("2003-oweek-80-88-conclusions.txt", "3", "7", "oweek-2003", "2003", ["--smart"]),
    ("2006-oweek-book.txt", "83", "87", "oweek-2006", "2006", []),
    ("2007-oweek-book.txt", "83", "87", "oweek-2007", "2007", []),
    (
        "2008-oweek-Part_7.txt", "3", "7", "oweek-2008", "2008",
        ["--loc-prefix", "part 7 ", "--bounds", "4:39/73,7:33/75", "--smart-pages", "7"],
    ),
    ("2010-oweek-book.txt", "90", "94", "oweek-2010", "2010", ["--mode", "indent"]),
    (
        "2011-oweek-book.txt", "92", "96", "oweek-2011", "2011",
        ["--mode", "indent", "--decode", GLOSSARY_EXTRACTION_ROOT + "/decode2011.py", "--bounds", "94:36/82,96:35/77"],
    ),
    (
        "2014-oweek-book.txt", "102", "106", "oweek-2014", "2014",
        [
            "--mode", "para", "--decode", GLOSSARY_EXTRACTION_ROOT + "/decode2014.py",
            "--bounds", "102:44/90,103:62/107,104:40/78,105:56/98,106:42/82",
        ],
    ),
    (
        "2015-oweek-book.txt", "118", "123", "oweek-2015", "2015",
        ["--mode", "inline", "--ncols", "2", "--furniture", *FURNITURE_2015_TO_2017],
    ),
    (
        "2016-oweek-book.txt", "13", "18", "oweek-2016", "2016",
        ["--mode", "inline", "--ncols", "2", "--bounds", "18:56", "--furniture", *FURNITURE_2015_TO_2017],
    ),
    (
        "2017-oweek-book.txt", "14", "19", "oweek-2017", "2017",
        ["--mode", "inline", "--ncols", "2", "--bounds", "19:56", "--furniture", *FURNITURE_2015_TO_2017],
    ),
    (
        "2016-owlmanac.txt", "55", "57", "owlmanac-2016", "2016-owlmanac",
        ["--mode", "colon", "--furniture", r"Conclusion", r"Rice speak"],
    ),
]


class ExtractionJob(NamedTuple):
    """One book's extract_layout.py run.

    Field order matches the rows of EXTRACTION_JOBS, so ExtractionJob(*row) converts one.
    """

    text_subpath: str  # relative to OWEEK_TEXT_ROOT
    first_page: str  # first glossary page, counting from 1 as in the PDF
    last_page: str  # last glossary page
    source_key: str  # the bibliography key written in every row, e.g. "oweek-2011"
    output_label: str  # names out/<label>.tsv and out/<label>.review.txt; picks the job on the command line
    extra_arguments: list[str]  # further extract_layout.py options


def main(arguments: list[str]) -> None:
    """Run the extraction for every book, or only for the books whose labels are given."""
    for row in EXTRACTION_JOBS:
        job = ExtractionJob(*row)
        if arguments and job.output_label not in arguments:
            continue
        run_extraction(job)


def run_extraction(job: ExtractionJob) -> None:
    """Run extract_layout.py for one book, pass on its messages, and save what it printed as the review file."""
    command = [
        sys.executable,
        GLOSSARY_EXTRACTION_ROOT + "/extract_layout.py",
        OWEEK_TEXT_ROOT + job.text_subpath,
        job.first_page,
        job.last_page,
        job.source_key,
        f"{GLOSSARY_EXTRACTION_ROOT}/out/{job.output_label}.tsv",
        *job.extra_arguments,
    ]
    extraction = subprocess.run(command, capture_output=True, text=True, check=False)
    sys.stderr.write(extraction.stderr)
    with open(f"{GLOSSARY_EXTRACTION_ROOT}/out/{job.output_label}.review.txt", "w") as review:
        review.write(extraction.stdout)


if __name__ == "__main__":
    main(sys.argv[1:])
