## Installing locally

macOS or Linux, with git and Python 3.12 or newer. Once per machine:

```
./setup.sh
```

It makes a virtual environment in `.venv/`, installs `requirements.txt` into it, asks where your checkout of
the governance repo is (if you have one) and writes it to `tfwkb.config.yml`, lists any optional tools that
are missing (it doesn't install them), and builds the site once. Run it again whenever `requirements.txt`
changes.

Then, in each new terminal:

```
source .venv/bin/activate
mkdocs serve            # http://127.0.0.1:8000
mkdocs build --strict   # what CI runs; an unknown citation key fails here
python3 tools/check_links.py --limit 20   # do the permalinks still resolve (network)
```

`tfwkb.config.yml` is yours and isn't committed; `tfwkb.config.example.yml` shows the format. For one run,
`TFWKB_GOVERNANCE_REPO=/path/to/governance` overrides it.

Found an O-Week book whose glossary isn't in `sources/glossaries/` yet? Give its PDF to `tools/add_glossary.py`
with the pages the glossary is on. It writes a draft table, marks the entries that look misread, and shows
what changed since the previous book; you fix the table by hand. `python3 tools/add_glossary.py --help`.
