---
title: Maintainers
---

# Maintainers

Team Familypedia belongs to the `Wiess-College` GitHub organization, alongside [WarPig](https://github.com/Wiess-College/WarPig), [governance](https://github.com/Wiess-College/governance) and the TFW tile widget. Organizations survive people: ownership is a role held by several accounts, not a repository someone has to remember to hand over.

## Roles

| Role | Who | Term | Responsibilities |
|---|---|---|---|
| **Org owner** (minimum three, from different clocks) | a staff member (Magister or College Coordinator); an alumni representative; the sitting student Historian | staff: while in post · alumni: 3 years · Historian: the academic year | Keys, billing, adding and removing maintainers. No single owner may remove another. |
| **Historian** | the Cabinet's Historian(s), per the Constitution | Changeover to Changeover | Walk the Commons; open issues; shepherd PRs; run the annual handoff; keep the search log. |
| **Maintainer** | anyone who has had three PRs merged and is nominated by a maintainer | until they ask to step down | Review PRs; approve merges. |
| **Emeritus** | past Historians and maintainers | — | Read access to everything; a standing invitation to answer issues tagged `ask-an-alum`. |

Current holders are listed in `MAINTAINERS.md` at the repository root, with GitHub handles and start dates. *(October 2026: the organization has a single owner. The first job is to add the other two.)*

## CODEOWNERS

Reviews route to the people who know. `docs/traditions/warpig.md` → the WarPig builders and the Historian; `docs/governance/**` and `docs/decisions/**` → the Parliamentarian and the Historian, two approvals required; everything else → any maintainer.

## The annual handoff (at Changeover)

An issue from the template `handoff.md`, closed when all are done:

- [ ] new Historian added as org owner and maintainer; outgoing Historian moved to Emeritus
- [ ] any tokens or deploy keys rotated
- [ ] the wiki mirror and the Wayback save of the site confirmed to have run
- [ ] a "State of the Record" note: pages reviewed this year, disputes resolved, the search log's top five open leads
- [ ] the year's snapshot handed to the Woodson Research Center (UA 0079)

## Off-platform copies

A GitHub Action, on every release: saves the published site to the Wayback Machine; uploads a tarball of the repository to an archive.org item; and once a year hands a snapshot to the Woodson. If GitHub disappears, the Markdown, the manifests and the citations are enough to rebuild everything.
