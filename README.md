# Team Family Knowledgebase (Wiess)

The sourced history of Wiess College—traditions, places, people, governance and how they changed—with every claim cited to a permalink that resolves without us.

**Site:** https://wiess-college.github.io/TFWKB/. 
**Commons (wiki):** the easy place to say something. 
**Record (this repo):** the cited records.

## What is here

```
docs/                     markdown pages following a fixed template with every claim cited  
  traditions/             current and retired traditions  
  places/  
  people/  
  governance/  
  changes/  
  decisions/  
  web/  
  sources/  
  contributing/
sources/
  bibliography/*.yaml      every source the pages cite (key, permalink, corpus path, evidence class, notes)  
  glossaries/<year>.tsv    1,288 definitions from 12 O-Week glossaries, 1994–2017  
  manifests/               what the maintainer's 2 GB corpus contains and how to rebuild it from the Wayback Machine  
  governance-versions.md   generated from the governance repo's tags  
hooks/citations.py         turns [@key p.N] into links at build time; unknown keys fail the build  
tools/                     helpers: cite.py, check_links.py, build_glossary_series.py, diff_glossary.py,  
                           import_governance_changes.py, fix_pdf_text.py, pdfpage.py, html2text.py  
tools/paths.py             finds the corpus and governance folders on this machine (from tfwkb.config.yml)  
setup.sh                   sets up a new machine: .venv/, tfwkb.config.yml, a first build  
tools/STYLE.md             how to write those helpers (names, docstrings, linting); pyproject.toml holds the lint rules  
```

## Installing locally

macOS or Linux, with git and Python 3.12 or newer. Once per machine:

```
./setup.sh
```

It makes a virtual environment in `.venv/`, installs `requirements.txt` into it, asks where your research
corpus (`wiess-archive`) and governance checkout are and writes them to `tfwkb.config.yml`, lists any optional
tools that are missing (it doesn't install them), and builds the site once. Run it again whenever
`requirements.txt` changes. The site itself builds without the corpus; only some tools in `tools/` read it.

Then, in each new terminal:

```
source .venv/bin/activate
mkdocs serve            # http://127.0.0.1:8000
mkdocs build --strict   # what CI runs; an unknown citation key fails here
python3 tools/check_links.py --limit 20   # do the permalinks still resolve (network)
```

`tfwkb.config.yml` is yours and isn't committed; `tfwkb.config.example.yml` shows the format. For one run,
`TFWKB_CORPUS=/path/to/wiess-archive` or `TFWKB_GOVERNANCE_REPO=/path/to/governance` overrides it.

Read `docs/contributing/citing.md` and `docs/contributing/page-template.md` before writing. Conflicts between sources go in the page, under **Variants & disputes**.

## Licence

Text CC BY-SA 4.0 (`LICENSE`); code MIT (`LICENSE-CODE`). Third-party material is quoted briefly and linked, not re-hosted: `docs/contributing/rights.md`.