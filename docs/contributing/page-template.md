# Page template

Every Record page follows the same shape, so a reader always knows where to find the current understanding, the evidence, and the doubts. Copy this file to start a new page.

````markdown
---
title: <Tradition / place / event / office>
status: draft            # draft → reviewed
last_reviewed: 2026-10-04
reviewed_by: <GitHub handle>
---

# <Title>

<One or two short sentences that hook the reader. Optional.>

!!! abstract "TL;DR"
    - <2–4 bullets, one fact each, each with its citation.> [@handbook-1994]
    - <If someone reads only this box, they should still be right.>

## <A plain, fun heading>

<Two to five short sections, 1–3 short paragraphs each. Every fact keeps its
citation. Where sources disagree, say so here in a sentence:
"The sources disagree: 1974 or 1975" [@handbook-1994] [@oweek-2006 p.36].>

<!-- GALLERY:key -->
<photos stay visible, outside any collapsed box>
<!-- /GALLERY:key -->

??? info "The receipts: timeline"

    | When | What | Evidence |
    |---|---|---|
    | 1984-10-26 | First large effigy, a chicken-wire pig hung at NOD [@portal metapth245573 p.27] | [P] |
    | 1986-04-05 | First Beer Bike balloon, built by Jorge Martin de Nicolas '85 [@maxham-pig-document] | [R] |
    | 2021-12-14 | Dave McCooey: the name came from the Black Sabbath song [@rhc-2021-12-10-im-pissed comment, 14 Dec 2021] | [T] |

??? quote "In the college's own words"

    "The Wiess mascot, an enormous inflatable pig made from plastic and duct tape,
    'flown' at Beer-Bike to the amazement of all." — 1994 Freshman Handbook [@handbook-1994]

<div class="reviewed" markdown>Last reviewed 2026-10-04 by @handle · [Edit this page](#)</div>
````

## Notes on the sections

**TL;DR first.** Someone who reads only the gold box should leave with the right picture. Do not open with "The history of X is long and storied."

**Timeline rows are claims, not prose.** One dated row per claim: ISO dates when known (`1984-10-26`), year-month or year otherwise, `c.` for approximations. Each row carries its own citation and its evidence tag. If a row needs two citations, give it two. If you cannot cite a row yet, leave it out and put it in the Commons or a [GitHub issue](https://github.com/Wiess-College/TFWKB/issues).

**"In the college's own words" is quotation, not paraphrase.** Short, dated, cited. It is where the humour lives, and it is where drift shows: the War Pig was "the Wiess mascot" in 1994 and 2003, "Former Wiess mascot" from 2006 to 2011, and "embodied by the giant wooden pig built by the Class of 2012" from 2014.

**Disagreements get a sentence, where they matter.** Don't pick silently, and don't build a separate section for them: one or two plain sentences in the prose, with both citations.

**Open questions don't live on the page.** They are tracked as [GitHub issues](https://github.com/Wiess-College/TFWKB/issues), where anyone can pick them up. The "Add your story" and "Suggest a correction" buttons point readers there. What we've gathered is a small part of what exists (the Woodson alone holds about 34 linear feet of Wiess papers), so write "we haven't found it yet," not "nobody wrote it down."

**Retired traditions** get the same template plus a line near the top on when and why they stopped, if a source says so. Where the sources simply stop, say "last seen in <year>."
