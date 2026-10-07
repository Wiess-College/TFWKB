# Python style for tools/ and hooks/

How to write the Python helpers in this repo. Read this before you add or rewrite a script. The page style guide,
`STYLE.md` at the repo root, covers writing pages; this file covers the code that builds them.

The people who maintain these scripts are mostly editors and historians who know some Python. They open a script
months after it was written, usually to change one thing. Write for them: they should be able to see what a
script does, why each step is there, and where to make their change, without running it.

[`apply_photos.py`](apply_photos.py) is the reference example. When this guide and that script disagree, fix one
of them.

---

## 1. Names

**Whole words that say what the value is.** No single letters and no abbreviations, in loops and comprehensions
too. Read the line aloud: `for placement in placements` says something; `for e in P` does not.

| Not this | This |
|---|---|
| `e`, `r`, `t`, `fh` | `placement`, `row`, `page_text`, `manifest` |
| `idx`, `rel`, `cand`, `pat`, `desc` | `column_position`, `image_link`, `thumbnail_path`, `gallery_pattern`, `lightbox_description` |
| `P`, `PAGES` | `PHOTO_PLACEMENTS`, `GALLERY_PAGES` |
| `CONS`, `UNREC` | `WOODSON_VIA_RICE_HISTORY_CORNER_CREDIT`, `SOURCE_NOT_RECORDED_CREDIT` |

Long names are fine. `placements_by_gallery` and `record_page_link` are the right length. If a line gets too
long, wrap it; don't shorten the name.

**Use the source's words.** If the data calls a column `web_path`, the variable is `web_path` or
`placement_by_web_path`, not a new term like `manifest_path`. A term the data or the outside world already uses
may stay short: `url`, `pdf`, an ARK identifier, the citation prefixes `@wb`, `@rhc`, `@oweek-`. Names still need
three characters, so write `ark_id`, not `id`. Spell out anything the script itself made up.

**One meaning per word in a script.** In `apply_photos.py`, "gallery" means one `GALLERY_PAGES` entry and its
photos; the HTML rendered for it is a "photo grid", and the lightbox's grouping is a `lightbox_group`.
`placement` always means one photo entry.

**Paths and addresses say what they're relative to:**

| Suffix | Means | Example |
|---|---|---|
| `_path` | relative to `docs/`, with forward slashes, as pages link to it | `page_path = "places/old-wiess.md"` |
| `_subpath` | relative to some other folder, named in the comment beside it | `photo_subpath  # relative to docs/assets/photos/` |
| `_file` | absolute path on disk, the thing you `open()` | `page_file = os.path.join(DOCS_ROOT, page_path)` |
| `_link` | relative link written into a page | `image_link = os.path.relpath(image_path, ...)` |
| `_url` | absolute web address | `original_url` |
| `_glob` | a pattern for `glob.glob` | `BIBLIOGRAPHY_FILES_GLOB` |
| `_ROOT` | absolute folder that other paths are relative to | `REPO_ROOT`, `DOCS_ROOT` |

When a whole script works in a frame other than `docs/` (a corpus folder, the repo root), name it
(`corpus_path`, `repo_path`) and say what the frame is where the value first appears: in a constant's comment,
or in the docstring of the function that takes it.

**Kinds of name:**

- Functions start with a verb: `update_manifest`, `check_every_photo_file_exists`. A function that only works
  out a value uses a verb for how: `render_figure`, `format_manifest_credit`, `escape_html_attribute`,
  `find_citation_url`.
- Classes are nouns in CapWords: `PhotoPlacement`, `GalleryPage`.
- Module constants are UPPER_SNAKE_CASE: `GALLERY_INDEX_PATH`.
- `_` is the only short name allowed. It marks a value you deliberately ignore.
- Don't start function names with `_`. These scripts aren't libraries, and the docstring check skips `_names`.

These rules cover hand-edited data files such as `photo_placements.py` too.

## 2. Docstrings

Write docstrings as plain paragraphs. Don't use labels like `Why:` or `How:`.

### The module docstring

Every script opens with one. After a one-line summary, say:

