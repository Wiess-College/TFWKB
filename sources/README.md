# sources/

What the site is built from, and records about the evidence. **Not the evidence itself:**

## How sources get here

1. A contributor gets hold of a source: a Wayback capture, an O-Week book PDF, a photo, a Thresher page.
2. They run the matching tool from `tools/` on their own machine (see `tools/README.md`).
3. They commit only the result: a bibliography entry, a TSV, a YAML block, a manifest row.

- The source document stays on the contributor's machine (their "working copy"). Nothing here depends on it.
- To get your own copy of everything the manifests list on archive.org: `python3 tools/fetch_working_copy.py --dry-run`, then without `--dry-run`. It takes hours and resumes if stopped.
- Every citation must resolve to a public permanent copy (Wayback, Portal, Fondren, Woodson), not to anyone's working copy.
- No source has a public copy? See "Sources with no public copy" in `docs/contributing/citing.md`.

## Why the evidence isn't in the repo

- **Size:** the 2026 working copy alone was about 2 GB, in 6,400 files.
- **Rights:** most of it is third-party (Thresher, Campanile, student-run websites).
- **It's already archived:** the Wayback Machine, the Portal to Texas History and the Woodson Research Center keep it permanently.

## What's here

| Path | What it is | Edited by |
|---|---|---|
| `bibliography/*.yaml` | Every source the pages cite: key, permanent URL, evidence class | Hand |
| `manifests/<site>/` | Provenance: each file a contributor examined, with the URL it came from | Hand, when adding a source |
| `glossaries/<key>.tsv` | Glossaries as data, one file per source, named by its bibliography key (`oweek-2006`, `owlmanac-2016`, `handbook-1994`) | `add_glossary.py`, then hand |
| `photo-placements.yaml` | Each photo's page, caption, credit and date | Hand, then `apply_photos.py` |
| `portal-issue-dates.tsv` | Thresher issue dates for `[@portal ...]` citations | Hand |
| `wanted-core-team.tsv` | Records known to exist and still needed | Hand |
| `governance-versions.md` | Tags of the governance repository | `import_governance_changes.py` (generated) |
| `commons-snapshots/` | Nightly copy of the GitHub wiki | GitHub Action (generated) |

- Generated files: don't edit by hand; rerun the tool.
- `held_by:` in a bibliography entry says who holds a source with no public `url`. The site shows it; the build fails on an entry with neither.
- `local:` in a bibliography entry, and the `local` column in a manifest, name where a file sat in one contributor's working copy. They're provenance notes, not paths anyone else will have; the site doesn't show them.
- For readers, the site explains the same ground at `docs/sources/`.
