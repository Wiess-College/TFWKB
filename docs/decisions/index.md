---
title: Decisions
status: draft
last_reviewed: 2026-10-04
reviewed_by: unreviewed
---

# Decisions

A decision record is a short page written *when* the college decides something big, by the people who decided it. Move a party, retire a tradition, rewrite an office: write it down that week.

!!! abstract "TL;DR"
    - Many of the dates we're still hunting for would be a one-line lookup with a record written at the time: when Freshman Waiting ended, when Jamfest stopped, what the 2021 hate-speech clause said.
    - Every record uses the same headings, including **What was preserved**: the part of the tradition the college chose to keep.
    - The Constitution already asks officers to "update and pass on all relevant documents to their successor" [@constitution-2026 Art. IV §9]. This is the easy way to do it.

## Why bother

The constitutions have required Cabinet minutes and public Court abstracts since 1993. We've found very few of them online so far [@constitution-1993 Bylaws Art. II §6; Art. V §9]. The Parliamentarian is supposed to "Ensure that any amendments to the Constitution and the Bylaws passed by Cabinet are recorded" [@constitution-2026 Art. VI §4 (1)].

And minutes only say *what* passed. A record says *why*. When the pig balloon lost in 2004 went unreplaced for years, or the 2014 O-Week book dropped the "lesser college" Hanszen entry, we haven't found the reasons written down [@thresher-2004-03-26] [@oweek-2006 p.84] [@oweek-2014 p.105].

## The shape of a record

Borrowed from the "architecture decision record" software teams use, adapted for a college:

| Heading | What goes there |
|---|---|
| **Status** | proposed · decided · superseded by *(link)* |
| **Date** | the date of the vote or decision, ISO format |
| **Context** | what prompted the decision: the problem, the constraint, the complaint, the opportunity. Cite the Cabinet minutes, the Thresher, the survey. |
| **Decision** | what was decided, in one or two sentences, in the words of the motion if there was one |
| **Who decided** | the body (Cabinet, Court, a College vote, the Magisters, Head Fellows, a committee) and the vote if recorded; names only of officers acting in their public roles |
| **Consequences** | what changes as a result—dates, money, duties, the text of any amendment |
| **What was preserved** | the parts of the tradition, office or practice that the decision deliberately kept, and why. This heading is the one that distinguishes a college's record from a software team's: traditions are the point. |
| **Sources** | the minutes, the amendment text, the announcement, with permalinks—the same citation rules as every other page |

A record needs citations, like any Record page. Link it to the tradition or governance page it affects.

## How to write one

1. The Secretary or Parliamentarian (or whoever moved it) copies the template below into `docs/decisions/<topic>-<year>.md` the week of the decision.
2. Link the minutes. If they aren't public, quote the motion and the vote.
3. The Historian adds a dated row to the right [Changes](../changes/index.md) decade page and the tradition's timeline.
4. If a later decision changes things, mark the old record "superseded by" with a link. Never delete.

```markdown
---
title: <Topic> <year>
status: draft
last_reviewed: <date>
reviewed_by: <handle>
---

# <Topic> <year>

**Status:** decided · **Date:** <YYYY-MM-DD>

## Context
## Decision
## Who decided
## Consequences
## What was preserved
## Sources
```

## Records

- [NOD 2026](nod-2026.md): the permanent cancellation of Night of Decadence, announced 5 June 2024 (the page keeps the college's label). Rebuilt from the public record, with sections still to be supplied by the people who made the decision.

<div class="reviewed" markdown>Last reviewed 2026-10-04 by unreviewed · [Edit this page](#)</div>
