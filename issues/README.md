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

## Open questions list

`open-questions.tsv` is a research to-do list gathered from the "Arguments & loose ends" boxes on the site's
pages (plus the open leads in `docs/sources/wanted.md` and `docs/sources/search-log.md`), with questions that
appear on several pages merged into one row. It is a list of things to find, not a list of failures: the files
gathered so far are a small part of what exists, and the Woodson alone holds about 34 linear feet of Wiess
papers. Stories already drafted in `drafts/` are not repeated; rows point to the draft instead.

Columns: `id`, `keep` (empty until vetted), `title`, `type` (question, disagreement or lead), `pages`
(docs-relative, `; `-separated), `detail`, `cites` (citation keys as on the page), `where_to_look`, `labels`,
`priority` (high, medium, low) and `merged_from` (every page and note folded into the row).

1. Open `open-questions.tsv` in a spreadsheet (tab-separated, UTF-8) and mark `keep` with `y` for rows worth
   an issue, `n` for the rest. Edit titles or details freely; save as tab-separated text.
2. Dry run, to see the labels and each issue body without changing anything:

   ```sh
   tools/tsv_to_issues.sh -n
   ```

3. File them:

   ```sh
   tools/tsv_to_issues.sh
   ```

Only `keep=y` rows are filed. The script creates any missing labels, and skips a row whose title already exists
as an open issue, so it is safe to run again after marking more rows.

## Closing one

When a written source turns up, add it to `sources/bibliography/`, restore the claim on the page with the
citation, and close the issue with a link to the pull request. If a contributor tells the story in the
Commons, that is testimony `[T]`, which a page may cite once the contributor is named and dated.
