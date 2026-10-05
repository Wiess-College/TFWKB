---
title: Contributing
---

# Contributing

Team Family Knowledgebase is maintained by Wiess students, alumni and staff on GitHub, in the open. Anyone with a GitHub account can contribute; what differs is where.

**Two tiers.** The [Commons](https://github.com/Wiess-College/TFWKB/wiki)—this repository's wiki—is the easy place to *say* something: a memory, a question, a draft, a photograph you can't quite date. No review. Sign with your name and class year, say how you know (I was there / I was told / I read it in…), and strike through rather than delete. The **Record**—these pages—is the careful place to *state* something: every change is a pull request, every claim is cited, and one other maintainer approves before it lands (two for Governance and Decisions pages). The path from one to the other is [Commons → Issue → PR → Record](commons-to-record.md), and walking it is the Historian's job.

**Editing a page** takes no git. Click the pencil at the top of any page; GitHub opens the Markdown in your browser, and when you save it opens a pull request for you. Read [Citing](citing.md) first—an uncited claim will be sent back—and use the [page template](page-template.md) for a new page.

**What belongs here**: anything about Wiess College that can be sourced. Traditions, places, people in their college roles, governance, decisions, the web. **What does not**: anything about a private individual beyond their public college role; student rosters, room numbers, phone numbers (even when an old source printed them); third-party text or images beyond brief quotation (see [Rights](rights.md)); and claims that cannot be cited, which belong in the Commons until they can.

**Who maintains it**: see [Maintainers](maintainers.md)—the org owners, how the roles rotate at Changeover, and the annual handoff.

**Tooling**: the site is MkDocs Material; `mkdocs serve` previews it locally after `pip install mkdocs-material`. `tools/` holds small, dependency-free scripts: `cite.py` (corpus path ↔ citation), `check_links.py` (do the permalinks still resolve), `build_glossary_series.py`, `import_governance_changes.py`, `fix_pdf_text.py`. GitHub Actions builds and publishes on every push to `main` and fails the build on an unknown citation key.
