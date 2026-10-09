# TFWKB style guide

How to write and rewrite pages for Team Family Knowledgebase. Read this before you touch a page under `docs/`.

Assume that readers are mostly college students on their phones or in a hurry. Give them the plain facts first and short paragraphs. The timeline and sources are underneath for anyone who wants to check.

---

## 1. Voice

Write like a good reference work about a fun place: plain, exact, and calm. The fun comes from the facts and from the sources' own words, not from our sentences.

- **Neutral narrator.** Third person. No "you", "we'll", exclamation marks, jokes or winks in our own sentences. Use Present tense for things that still happen ("Cabinet meets on Wednesdays"), past tense for things that ended or were last seen long ago ("JamFest was…").
- **Quote a source; don't imitate them.** for example, o-week books are written like a hype video. That voice belongs in quotation marks, mostly under "Historic references". In the body, say what happened in flat terms: "Freshmen are drawn at random," not "it's a little bit complicated, but you'll figure it out."
- **Only details that define the thing.** Ask: would a Wiessman from another decade recognise the thing from this sentence? "A day of live bands in the Acabowl" passes. "Free", "food", "towel on the grass" don't. Side details can live in the timeline.
- **Short and concrete.** One idea per sentence, most under 20 words. Paragraphs of one to three sentences. Specific nouns and dates ("16 April 1993", "12 to 14 acts"); no filler ("over the years", "it's worth noting", "a variety of").
- **Explain by linking, not by asides.** Link the first mention of a Wiess word to its page. Avoid parenthetical glosses like "(a grown-up who lives in the college)"; if a gloss is needed, use a short noun phrase: "Dr. Bill Wilson, a longtime resident associate".
- **Say uncertainty once, plainly.** "The earliest mention found so far is 1987." Don't repeat it in every paragraph, and don't narrate the research ("we dug through…").
- **Give the record the benefit of the doubt.** What we've gathered is a small part of what exists. Rice's Woodson Research Center alone holds 34.75 linear feet of Wiess papers, plus 28 GB of digital files. If we haven't found something, nothing is lost, missing, forgotten or undocumented: it hasn't been found yet.
- **Disagreements in one sentence.** "The sources disagree: the 2005 site says 1974, the college website 1975." Both citations. Don't pick a winner quietly.
- **Words to avoid:** "corpus", "attested", "provenance", "extant", "the record shows", "notably", "legendary", "beloved", "iconic", "epic", "super", "vibes", "sadly", "survive(s)" (about documents).
- **Glossary of house terms** (link on first use): Magister → [Magisters](docs/people/magisters.md);
  Commons → [The Commons](docs/places/commons.md); O-Week → [O-Week](docs/traditions/o-week.md);
  Cabinet → [Cabinet](docs/governance/cabinet.md); resident associate (RA) →
  [Resident Associates](docs/people/associates.md); jack → explain in a few words or link
  [The Housing Jack](docs/traditions/housing-jack.md).

## 2. Page shape

Every page about something (a tradition, place, office, role) uses this shape, top to bottom. The models are
`docs/traditions/jamfest.md` and `docs/governance/cabinet.md`.

```markdown
---
(front matter: keep as is)
---

# Page title

One or two plain sentences saying what it is now, or what it was. Cite them.

<div class="facts" markdown>

- **Held** Spring, usually a Friday in mid-April
- **Place** The Acabowl
- **First found** March 1987
- **Last found** April 2011

</div>

## How it works            (or "How it worked")

The present first: who, what, when, where, how. Two to four short paragraphs.

## History                 (or "How it has changed")

The past second, oldest to newest. A timeline chart helps when the thing had phases:

```timeline
from: 1985
to: 2023
Talent show in the Commons: ?1987-1992
Concert in the Acabowl: 1993-2001
Short evening show: 2010-2011?
* Two stages, 14 acts: 2005
```

Bold run-in labels for eras are fine: **Talent show, 1987–1992.** …

<!-- GALLERY:key -->
...photos stay visible, untouched...
<!-- /GALLERY:key -->

## Timeline

| When | What | Evidence |
|---|---|---|
| 1987-03-27 | … [@source] | [P] |

## Historic references

!!! quote "O-Week book, 2003"
    "The source's own words, short." [@source]
```

Notes on the shape:

- **Key facts strip:** three to six short facts under the lead, no citations needed if the body cites them.
  Pick from: Held / Meets, Place, Run by / Led by, Members, First found, Last found, Status, Followed by.
- **Timeline chart** (a fenced `timeline` block): one row per phase, office or version. `1993-2001` is a solid
  bar for what the sources show; a leading `?` (`?1987-1992`) adds a fade before the first mention found, a
  trailing `?` (`2010-2011?`) a fade after the last; something still going ends in an arrow: write `2012-now`, `2012-current` or just `2012-`; `* Label: 2005` is a single
  marker for an event. Something seen only once, which may have run longer, is `?2017?`: a one-year bar with
  short fades on both sides. Group rows under a heading with `[Vice Presidents]`. One row can hold several labelled segments,
  separated by semicolons, written either way round: `Internal VP: ?1993-2006 Executive; 2016- Internal` or
  `Assistant: ?2020-2024; Apprentice: 2025-now`. `[Parliamentarian]: ?1993-now` is a one-row group. A bar that starts
  before `from:` is cut at the left edge and marked ‹. Keep the dates exactly as the timeline table and sources give them.
