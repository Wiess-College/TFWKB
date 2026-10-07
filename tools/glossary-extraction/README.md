# Glossary extraction pipeline

The scripts that produced `sources/glossaries/<year>.tsv` from the O-Week book text layers
(October 2026). They are kept so the TSVs can be re-derived or extended when a missing book
turns up. `run_all.py` drives the others; `extract_layout.py` splits two-column layouts;
`decode2011.py` and `decode2014.py` undo the glyph-order ciphers of those two books;
`finalize.py` normalises terms and writes the TSVs. They find the corpus with
`tools/paths.py`: set it once with `./setup.sh` (which writes `tfwkb.config.yml`), or for one run with
`TFWKB_CORPUS=/path/to/wiess-archive`. The TSVs are written straight into `sources/glossaries/`, so
check `git diff sources/glossaries` afterwards. Run them in this order (`run_all.py` needs an `out/`
folder here, which git ignores):

```
mkdir -p tools/glossary-extraction/out
python3 tools/glossary-extraction/run_all.py
python3 tools/glossary-extraction/finalize.py
python3 tools/glossary-extraction/extract_2019_2025.py
```

On an unchanged corpus this rewrites the committed TSVs byte for byte (checked October 2026).
That includes two hand edits now made in code: closed-up em dashes in the 2003–2011 books
(`CLOSED_UP_DASH_GLOSSARIES` in `finalize.py`) and current students' names withheld in 2024 and 2025
(`STUDENT_NAMES_PATTERN_BY_YEAR_AND_TERM` in `extract_2019_2025.py`).

For a new book whose text comes out garbled, don't write another decoder: run
`tools/fix_pdf_fonts.py repair` on the PDF and extract text from the repaired copy. It identifies each
glyph by its outline and writes correct `/ToUnicode` maps, and on the 2011 and 2014 books it reproduces
these glossaries without `--decode` (October 2026). The two decoders are kept because the corpus text
files the TSVs were made from still need them.

`extract_2019_2025.py` (October 2026) is separate: it reads the reading-order text layer
(`historian-collection/text-raw/`) of the four books from the maintainer's collection, with the
term list for each page given by hand and the few column splits patched in `FIXES`. The 2021
"Outer Loop" entry breaks off mid-sentence in the book itself and is marked so. The 2024 and 2025
books moved the college-nickname table out of the glossary (to "The Lesser Colleges (and Wiess!)",
p.4), so it is not in those TSVs.
