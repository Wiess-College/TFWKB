# TFWKB style guide

How to write and rewrite pages for Team Family Knowledgebase. Read this before you touch a page under `docs/`.

The readers are college students skimming on a phone between classes. Write for them. The receipts are still there for the historians, folded up underneath.

---

## 1. Voice

- **Official-ish, but playful.** Think "a good O-Week book," not "a museum label" and not "a meme page." A joke is fine when the facts are funny on their own (they usually are). Don't make jokes *at* people.
- **8th-grade reading level.** Short words. Short sentences. Most sentences under 20 words.
- **Max ~3 sentences per paragraph.** White space is your friend.
- **"You" is OK.** "If you've been to Beer Bike, you've heard the chant."
- **Active voice.** "The Class of 2012 built a wooden pig," not "A wooden pig was built."
- **Say the uncertain thing plainly.** "We haven't found when this started yet." "The sources disagree: 1974 or 1975." Not "the provenance remains contested."
- **Give the record the benefit of the doubt.** What we've gathered is a thin slice of what exists. Rice's Woodson Research Center alone holds about 34 linear feet of Wiess papers. If we haven't found something, nobody failed, and nothing is lost, missing, forgotten or undocumented. We just haven't found it yet. Write "the earliest mention we've found so far is 2021", not "nobody wrote it down until 2021". Write "last seen in the 2017 book", not "it vanished after 2017". No hyperbole, no drama.
- **No jargon without a translation.** The first time a Wiess or Rice word shows up on a page, explain it in a few plain words and link it:
  - **Magister**: the professor who lives next to the college with their family and looks out for it (used to be called "Master"). Link [Magisters](docs/people/masters-and-magisters.md).
  - **Commons**: the dining hall, Wiess's biggest room. Link [The Commons](docs/places/commons.md).
  - **jack / jacking**: a prank, usually on another college. Explain it inline.
  - **O-Week**: Orientation Week, when new students arrive. Link [O-Week](docs/traditions/o-week.md).
  - **Cabinet**: Wiess's student government. Link [Cabinet](docs/governance/cabinet.md).
  - **RA / Resident Associate**: a grown-up (often faculty or staff) who lives in the college. Link [Resident Associates](docs/people/resident-associates.md).
  - Glossary words in general: link [How we described ourselves](docs/traditions/glossary-series.md).
- **Words to avoid:** "corpus", "attested", "provenance", "extant", "the record shows", "it should be noted", "notably". Say "the sources", "first shows up", "where it came from", "still around".

## 2. Page shape

Every Record page (traditions, places, people, governance, changes) uses this shape, top to bottom.

```markdown
---
(front matter: KEEP EXACTLY AS IS — title, status, last_reviewed, reviewed_by, search, hide…)
---

# Page title

One or two short sentences that hook the reader. Optional.

!!! abstract "TL;DR"
    - 2–4 bullets. The short version.
    - Each bullet is one fact, with its citation [@key].
    - If someone reads only this box, they should still be right.

## A fun, plain heading

Two to five short sections. Plain words. Each fact keeps its [@citation].
Headings can be playful ("Where the name came from", "The year it floated away",
"Why it stopped") — but they should still say what the section is about.

<!-- GALLERY:key -->
...photos stay visible, outside any collapsed box...
<!-- /GALLERY:key -->

??? info "The receipts: timeline"
    | When | What | Evidence |
    |---|---|---|
    | (the existing timeline table, UNCHANGED, indented 4 spaces) | ... | [P] |

```

Notes on the shape:

- **TL;DR** is the `!!! abstract "TL;DR"` admonition (it renders as a gold box). 2–4 bullets. No more.
- **Sections:** 2–5 of them, each 1–3 short paragraphs. If you need more, it probably belongs in the receipts.
- **The receipts** box holds the timeline table *exactly as it was*: same rows, same citations, same evidence tags. Just indent it 4 spaces inside `??? info "The receipts: timeline"`. Leave a blank line after the `???` line and between paragraphs inside the box; every line inside must be indented 4 spaces.
- Other long reference blocks (e.g. "As the college described it, by year", "The pigs, numbered") can also go into their own `??? info "The receipts: …"` box. Keep their content unchanged.
- **Open questions don't live on the page.** They go in `issues/open-questions.tsv`, and from there into GitHub issues (see `issues/README.md`), where the Historian and anyone else can pick them up. The page's "Suggest a correction" and "Add your story" buttons point readers there.
- **Disagreements** get one or two plain sentences in the prose where they matter ("The sources disagree: 1974 or 1975"), with both citations.
- A "Sources" or "See also" list at the bottom can stay as it is.
- Anchors: if other pages link to a heading (e.g. `old-wiess.md#photographs`), keep that heading text, or add `{ #photographs }` to the new heading so the link still works. Run the build to catch broken anchors.

