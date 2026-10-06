---
title: Where to look
---

# Where to look

A map of the archives: who holds what, and the tricks that worked in the autumn-2026 dig. Learned a new trick? Add it here.

!!! abstract "TL;DR"
    - **Old websites:** the Wayback Machine.
    - **The Thresher:** the Portal to Texas History up to about 2009, ricethresher.org after.
    - **Anything before 1991 on paper** (constitutions, Cabinet minutes, the 1960s): the Woodson Research Center, Wiess College Records UA 0079.
    - **Alumni memories:** the comment threads on Rice History Corner.

## The Wiess websites, 1997–2026

All in the **Wayback Machine** (web.archive.org).

| Era | Host | What is there | Captures |
|---|---|---|---|
| 1998–2003 | `riceinfo.rice.edu/projects/colleges/wiess/` | the first site (Cunningham 1997, Abraham 1998, Wagner 1999): glossary, history, traditions, rules, people | 116 page versions |
| 2000–01 | `www.rice.edu/projects/colleges/wiess/` | the same site, later hostname | 50 |
| 2001–2021 | `teamwiess.com` | O-Week books as PDFs (2003, 2006–11, 2014–17), tradition pages, NOD sites, Cabinet minutes, forum 2007–08, government pages 2020–21 | ~3,400 content captures; 60,000+ of forum spam in 2009 |
| 2014– | `wiess.rice.edu` | the current site; from 2023 a React app whose text is in a JS bundle, so captures are often empty shells | 44 homepage versions |
| 2011–14 | `wiess.wordpress.com` | the official blog: comedy Cabinet minutes, newsletters | 52 URLs |
| 2012–17 | `wiessassociates.rice.edu` | the Associates' blog, with a Traditions page | 83 URLs (site retired, HTTP 410) |
| 2011–13 | `wiessmentors.rice.edu` | Wiess Mentors program | 37 URLs (retired) |
| 2018– | `wiesscooks.rice.edu` | Wiess Cooks | live |
| 1997–2004 | `*.wiess.rice.edu` | students' own machines named under the college (bobafett, wiess-2043, jwh06, polonius…) | CDX `matchType=domain` |

??? info "Wayback recipes"
    All in the **Wayback Machine** (web.archive.org). The CDX API lists every capture; `collapse=digest` gives version history, `collapse=urlkey` gives an inventory; `/web/<timestamp>id_/<url>` fetches the raw bytes.

    Recipes: `url=wiess.rice.edu&matchType=domain` finds dead sub-hosts; a current-DNS subdomain census (26,719 rice.edu hostnames in 2026) finds what still resolves—use both. The 2003 teamwiess.com homepage was Flash and renders only after the Ruffle emulator loads.

## The Rice Thresher

The student paper, and the best source for anything before the web.

- **1916–c.2009:** the Portal to Texas History (texashistory.unt.edu), full run, with OCR text.
- **c.2009–now:** ricethresher.org.

The Portal's search now sits behind an "I'm not a robot" check, which agents must not complete. The same pages' OCR text is also served at **digital.library.unt.edu**, page by page, at `/ark:/67531/<id>/m1/<page>/ocr/`. That's how every issue from November 1956 to January 1994 was read in October 2026 (see the [search log](search-log.md)).

??? info "Thresher recipes"
    **1916–c.2009: the Portal to Texas History** (texashistory.unt.edu), full run, OCR'd. Ark ids are sequential by issue (Vol. 71 No. 1 = `metapth245533`; Vol. 72 No. 4 = `metapth245566`). Per-page OCR at `/ark:/67531/<id>/m1/<page>/ocr/`. The cheap trick: per-issue hit snippets at `/ark:/67531/<id>/hits/?format=json&q=<query>` return page numbers and highlighted context without opening pages. Phrase search does not stem ("war pig" ≠ "war pigs"). The `/search/` and `/explore/` pages trip a CAPTCHA once per browser session. Cite as `[@portal <ark> p.N]`.

    **c.2009–: ricethresher.org.** Site search renders nothing; `/section/news?page=N&per_page=20` paginates the whole archive by date (page 49 ≈ September 2021) and article slugs end in `-YYYYMMDD`, so listing pages and grepping hrefs finds an article when search engines fail. Author pages carry excerpts.

    **The OCR route.** Search and hits are blocked on digital.library.unt.edu too, so only page-by-page OCR works there. Pages without OCR text (about 300 of them in 1956–94) can't be searched, and OCR misses words, so "not found" means "not found in the OCR".

## The Woodson Research Center

Fondren Library's archive. Ask for the **Wiess College Records, UA 0079**: Cabinet minutes and governing documents from 1950. It's the first place to look for the 1957–1993 constitutions and the pre-1991 Rules: the college's records there run to about 34 linear feet. Bring a camera.

