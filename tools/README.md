# tools/

Maintainer scripts. This page is the map. Each script's docstring is the full reference: usage, inputs, outputs, failures.

## Setup

- `./setup.sh` makes `.venv/`, installs `requirements.txt`, writes `tfwkb.config.yml`, lists missing optional tools.
- Python 3.12.
- `requirements.txt`: site build only (MkDocs, PyYAML). Every deploy installs it, so keep it small.
- `requirements-dev.txt`: linters, plus PyMuPDF and fontTools (PDF fonts) and Pillow (photos).
- External programs:

  | Program | Needed by |
  |---|---|
  | `pdftotext` (poppler) | `add_glossary.py` |
  | `gh` (GitHub CLI) | `file_issue_drafts.sh`, `file_open_questions.sh` |
  | `git` | `import_governance_changes.py` |

- Source documents are not in the repo. You run a tool on a document you have; you commit only its output (see `sources/README.md`).
- Working copy: a folder outside the repo for source files. Set `working_copy:` in `tfwkb.config.yml` (or `TFWKB_WORKING_COPY`); `fetch_working_copy.py` fills it from archive.org.

## Scripts

| Script | Does | Run when |
|---|---|---|
| `add_glossary.py` | Drafts `sources/glossaries/oweek-<year>.tsv` from an O-Week book PDF | A book with no table turns up |
| `apply_photos.py` | Copies `sources/photo-placements.yaml` onto Record pages, the Photographs page and the manifest | After any edit to that file |
| `build_glossary_series.py` | Generates the glossary-by-year page and year-to-year diff | After a glossary TSV changes (deploys run it too) |
| `check_links.py` | Checks that cited web addresses still answer | Monthly in CI; by hand before a big review |
| `cite.py` | Corpus path → citation; `--url` citation → link | Writing or checking a citation |
| `convert_html_to_text.py` | Prints the readable text of archived HTML pages | Reading or quoting corpus pages |
| `diff_glossary.py` | Compares two years' glossaries | Ad hoc |
| `file_issue_drafts.sh` | Files `issues/drafts/*.md` as GitHub issues | After adding drafts (`-n` first) |
| `file_open_questions.sh` | Files `keep=y` rows of `issues/open-questions.tsv` as issues | After vetting rows (`-n` first) |
| `fetch_working_copy.py` | Downloads every archive.org file in `sources/manifests/` into your working copy; resumable | Setting up a working copy (`--dry-run` first; takes hours) |
| `find_pdf_page.py` | Finds which PDF page a phrase is on, in a corpus text extract | Citing an O-Week book page |
| `fix_pdf_fonts.py` | Repairs a PDF whose fonts extract as garbage (`report`, `repair`) | Text from a PDF is garbled |
| `fix_pdf_text.py` | Decodes "+29" shifted-font runs in existing text extracts | Rarely by hand; `find_pdf_page.py` uses it |
| `import_governance_changes.py` | Regenerates `sources/governance-versions.md` from governance repo tags | A new version is tagged (deploys try it; skipped without a checkout) |
| `make_web_photos.py` | Makes web copies and thumbnails of original photos; adds manifest rows | Originals are added |

Modules (imported, never run):

| Module | Holds |
|---|---|
| `repository_folders.py` | Repo root; folders outside it: governance checkout, working copy (argument → environment variable → `tfwkb.config.yml`) |
| `glossary_layouts.py` | Column splitting and entry parsers for `add_glossary.py` |
| `../tools/hooks/citations.py` | MkDocs hook: citations, timelines, bibliography at build time. `cite.py` imports it. |

## Common jobs

**Add photos**

1. `python3 tools/make_web_photos.py <originals-folder>`
2. Add one block per photo to `sources/photo-placements.yaml` (its header lists the fields).
3. Put `<!-- GALLERY:<gallery> -->` on the Record page where the photos go, if it isn't there yet.
4. `python3 tools/apply_photos.py`
5. `mkdocs serve` to check.