- **why the script exists:** what goes wrong or drifts without it;
- **what it reads and what it writes:** list every file it writes. If it writes none, say so and say where
  its output goes ("prints one line per input");
- **how to run it:** the exact command, and when to run it;
- **what to do if it stops:** for each error message, what has already been written. This is what someone needs
  when the script fails halfway. Also list any output that means "not recognised" rather than an error.

Lists, command lines and examples go in indented blocks, introduced by a sentence. See the top of
`apply_photos.py`.

If a script prints its module docstring as usage text (`print(__doc__)`), keep doing so. Put the run commands
before the failure notes, since they are what someone asking for help needs first.

### Function docstrings

**First line:** one sentence saying what calling it does, starting with a verb and ending with a period.
"Return each gallery's photos…", "Write each gallery's photo grid into its Record page…". Not a noun phrase like
"The photo grid for a page." The sentence must fit on one line (ruff `D205`). If it doesn't, shorten it and move
the detail into the next paragraph; don't wrap it.

**Then, if the reason isn't obvious, a paragraph on why.** Say what it is for, in terms of the site, the editors
or the readers, and what would go wrong without it. Mention anything it relies on: an order, a file another
script creates, a key that must exist.

**Then, if the method isn't visible from the code, a paragraph on how.** Name the MkDocs plugin that reads the
output, the format rule, or the trick a reader would miss.

Don't describe the code line by line. If the paragraph could be rebuilt by reading the function, delete it.

**Match the length to the function.** A three-line helper gets one sentence, with the reason folded in:

```python
def escape_html_attribute(text: str) -> str:
    """Escape text for a double-quoted HTML attribute (captions contain quotes and ampersands)."""
```

A function that does a whole job gets the summary plus a paragraph or two:

```python
def update_manifest(placements: list[PhotoPlacement], gallery_pages: dict[str, GalleryPage]) -> int:
    """Copy captions, credits, dates and topics into manifest.tsv, and return how many rows it rewrote.

    The manifest is the record that will travel with the photos to the Internet Archive, so it must
    say what each photo shows to someone who never sees this site.

    Rows are created by tools/make_web_photos.py, not here. This only overwrites four columns of rows
    that already exist, and leaves sizes, checksums and unplaced photos alone. Columns are found by
    header name, so reordering them in the file is safe. Both exits happen before the file is
    rewritten.
    """
```

**No `Args:` or `Returns:` sections unless they add something** the names, type hints and summary don't
already say: allowed values, units, an example, what's left on disk after a failure. When you do write `Args:`,
list every argument.

### Class docstrings

Start with a noun phrase saying what one instance is: "One photograph, the gallery it belongs to, and what to
say about it." Give each field of a record a short comment beside it on what it holds.

### Keep docstrings true

A docstring that's out of date is worse than none. When you change what a function does, reread its docstring.
Don't quote current data that will change ("Old Wiess has two galleries"); state the rule ("two galleries may
share a page"). Don't give a reason you haven't checked. A plausible but false "why" misleads more than no
"why" at all.

## 3. Comments

Comments are for surprises: why a line is the way it is, or how a dense line works. Good places for them:

- a regular expression, explained piece by piece;
- a choice that looks wrong but isn't ("the replacement is a function, not a string, so backslashes in
  captions are written as-is");
- path arithmetic, such as converting a link from one page's folder to another's;
- a value someone has to update by hand ("Update when someone reviews the Photographs page").

Don't restate the next line, and don't leave commented-out code. Add `# noqa` only for a rule that is switched on
in `pyproject.toml`, with the reason beside it.

## 4. Structure

- **Give tuple records named fields.** Don't index with numbers (`entry[4]`, `PAGES[key][0]`). Turn rows into a
  `typing.NamedTuple` where the script starts, or unpack them into named variables where they're first used.
- **Name regex groups and read them by name.** Use `(?P<timestamp>...)` and `match["timestamp"]`, not `group(1)`
  or `groups()`, which are numbered indexing too. A regex used in more than one place, or longer than a line,
  becomes a compiled UPPER_CASE constant with a comment.
- **Order the file top-down.** Imports, then constants, then record types. Then `main()`, then each step's
  function in the order `main()` calls it, each followed by the helpers only it uses. Helpers shared by more
  than one step go at the end.