??? info "More on the Woodson"
    It also has Dr. Bill Wilson's papers and recordings (received 2021), and is the place to look for the 1960s Magisters and the 1968 Wiess Crack. Rice's Digital Scholarship Archive (`hdl.handle.net/1911/…`) has photographs such as Wiess students pumpkin caroling in 1969.

## Rice History Corner

Melissa Kean's blog (ricehistorycorner.com), 2010–2025. The photos are good, but **the comments are the real source**: alumni from the 1960s–90s correcting each other, often quoting Thresher pages.

??? info "How to search the comments"
    The site's own search doesn't index comments, so query the WordPress.com API: `public-api.wordpress.com/rest/v1.1/sites/ricehistorycorner.com/posts/?search=…` then `/posts/<ID>/replies/?number=100&order=ASC`; add known posts by `/posts/slug:<slug>`. Recurring commenters worth following: marmer01, almadenmike (quotes Thresher PDFs with page numbers), James Medford, Walter Underwood, Richard Miller (Hanszen '75), Marty Merritt, George Webb '88, Kermit Lancaster (1970s Wiess memorabilia at lancasterteam.com/wiess). Cite as `[@rhc <date> <slug> comment by X, <date>]`.

## The O-Week books

We hold 2003, 2006–2011 (some in parts), 2014–2017 and the 2016 Owlmanac from teamwiess.com, plus 2019, 2021, 2024 and 2025 (found in October 2026). The 1994 and 1995 handbooks survive as copies on the 1997 website. Each book's glossary is extracted to `sources/glossaries/<year>.tsv`; [the series](../traditions/glossary-series.md) is built from them.

??? info "Details: which parts, and the font tricks"
    2003 (four section PDFs), 2006, 2007, 2008 (seven parts), 2009 (parts 2, 4, 5, 6), 2010, 2011, 2014, 2015, 2016 (+ Owlmanac), 2017—all from teamwiess.com via the Wayback Machine, all with text layers. The 1972 handbook survives as the architecture page. **Not held yet**: everything before 1994 in print, 1996–2002, 2004–05, 2009 parts 1/3/7, 2012–13, and 2018, 2020, 2022, 2023, 2026. The Historian's filing cabinet and the Woodson are the places to ask.

    Text-layer quirks: some books use a font whose codes are shifted by 29 (`SODFH` = "place"); `tools/fix_pdf_text.py` decodes it. The 2011 book uses two other glyph-order ciphers; the 2014 book interleaves columns.

## The Campanile

The yearbook. archive.org has only 1916–1939 and 1988. Rice's own repository (repository.rice.edu / scholarship.rice.edu) blocks automated access, so use a browser. The college holds scans of the War Pig pages 1984–2012 in `artifacts/campanile-pages/`, with an index of print and PDF page numbers. The 1960s volumes are the place to look for the Academic Bowl game and Jock Row.

## Other people's archives

- Machado and Silvetti and Kirksey (architects of New Wiess) keep project pages with plans and photographs.
- Colin Delany '91's photographs of the emptied Old Wiess (August 2002) are still live at edesigns-graphics.com/wiess after 24 years, and mirrored.
- Hanszen's traditions page tells the rivalry from the other side.
- Mark Maxham's War Pig Design Document (1998) is live at interstice.com/~max/pig.html and maxham.com/mark/pig.html.
- Rice Magazine, "Traditions: Wiess College" (Nov 2016).

## What's blocked from where

web.archive.org, texashistory.unt.edu and scholarship.rice.edu refuse connections from cloud build environments; they work from a personal machine and a browser. repository.rice.edu blocks every automated route. Plan digs accordingly: the browser is the instrument of record for the Portal, the Wayback Machine the bulk source, and a personal machine the place to run both.

??? info "The corpus layout (working corpus, `~/projects/wiess-archive/`)"
    ```
    <site>/index.tsv                      timestamp, url, status, mimetype, digest, local path
    <site>/cdx/*.tsv                      raw CDX lists
    <site>/mirror/<host>/<path>/<timestamp>__<file>    raw captures—the path IS the Wayback URL
    riceinfo.rice.edu-wiess/text/<section>__<page>.html__<timestamp>.md    text of each page version
    teamwiess.com/oweek-books/{*.pdf, text/, text-raw/, manifest.tsv}
    ricehistorycorner.com/{posts/<date>_<slug>.md, index.tsv, commenters.tsv}
    homepage-history/{index.tsv, shots/, cdx/}        409 homepage versions, screenshots
    wiess-governance/                                   the governance git repo
    artifacts/{campanile-pages, photos, warpigtedtalk, class-council-06-historian}
    offsite/{edesigns…, machado-silvetti.com, portfolio-cloudfront, rice-subdomains, wiesscooks.rice.edu}
    ```

    `tools/cite.py <path>` turns any corpus path into its citation; `fetch_generic.sh <name> <cdx-query>` rebuilds any mirror from the Wayback Machine. The manifests in this repository (`sources/manifests/`) make the whole corpus reproducible.