- **No TL;DR box.** The lead and the key facts do that job.
- **Citations** are written inline as `[@key]` and render as numbered footnotes with a References list at the
  bottom (built automatically).
- **Timeline** is visible, at the bottom, with its evidence tags. Long pages may collapse it with
  `??? info "Timeline"`.
- **Historic references** holds the best two to five quotes, each in a `!!! quote "Source, year"` box. This is
  where the O-Week books' voice belongs.
- **Open questions don't live on the page.** They go in `issues/open-questions.tsv` and from there into GitHub
  issues (see `issues/README.md`).
- **Disagreements** get one plain sentence where they matter, with both citations.
- **Anchors:** if other pages link to a heading, keep it or add `{ #old-anchor }`. The strict build catches
  broken ones.

## 3. Rules (these are not optional)

1. **Never drop a citation that supports a claim you keep.** Every fact left on the page keeps its `[@…]`. If you cut a fact, you may cut its citation; if you keep a fact, its citation goes with it, even into the key facts.
2. **Don't invent facts.** Simplify, don't embellish. No new dates, numbers, names or "probably"s that aren't in the page or its sources. If the page says "c.1990", you say "around 1990", not "1990".
3. **Evidence tags `[P]` `[R]` `[T]` stay inside the receipts tables**, in the Evidence column. Don't sprinkle them in the prose.
4. **Gallery blocks stay intact.** Never edit anything between `<!-- GALLERY:key -->` and `<!-- /GALLERY:key -->`, never remove the markers, and never put a gallery inside a collapsed `???` box. Photos stay visible.
5. **Front matter stays.** Don't change `title`, `status`, `last_reviewed`, `reviewed_by`, `search`, `hide`, or anything else between the `---` lines.
6. **Big Bang spoiler rule.** Big Bang is a surprise for freshmen. Its page shows only a teaser ("It's coming.") and everything else stays inside the `??? danger "Spoilers ahead…"` box, and the page stays out of search (`search: exclude: true`). On *other* pages, never describe what happens at Big Bang; just link the page. Same goes for anything else a page marks as a spoiler.
7. **Privacy.** No one who may still be a student is named: anyone whose Wiess or Rice mention dates from the 2023–24 academic year or later is described by role instead ("the Chief Justice", "a Head Fellow"). Naming a current officer can imply academic standing, which is student record information. Older students appear only in their public college roles (officers, authors, people quoted in the Thresher, public commenters). No room numbers, phone numbers, addresses or rosters, even if an old source printed them. Nothing revealing from Night of Decadence. Anyone can ask to be named by role instead. See `docs/contributing/rights.md`.
8. **Disagreements stay visible.** If sources disagree, say so briefly in the prose, with both citations. Don't quietly pick a winner. The full back-and-forth goes in an issue.
9. **Quotes are for Historic references.** Keep the best short ones (under ~25 words), word-for-word, including odd spelling, with their citations (see Rights). Quote sparingly in the body; never borrow a source's hype as our own wording.
10. **Build must pass.** `mkdocs build --strict` with no warnings. Unknown citation keys fail the build.

## 4. Formatting cheat sheet

| You want | Write |
|---|---|
| The key facts strip | `<div class="facts" markdown>` + a list of `**Label** value` (see section 2) |
| A timeline chart | a fenced `timeline` block (see section 2) |
| A quote under Historic references | `!!! quote "O-Week book, 2003"` |
| A collapsed timeline (long pages only) | `??? info "Timeline"` |
| A collapsed box that starts open | `???+ info "…"` |
| A spoiler | `??? danger "Spoilers ahead — opening this will ruin all the fun"` |
| A highlighted note without an admonition | `<div class="tldr" markdown>…</div>` |
| A citation | `[@key]`, `[@key p.14]`, `[@wb 20070709182921 http://teamwiess.com/x.html]` |
| An evidence tag (tables only) | `[P]` `[R]` `[T]` |
| An icon | `:material-pig-variant:` (any [Material icon](https://pictogrammers.com/library/mdi/)) |
| A button | `[Label](path.md){ .md-button }` |

The "Suggest a correction / Add your story / Discuss" buttons are added to every page automatically (`overrides/main.html`). Don't add them by hand. To hide them on a page, set `page_actions: false` in its front matter.

## 5. Before and after

**Before** (borrowed hype, incidental details, asides):

> Bands in the Acabowl, towels on the grass, hamburgers all day. It was free, and from 1993 it usually ran from the afternoon deep into the night. Dr. Bill Wilson, a longtime Wiess RA (a grown-up who lives in the college), ran "pretty much all the 'tech'".

**After:**

> Student bands from Rice played alongside Houston bands. From about 2000, a touring band headlined. Dr. Bill Wilson, a longtime Wiess resident associate, ran the sound and lent students his equipment.

Same subject, fewer words, nothing a reader has to skip past.

## 6. Checklist before you save

- [ ] Front matter unchanged.
- [ ] A one- or two-sentence lead saying what it is, then the key facts strip.
- [ ] Every kept fact still has its citation.
- [ ] Present before past: how it works, then history.
- [ ] Timeline at the bottom, rows unchanged; best quotes under Historic references.
- [ ] No "you", no exclamation marks, no borrowed hype, no incidental details.
- [ ] Evidence tags only in tables.
- [ ] Gallery blocks untouched and visible.
- [ ] Jargon explained and linked the first time.
- [ ] No paragraph over ~3 sentences.
- [ ] Spoiler and privacy rules followed.
- [ ] `mkdocs build --strict` is clean.
