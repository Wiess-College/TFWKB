# Glossary extraction pipeline

The scripts that produced `sources/glossaries/<year>.tsv` from the O-Week book text layers
(October 2026). They are kept so the TSVs can be re-derived or extended when a missing book
turns up. `run_all.py` drives the others; `extract_layout.py` splits two-column layouts;
`decode2011.py` and `decode2014.py` undo the glyph-order ciphers of those two books;
`finalize.py` normalises terms and writes the TSVs. Paths inside point at the corpus
(`/home/claude/corpus/...` in the build environment; `~/projects/wiess-archive/` on the
Historian's machine) — adjust before running.
