---
title: Sources
---

# Sources

Team Familypedia holds condensed knowledge, not copies of the evidence. The evidence lives in places that will outlast this site — the Wayback Machine, the Portal to Texas History, the Woodson Research Center, the college's own artifacts — and every claim here points at one of them with a link that works without us.

- **[Annotated bibliography](bibliography.md)** — every source the pages cite, with what it is, where it lives, what it is good for, and its gaps. Generated at build time from `sources/bibliography/*.yaml`; the keys in the YAML are the keys the pages cite.
- **[Where to look](where-to-look.md)** — the finding aid: which archive holds what, how to query it, and the recipes that worked.
- **[Evidence classes](evidence-classes.md)** — what the P / R / T tags mean and how to weigh them.
- **[Search log](search-log.md)** — what has been searched, where, with what result, and the leads not yet followed. The place to start if you want to find something new.

## The corpus

Behind the site is a working corpus on the Historian's machine: about 2 GB and 6,400 files of archived web captures (the first Wiess website 1998–2002, teamwiess.com 2001–2021, wiess.rice.edu 2014–), the O-Week books 2003–2017 with their text, the Rice History Corner crawl with 1,164 comments, 409 homepage screenshots, the governing documents, and the college's own artifacts. It is not in this repository; it is reproducible from the manifests and fetch scripts that are (`sources/manifests/`, `tools/`), because every file's path encodes the Wayback capture it came from. See [Where to look](where-to-look.md) for the layout.
