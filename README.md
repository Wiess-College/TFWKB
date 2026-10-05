# Team Familypedia

The sourced history of Wiess College, Rice University — traditions, places, people, governance and how they changed — with every claim cited to a permalink that resolves without us.

**Site:** https://wiess-college.github.io/TFWKB/ · **Commons (wiki):** the easy place to say something · **Record (this repo):** the careful place to state it.

## What is here

```
docs/           the Record: Markdown pages, one template, every claim cited
  traditions/   the War Pig, Team Wiess, Ubangee, NOD, Beer Bike … and the retired ones
  places/ people/ governance/ changes/ decisions/ web/ sources/ contributing/
sources/
  bibliography/*.yaml      every source the pages cite (key, permalink, corpus path, evidence class, notes)
  glossaries/<year>.tsv    1,288 definitions from 12 O-Week glossaries, 1994–2017
  manifests/               what the Historian's 2 GB corpus contains and how to rebuild it from the Wayback Machine
  governance-versions.md   generated from the governance repo's tags
hooks/citations.py         turns [@key p.N] into links at build time; unknown keys fail the build
tools/                     stdlib-only helpers: cite.py, check_links.py, build_glossary_series.py, diff_glossary.py,
                           import_governance_changes.py, fix_pdf_text.py, pdfpage.py, html2text.py
```

## Working on it

```
pip install -r requirements.txt
mkdocs serve            # http://127.0.0.1:8000
mkdocs build --strict   # what CI runs; an unknown citation key fails here
python3 tools/check_links.py --limit 20   # do the permalinks still resolve (network)
```

Read `docs/contributing/citing.md` and `docs/contributing/page-template.md` before writing. Conflicts between sources go in the page, under **Variants & disputes**, not in a reviewer's head.

## Licence

Text CC BY-SA 4.0 (`LICENSE`); code MIT (`LICENSE-CODE`). Third-party material is quoted briefly and linked, not re-hosted: `docs/contributing/rights.md`.
