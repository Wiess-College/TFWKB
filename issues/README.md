# Issue drafts: stories to source

The files in `drafts/` are **drafts of GitHub issues**, not site content. They sit outside `docs/`, so
MkDocs never builds them.

Each one records claims that were removed from the Record in October 2026 because they rested only on an
oral account shared with the maintainers, with no written source behind them. The Record states only what a
written source supports; these drafts keep the stories so that they can be confirmed (or not) and put back
with a citation. One draft covers one page or topic.

Each draft has front matter (`title`, `labels`, `page`) and a body: what the oral account says, what kind of
evidence would confirm it (an O-Week book page, a Thresher article, a GroupMe post, a dated photograph…), and
the page it belongs on.

## Filing them

```sh
tools/file_issues.sh -n   # dry run: show what would be created
tools/file_issues.sh      # create the labels, open one issue per draft, move each draft to filed/
```

The script needs the GitHub CLI (`gh`) authenticated with write access to `Wiess-College/TFWKB`. It is safe to
run more than once: filed drafts move to `filed/`, and a draft whose title already exists as an issue is moved
without creating a duplicate.

## Closing one

When a written source turns up, add it to `sources/bibliography/`, restore the claim on the page with the
citation, and close the issue with a link to the pull request. If a contributor tells the story in the
Commons, that is testimony `[T]`, which a page may cite once the contributor is named and dated.
