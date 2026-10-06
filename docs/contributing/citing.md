# Citing

Team Family Knowledgebase holds condensed knowledge, not copies of the evidence. The evidence lives elsewhere—in the Wayback Machine, the Portal to Texas History, the Woodson Research Center, the college's own artifacts—so **every claim carries a permalink that resolves without us.** A page with an unsourced claim is a Commons page, not a Record page.

## The short forms

Write citations inline, right after the claim. The site build turns each one into a small numbered footnote, Wikipedia-style: a superscript number in the text that links to a **References** list at the bottom of the page. Citing the same source and page again reuses its number. Hovering a number shows the source.

Thresher pages from the Portal are dated automatically when their ark id is in `sources/portal-issue-dates.tsv`. When you cite a new Thresher issue, add a line there (ark id, tab, `YYYY-MM-DD`).

| You write | It means | The footnote links to |
|---|---|---|
| `[@oweek-2006 p.84]` | a source in the [bibliography](../sources/bibliography.md), with a locator | a link to the archived PDF, opened at page 84 |
| `[@riceinfo-beerbike]` | a bibliography source, no locator | a link to the archived page |
| `[@wb 20070709182921 http://teamwiess.com/nod.html]` | a Wayback Machine capture: timestamp, then the original URL | `web.archive.org/web/20070709182921/http://teamwiess.com/nod.html` |
| `[@portal metapth245573 p.27]` | a Rice Thresher page at the Portal to Texas History: ark id, then page | the page viewer at UNT |
| `[@woodson UA0079 box 3 folder 12]` | an item in the Woodson Research Center | a pointer to the finding aid |

The locator is free text: `p.27`, `part 6 p.3`, `comment by Dave McCooey, 14 Dec 2021`, `slide 28`. Keep it short enough to read inline.

An unknown key fails the build (`mkdocs build --strict`), which is the point: you cannot cite something the bibliography does not know about. **To cite a new source, add it to the bibliography first**—a few lines in `sources/bibliography/*.yaml`:

```yaml
- key: thresher-1984-11-02
  title: "Rice Thresher, 2 Nov 1984, p.27—NOD 'Animal Farm' report"
  type: newspaper
  date: 1984-11-02
  url: https://texashistory.unt.edu/ark:/67531/metapth245573/m1/27/
  evidence: P
  notes: '"the pig was the symbol of the night, the decadent farm animal, the war-pig"'
```

Keys are lowercase, hyphenated, and stable: `oweek-2014`, `constitution-2013`, `riceinfo-ubangee`, `rhc-2021-12-10-im-pissed`, `campanile-1988`. Once a key is used on a page it is never renamed.

## Tag the kind of evidence

Every dated row in a timeline, and any claim that matters, carries one of three tags (see [Evidence classes](../sources/evidence-classes.md)):

- `[P]`—**primary / contemporary**: a document from the time, read directly. A Thresher report the week it happened, an O-Week book, a constitution, a photograph, a Wayback capture.
- `[R]`—**retrospective**: a later account by someone in a position to know. A history page written years afterwards, a magazine feature, Maxham's 1998 design document about 1986.
- `[T]`—**testimony**: a memory. A blog comment, an interview, a conversation, a note inside the pig. Always say who, their class year if known, and when they said it.

The tags are not a ranking of truth. A 2021 comment by the person who built the pig beats a 1999 web page by someone who wasn't there. They tell the reader what kind of thing they are being asked to trust, so that when two sources disagree they can weigh them.

## When sources disagree

Do not pick silently. Say so in one or two plain sentences in the section where the claim is made, with both citations: "The sources disagree: the 2005 site says 1974, the college website says 1975," followed by both citations. If it matters which is right and you can't settle it, open a [GitHub issue](https://github.com/Wiess-College/TFWKB/issues) so someone can go looking; open questions live there, not on the page. The Team Wiess chant is dated 1974, 1975 and 1984 by three different Wiess sources; the page says so.

## What not to cite

- A page on this site. Link to it instead; the citation belongs on the page where the claim is sourced.
- Your own memory, without saying so. That is `[T]` testimony: sign it with your name and class year, and put it in the Commons first.
- A search result or an AI summary. Go to the thing and cite the thing.

## Pages from PDFs

`p.N` in a locator refers to the **PDF page**, not the number printed on the page, because that is what the link opens. If they differ and it matters, write both: `p.12 (printed 10)`.

## Images

Photographs and scans are cited like anything else, and the page says where the original is: a Wayback URL, a Campanile page, a file in the college's `artifacts/` collection. Do not upload third-party images to this repository; see [Rights](rights.md).
