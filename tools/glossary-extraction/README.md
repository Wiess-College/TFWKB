# Glossary extraction pipeline

The scripts that produced `sources/glossaries/<year>.tsv` from the O-Week book text layers
(October 2026). They are kept so the TSVs can be re-derived or extended when a missing book
turns up. `run_all.py` drives the others; `extract_layout.py` splits two-column layouts;
`decode2011.py` and `decode2014.py` undo the glyph-order ciphers of those two books;
`finalize.py` normalises terms and writes the TSVs. Paths inside point at the corpus
(`/home/claude/corpus/...` in the build environment; `~/projects/wiess-archive/` on the
Historian's machine)—adjust before running.

`extract_2019_2025.py` (October 2026) is separate: it reads the reading-order text layer
(`historian-collection/text-raw/`) of the four books from the Historian's collection, with the
term list for each page given by hand and the few column splits patched in `FIXES`. The 2021
"Outer Loop" entry breaks off mid-sentence in the book itself and is marked so. The 2024 and 2025
books moved the college-nickname table out of the glossary (to "The Lesser Colleges (and Wiess!)",
p.4), so it is not in those TSVs.
