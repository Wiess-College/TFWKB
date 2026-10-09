# Team Family Wiess Knowledge Base 💛🖤💛

The sourced history of Wiess College—traditions, places, people, governance and how they changed—with every claim cited.  
**TL:DR; if you're just looking for the knowledge-base website, it's here: https://wiess-college.github.io/TFWKB/**

## How it Works

### Directories
 - **[docs/](docs/)**:         where all the markdown files live with all the cited information about Wiess in them
 - **[sources/](/sources/README.md)**:       this is where the build tools have saved records of all the citations used in the docs. it's ok to add to these manually too.
 - **[tools/](/tools/README.md)**:         the toolchain used to contribute, since we're citing but not duplicating sources  

### GitHub Tools

 - **[Actions](https://github.com/Wiess-College/TFWKB/actions)**:        build mkdocs, make the pretty HTML, and serve on GitHub pages **site:** https://wiess-college.github.io/TFWKB/
 - **[Wiki](https://github.com/Wiess-College/TFWKB/wiki)**:           a place for anyone to share stories, provide links and leads, and collaborate on content. This is the commons and you can comes say anything here.
 - **[Issues](https://github.com/Wiess-College/TFWKB/issues)**:         a place to report issues: with content, with the sites, or with the code

Within each section there's a bit more detail, and you can view the various README.md files for more information. The mkdocs pages serve up links to GitHub issue templates so in-page corrections can be suggested, but there are also links to the wiki pages as well.

## 🧠 Contributing Knowledge

1. Expand "[docs](docs/)" and navigate to the page you want to edit. 
2. Tap the "Edit this file" ✎ button 
3. Make your changes
4. Commit (save) the file

## 🤓 Contributing Code or Sources

Check tools/readme.md for more information about the technical underpinnings and how you can help.


### Other locations and tools

#### **overrides/**
where mkdocs override files go  


#### **sources/**
| path | job | 
|------|-----| 
| **bibliography/<_type_\>.yaml**   |  every source the pages cite (key, permalink or held_by, evidence class, notes) |  
| **glossaries/\<_key_\>.tsv**   |  1,672 definitions from 16 glossaries, 1994–2025, one file per source  |  
| **manifests/**   | where each examined file came from (contributors' working copies are not in the repo)   |  
| **governance-versions.md**    | generated from the governance repo's tags    |  
| **photo-placements.yaml** | every photo's page, caption, credit and date; tools/apply_photos.py puts them on the site  |    
| **portal-issue-dates.tsv** | a table matching Texas History arks to Thresher dates |
 #### **tools/**  
 maintainer scripts; tools/README.md says what each does and when to run it    |  
#### **setup.sh**  
sets up a new machine: .venv/, tfwkb.tfwkb.config.example.yml, a first build    |  
#### **tools/STYLE.md**  
how to write those helpers (names, docstrings, linting); pyproject.toml holds the lint rules  


## 💻 Installing locally

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

Read `docs/contributing/citing.md` and `docs/contributing/page-template.md` before writing. Conflicts between sources go in the page, under **Variants & disputes**.