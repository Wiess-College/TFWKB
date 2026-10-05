---
title: Decisions
status: draft
last_reviewed: 2026-10-04
reviewed_by: unreviewed
---

# Decisions

A decision record is a short, dated page written when the college decides something that changes how it works — moving a party, retiring a tradition, rewriting an office, renaming a building — by the people who made the decision, at the time they made it. It is the one kind of page on this site that is meant to be written *before* the history, not reconstructed from it afterwards. Most of what this site struggles to date (when Freshman Waiting ended, when Jamfest stopped, when the Chief Justice became directly elected, what the fall-2021 hate-speech clause said) would be a one-line lookup if a decision record had been written at the time.

## Why the college keeps them

The constitutions have required minutes since 1993 and the publication of Court abstracts since the same year, and almost none of either survives online [@constitution-1993 Bylaws Art. II §6; Art. V §9]. The 2026 Constitution asks every Cabinet member "to update and pass on all relevant documents to their successor" and the Parliamentarian to "Ensure that any amendments to the Constitution and the Bylaws passed by Cabinet are recorded" [@constitution-2026 Art. IV §9; Art. VI §4 (1)]. A decision record is the lightest way of meeting that duty for the decisions that matter: it is public, it is permanent, and it carries its own evidence.

The record is also the only place where *why* survives. Minutes say what passed; a decision record says what the alternatives were and what the college chose to keep. When the pig balloon lost at Beer Bike 2004 went unreplaced for eight years, or the 2014 O-Week coordinators dropped the "lesser college" Hanszen entry from the glossary, no one wrote down the reasoning, and the site can only report the outcome [@thresher-2004-03-26] [@oweek-2006 p.84] [@oweek-2014 p.105].

## The shape of a record

The format follows the "architecture decision record" used in software projects, adapted for a college. Every record has the same headings, so that a reader in 2036 knows where to look:

| Heading | What goes there |
|---|---|
| **Status** | proposed · decided · superseded by *(link)* |
| **Date** | the date of the vote or decision, ISO format |
| **Context** | what prompted the decision: the problem, the constraint, the complaint, the opportunity. Cite the Cabinet minutes, the Thresher, the survey. |
| **Decision** | what was decided, in one or two sentences, in the words of the motion if there was one |
| **Who decided** | the body (Cabinet, Court, a College vote, the Magisters, Head Fellows, a committee) and the vote if recorded; names only of officers acting in their public roles |
| **Consequences** | what changes as a result — dates, money, duties, the text of any amendment |
| **What was preserved** | the parts of the tradition, office or practice that the decision deliberately kept, and why. This heading is the one that distinguishes a college's record from a software team's: traditions are the point. |
| **Sources** | the minutes, the amendment text, the announcement, with permalinks — the same citation rules as every other page |

A record is a Record page, not a Commons page: it needs citations, and it should link to the tradition or governance page it affects so that page can carry a dated row pointing back.

## How a record gets written

1. The Secretary or Parliamentarian — or whoever moved the proposal — copies the template below into `docs/decisions/<topic>-<year>.md` the week the decision is made.
2. The minutes are the first source; the record links them. If the minutes are not public, the record quotes the motion and the vote.
3. The Historian adds a dated row to the relevant [Changes](../changes/index.md) decade page and to the tradition's timeline.
4. When a later decision changes the outcome, the old record's status becomes "superseded by" with a link; nothing is deleted.

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

- [NOD 2026](nod-2026.md) — the permanent cancellation of Night of Decadence, announced 5 June 2024 (the page keeps the college's label); reconstructed from the public record, with sections still to be supplied by the people who made the decision.

<div class="reviewed" markdown>Last reviewed 2026-10-04 by unreviewed · [Edit this page](#)</div>
