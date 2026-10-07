---
title: Sources
---

# Sources

This section explains where the evidence behind this site lives and how to find more. This site holds the short version, not the evidence. The evidence lives in places that will outlast us: the Wayback Machine, the Portal to Texas History, the Woodson Research Center, the college's own artifacts. Every claim here links to one of them.

!!! abstract "TL;DR"
    - Want to check a fact? Click its citation, or look it up in the [bibliography](bibliography.md).
    - Want to find something new? Start with the [search log](search-log.md) and the [wanted list](wanted.md).

## What's here

- **[Annotated bibliography](bibliography.md)**: every source the pages cite, what it is, where it lives, what it's good for, and its limits. Built automatically from `sources/bibliography/*.yaml`; the keys there are the keys the pages cite.
- **[Where to look](where-to-look.md)**: which archive holds what, and the tricks that worked.
- **[Evidence classes](evidence-classes.md)**: what the P / R / T tags mean.
- **[Search log](search-log.md)**: what's been searched, where, what turned up, and the leads not yet followed.
- **[Wanted](wanted.md)**: documents we know exist and still need.

??? info "Working copies: the files behind the site"
    Contributors read the evidence in their own working copies: files they downloaded from the archives above, kept on their own machines. The repository keeps only what they found. When you have a new source, run the matching tool in `tools/` on it and commit the result (a bibliography entry, a glossary table, a photo caption); the file itself stays with you. Nothing on this site depends on anyone's working copy, because every citation links to a public archive.

    The 2026 working copy held about 2 GB in 6,400 files: archived web captures (the first Wiess website 1998–2002, teamwiess.com 2001–2021, wiess.rice.edu 2014–), the O-Week books 2003–2017 with their text, the Rice History Corner crawl with 1,164 comments, 409 homepage screenshots, the governing documents, and the college's own artifacts. `sources/manifests/` records where each of those files came from, and `tools/fetch_working_copy.py` fetches the ones archive.org holds into a working copy of your own. See [Where to look](where-to-look.md) for a layout the tools understand.