## 3. Rules (these are not optional)

1. **Never drop a citation that supports a claim you keep.** Every fact left on the page keeps its `[@…]`. If you cut a fact, you may cut its citation; if you keep a fact, its citation goes with it, even into the TL;DR.
2. **Don't invent facts.** Simplify, don't embellish. No new dates, numbers, names or "probably"s that aren't in the page or its sources. If the page says "c.1990", you say "around 1990", not "1990".
3. **Evidence tags `[P]` `[R]` `[T]` stay inside the receipts tables**, in the Evidence column. Don't sprinkle them in the prose.
4. **Gallery blocks stay intact.** Never edit anything between `<!-- GALLERY:key -->` and `<!-- /GALLERY:key -->`, never remove the markers, and never put a gallery inside a collapsed `???` box. Photos stay visible.
5. **Front matter stays.** Don't change `title`, `status`, `last_reviewed`, `reviewed_by`, `search`, `hide`, or anything else between the `---` lines.
6. **Big Bang spoiler rule.** Big Bang is a surprise for freshmen. Its page shows only a teaser ("It's coming.") and everything else stays inside the `??? danger "Spoilers ahead…"` box, and the page stays out of search (`search: exclude: true`). On *other* pages, never describe what happens at Big Bang; just link the page. Same goes for anything else a page marks as a spoiler.
7. **Privacy.** Students appear only in their public college roles (officers, authors, people quoted in the Thresher, public commenters). No room numbers, phone numbers, addresses or rosters, even if an old source printed them. Nothing revealing from Night of Decadence. Anyone can ask to be named by role instead. See `docs/contributing/rights.md`.
8. **Disagreements stay visible.** If sources disagree, say so briefly in the prose, with both citations. Don't quietly pick a winner. The full back-and-forth goes in an issue.
9. **Quotes from O-Week books are gold.** Keep the funniest, shortest ones (under ~25 words) with their citations. "Fell with style" beats any paraphrase. Keep quotes word-for-word, including odd spelling, and keep them short (see Rights).
10. **Build must pass.** `mkdocs build --strict` with no warnings. Unknown citation keys fail the build.

## 4. Formatting cheat sheet

| You want | Write |
|---|---|
| The gold summary box | `!!! abstract "TL;DR"` |
| A collapsed receipts box | `??? info "The receipts: timeline"` |
| A collapsed box that starts open | `???+ info "…"` |
| A spoiler | `??? danger "Spoilers ahead — opening this will ruin all the fun"` |
| A highlighted note without an admonition | `<div class="tldr" markdown>…</div>` |
| A citation | `[@key]`, `[@key p.14]`, `[@wb 20070709182921 http://teamwiess.com/x.html]` |
| An evidence tag (tables only) | `[P]` `[R]` `[T]` |
| An icon | `:material-pig-variant:` (any [Material icon](https://pictogrammers.com/library/mdi/)) |
| A button | `[Label](path.md){ .md-button }` |

The "Suggest a correction / Add your story / Discuss" buttons are added to every page automatically (`overrides/main.html`). Don't add them by hand. To hide them on a page, set `page_actions: false` in its front matter.

## 5. Before and after

**Before** (accurate, but heavy):

> The college's record dates it to 1972: the 2005 party site counted that year as "its 34th", and Rice Magazine found a Wiess Magister who "attended the first NOD in 1972" with about thirty other men, though the Thresher of 1998–99 counted from 1973 or 1974.

**After:**

> NOD probably started in 1972. A future Magister remembered going to the first one, with about 30 other guys [@rice-magazine-2016-wiess-traditions]. The Thresher later counted from 1973 or 1974, so people still argue [@thresher-1998-10-30-nod-security] [@thresher-1999-10-29-nod-tonight].

Same facts. Same citations. Half the effort to read.

## 6. Checklist before you save

- [ ] Front matter unchanged.
- [ ] TL;DR box with 2–4 cited bullets.
- [ ] Every kept fact still has its citation.
- [ ] Timeline table unchanged, inside `??? info "The receipts: timeline"`.
- [ ] Evidence tags only in tables.
- [ ] Gallery blocks untouched and visible.
- [ ] Jargon explained and linked the first time.
- [ ] No paragraph over ~3 sentences.
- [ ] Spoiler and privacy rules followed.
- [ ] `mkdocs build --strict` is clean.