- **Make `main()` read like a list of steps.** One call per job, each job a function with a verb name. If the
  script takes arguments, `main(arguments: list[str])` reads them and calls one function per mode. Use
  `argparse` in new scripts.
- **The `if __name__ == "__main__":` block is one line**, `main()` or `main(sys.argv[1:])`. All work happens in
  functions, where the linters can see it.
- **Type-hint every function signature**, with built-in generics: `list[PhotoPlacement]`,
  `dict[str, GalleryPage]`. The hints document what a parameter holds better than an `Args:` entry can.
- **Open files with `with`.**
- **Never write one machine's path into a script.** Folders outside this repository (the research corpus, the
  governance checkout) come from `tools/paths.py`: `corpus_folder()`, `governance_folder()`. Folders inside it are
  found from `REPOSITORY_ROOT` there, or from the script's own `__file__`. CI fails on `/home/`, `/Users/` or
  `/mnt/` in `tools/` and `hooks/`.
- **Lines are at most 120 characters.** Wrap long text with implicit string concatenation. Hand-edited data files
  such as `photo_placements.py` are exempt.
- **Standard library, plus what `requirements.txt` installs for the site** (MkDocs, PyYAML), on Python 3.12.
  Anything else, such as Pillow for `make_web_photos.py`, is named in the module docstring. If only one mode of
  a script needs an extra package, import it inside the function that uses it, with a comment saying why.

## 5. What the linters check, and what review checks

Run the linters before you push. CI (`.github/workflows/lint.yml`) runs the same two commands on every pull
request that touches `tools/`, `hooks/`, the lint settings or the lint workflow.

```
pip install -r requirements-dev.txt
ruff check
pylint tools hooks
```

| Rule | Checked by |
|---|---|
| Every module, class and public function has a docstring | ruff `D` |
| A function's summary starts with a verb | ruff `D401` |
| snake_case functions and variables, CapWords classes | ruff `N` |
| UPPER_SNAKE_CASE module constants; one-word constants at least 4 characters | pylint `invalid-name` |
| Variable, argument, function and class names at least 3 characters | pylint `invalid-name` |
| No banned abbreviations (`rel`, `idx`, `fh`, `tmp`, …) | pylint `disallowed-name` (`bad-names` in `pyproject.toml`) |
| Type hints on every argument, `*args`, `**kwargs` and return | ruff `ANN001`, `ANN002`, `ANN003`, `ANN201`, `ANN202` |
| At most 10 branches and 40 statements in a function | ruff `C901`, `PLR0915` |
| Files opened with `with`; one import and one statement per line; no commented-out code | ruff `SIM115`, `E401`, `E702`, `ERA001` |
| Lines of at most 120 characters | ruff `E501` |
| Docstrings explain why and how, and are still true | **review** |
| Names say what the value is; one meaning per word; path suffixes; function names start with a verb | **review** |
| No numbered indexing into records or regex groups | **review** |
| Comments explain surprises, not the next line | **review** |

When review finds the same abbreviation more than once, add it to `bad-names` in `pyproject.toml`.

### Rolling it out

Scripts that haven't been rewritten yet are listed in `pyproject.toml`, twice: ruff's `extend-exclude` and
pylint's `ignore`. To convert one:

1. **Rewrite it to this guide without changing what it does**, including bugs and what it does with bad input.
   If you find a bug, note it in the docstring or open an issue, and fix it in a separate commit. That keeps
   step 2's comparison exact. Two changes are allowed: usage text that prints the module docstring, and the
   traceback from bad input. Input that stopped the old version with a traceback must still stop with one,
   with the same exit status, but the exception type and message may change.
2. **Check that it behaves exactly as before.** Make a second copy of the repo, for example with
   `git worktree add ../tfwkb-before HEAD`. Run the old and new versions on the same arguments: the examples in
   the docstring, real inputs from `docs/` or `sources/`, and at least one unrecognised or malformed input.
   Compare what they print, their exit status, and `diff -r` of any folder they write to (exclude `.git`).
3. **Remove it from both lists** in the same commit.

New scripts aren't on either list, so they're linted from the start.