**Add a newly found O-Week glossary**

1. `python3 tools/add_glossary.py <book.pdf> --pages A-B --year YYYY`
2. Check the flagged entries against the PDF; fix the TSV by hand.
3. Add the bibliography entry it prints, if it prints one.
4. `python3 tools/build_glossary_series.py`

**Text from a PDF is garbled**

1. `python3 tools/fix_pdf_fonts.py report <book.pdf>` lists the broken fonts.
2. `python3 tools/fix_pdf_fonts.py repair <book.pdf> <fixed.pdf>`
3. `pdftotext -layout <fixed.pdf> <book.txt>`

- A font reported "unchecked": give it the typeface with `--ref <font file>`.
- `add_glossary.py` does all this itself.

**Get your own working copy**

1. Set `working_copy:` in `tfwkb.config.yml` (see `tfwkb.config.example.yml`).
2. `python3 tools/fetch_working_copy.py --dry-run` shows what it will fetch and roughly how long.
3. `python3 tools/fetch_working_copy.py`. Stop with Ctrl-C any time; run again to continue. If archive.org throttles it, it stops; wait an hour and rerun.

**Cite the corpus**

- Archived web page: `python3 tools/cite.py <corpus path>`
- O-Week book page: `python3 tools/find_pdf_page.py <text extract> "phrase"`, then cite `[@oweek-YYYY p.N]`.
- Where a citation links: `python3 tools/cite.py --url "[@...]"`

**File GitHub issues** (details: `issues/README.md`)

- Drafts: `tools/file_issue_drafts.sh -n`, then without `-n`.
- Open questions: set `keep=y` in `issues/open-questions.tsv`; `tools/file_open_questions.sh -n`, then without `-n`.

**New governance version tagged**

- `python3 tools/import_governance_changes.py [governance checkout]`

## Why it's built this way (October 2026)

- **Tools run anywhere, on whatever document you have:** Nothing assumes one machine or a shared corpus. Commit the output, not the source document.
- **Editor data is YAML under `sources/`:** Fields are labelled, and there's no Python syntax to break. Scripts check it and stop with a message naming the entry.
- **Generated files are never edited by hand:** This covers the Photographs page, Record-page galleries, the glossary series page, `governance-versions.md` and the manifest's caption columns. Edit the source and rerun the tool.
- **Two requirements files:** `requirements.txt` holds only what the site build needs, since every deploy installs it. Everything else goes in `requirements-dev.txt`.
- **No machine-specific paths in code:** Folders outside the repo come from `repository_folders.py`. CI fails on `/Users/`, `/home/` or `/mnt/` in `tools/` and `hooks/`.
- **Names:** scripts are verb_object (what they do); modules are nouns (what they hold). `cite.py` stays short because editors type it most. See `STYLE.md` §1.
- **Garbled PDFs are fixed in the PDF, not in the text:**
  - `fix_pdf_fonts.py` identifies each glyph by its outline, matching installed fonts and readable fonts in the same PDF.
  - It replaced per-book cipher tables built by hand. One of those had `!` and `)` swapped.
  - `fix_pdf_text.py` remains only for searching old text extracts.
- **`convert_html_to_text.py` uses only the standard library:** It's crude, but needs nothing installed; its docstring lists the gaps. The upgrade is PyPI `html2text`; delete ours if you adopt it, because the import names clash.
- **`hooks/citations.py` stays in `hooks/`:** MkDocs runs it on every build; `tools/` is for scripts run by hand.

## Changing a tool

- Follow `STYLE.md`. `apply_photos.py` is the reference example.
- Lint:
  1. `pip install -r requirements-dev.txt`
  2. `ruff check`
  3. `pylint tools hooks`

  CI runs the same on pull requests that touch `tools/` or `hooks/`.
- Scripts not yet rewritten are listed twice in `pyproject.toml`. To convert one, follow `STYLE.md` §5: compare outputs before and after, then remove it from both lists.
- Adding a tool: add a row to the tables above.
