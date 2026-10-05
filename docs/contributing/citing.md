# Citing

Team Familypedia holds condensed knowledge, not copies of the evidence. The evidence lives elsewhere — in the Wayback Machine, the Portal to Texas History, the Woodson Research Center, the college's own artifacts — so **every claim carries a permalink that resolves without us.** Unsourced claims and stories are still important, and a page with an unsourced claim is a Commons page, not a Record page.

## The short forms

Write citations inline, right after the claim. The site build turns them into links.

| You write | It means | It becomes |
|---|---|---|
| `[@oweek-2006 p.84]` | a source in the [bibliography](../sources/bibliography.md), with a locator | a link to the archived PDF, opened at page 84 |
| `[@riceinfo-beerbike]` | a bibliography source, no locator | a link to the archived page |
| `[@wb 20070709182921 http://teamwiess.com/nod.html]` | a Wayback Machine capture: timestamp, then the original URL | `web.archive.org/web/20070709182921/http://teamwiess.com/nod.html` |
| `[@portal metapth245573 p.27]` | a Rice Thresher page at the Portal to Texas History: ark id, then page | the page viewer at UNT |
| `[@woodson UA0079 box 3 folder 12]` | an item in the Woodson Research Center | a pointer to the finding aid |

The locator is free text: `p.27`, `part 6 p.3`, `comment by Dave McCooey, 14 Dec 2021`, `slide 28`. Keep it short enough to read inline.

An unknown key fails the build (`mkdocs build --strict`), which is the point: you cannot cite something the bibliography does not know about. **To cite a new source, add it to the bibliography first** — a few lines in `sources/bibliography/*.yaml`. Fields follow APA 7 so the build can render a reference list that a Rice reader will recognize:

```yaml
- key: thresher-1984-11-02
  type: newspaper-article
  authors:
    - { family: Gillis, given: A. }
  year: 1984
  date: 1984-11-02
  title: "NOD 'Animal Farm' report"
  container-title: The Rice Thresher
  volume: 72
  issue: 11
  pages: "27"
  publisher: Rice University
  publisher-place: Houston, TX
  url: https://texashistory.unt.edu/ark:/67531/metapth245573/m1/27/
  archive: Portal to Texas History
  accessed: 2026-10-05
  evidence: P
  notes: '"the pig was the symbol of the night, the decadent farm animal, the war-pig"'

- key: maxham-1998-pig
  type: unpublished-document
  authors:
    - { family: Maxham, given: J. }
  year: 1998
  title: "Design notes on the Wiess pig (1986)"
  archive: Woodson Research Center, Fondren Library, Rice University
  archive-collection: Wiess College Records
  archive-location: "UA 0079, box 3, folder 12"
  evidence: R

- key: mccooey-2021-nod
  type: personal-communication
  authors:
    - { family: McCooey, given: D. }
  class-year: 1987
  year: 2021
  date: 2021-12-14
  title: "Comment on 'NOD origins' thread"
  container-title: Rice History Corner
  url: https://ricehistorycorner.com/2021/12/10/im-pissed/
  wayback: https://web.archive.org/web/20220103145522/https://ricehistorycorner.com/2021/12/10/im-pissed/
  evidence: T
```

Rendered in APA 7, those become:

- Gillis, A. (1984, November 2). NOD 'Animal Farm' report. *The Rice Thresher*, *72*(11), 27. Portal to Texas History. https://texashistory.unt.edu/ark:/67531/metapth245573/m1/27/
- Maxham, J. (1998). *Design notes on the Wiess pig (1986)* [Unpublished document]. Wiess College Records (UA 0079, box 3, folder 12), Woodson Research Center, Fondren Library, Rice University.
- McCooey, D. (Class of 1987). (2021, December 14). Comment on 'NOD origins' thread [Online comment]. *Rice History Corner.* https://ricehistorycorner.com/2021/12/10/im-pissed/

A few APA conventions that shape the YAML:

- `authors` is a list of `{ family, given }` pairs. Initials go in `given` (`A.`, not `Alice`); multi-word surnames stay whole in `family`. Unknown author: omit the field, and the renderer falls back to the title in the author slot.
- `year` is required for the in-text short form; `date` is the full publication date for the reference list. For undated web pages, write `year: n.d.`.
- `type` is one of `journal-article`, `newspaper-article`, `magazine-article`, `book`, `book-chapter`, `webpage`, `unpublished-document`, `personal-communication`, `photograph`, `audiovisual`. The renderer uses this to pick the APA template.
- `container-title` is the italicized title in the reference: the journal, newspaper, book, or website.
- `archive`, `archive-collection`, `archive-location` describe where the physical or archival copy lives — Woodson, Portal to Texas History, the Wayback Machine. `wayback` is a convenience for the archived mirror of a `url`.
- `evidence` (`P`, `R`, `T`) is a Familypedia extension, not APA. It drives the inline tag; APA output ignores it. For `T` sources, add `class-year` so the reader can place the voice.

Keys are lowercase, hyphenated, and stable: `oweek-2014`, `constitution-2013`, `riceinfo-ubangee`, `rhc-2021-12-10-im-pissed`, `campanile-1988`. They are *not* APA short forms — the renderer builds `(Gillis, 1984)` from the `authors` and `year` fields. Once a key is used on a page it is never renamed.

## Tag the kind of evidence

Every dated row in a timeline, and any claim that matters, carries one of three tags (see [Evidence classes](../sources/evidence-classes.md)):

- `[P]` — **primary / contemporary**: a document from the time, read directly. A Thresher report the week it happened, an O-Week book, a constitution, a photograph, a Wayback capture.
- `[R]` — **retrospective**: a later account by someone in a position to know. A history page written years afterwards, a magazine feature, Maxham's 1998 design document about 1986.
- `[T]` — **testimony**: a memory. A blog comment, an interview, a conversation, a note inside the pig. Always say who, their class year if known, and when they said it.

The tags are not a ranking of truth. A 2021 comment by the person who built the pig beats a 1999 web page by someone who wasn't there. They tell the reader what kind of thing they are being asked to trust, so that when two sources disagree they can weigh them.

## When sources disagree

Do not pick silently. Put every version in the page's **Variants & disputes** section with its citation, say which you find more convincing and why, and leave the question open in **Open questions** if it is. The Team Wiess chant is dated 1974, 1975 and 1984 by three different Wiess sources; the page says so.

## What not to cite

- A page on this site. Link to it instead; the citation belongs on the page where the claim is sourced.
- Your own memory, without saying so. That is `[T]` testimony: sign it with your name and class year, and put it in the Commons first.
- A search result or an AI summary. Go to the thing and cite the thing.

## Pages from PDFs

`p.N` in a locator refers to the **PDF page**, not the number printed on the page, because that is what the link opens. If they differ and it matters, write both: `p.12 (printed 10)`.

## Images

Photographs and scans are cited like anything else, and the page says where the original is: a Wayback URL, a Campanile page, a file in the college's `artifacts/` collection. Do not upload third-party images to this repository; see [Rights](rights.md).
