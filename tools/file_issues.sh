#!/usr/bin/env bash
# File the "Story to source" issue drafts in issues/drafts/ as GitHub issues.
#
#   tools/file_issues.sh        create the labels, file every draft, move each filed draft to issues/filed/
#   tools/file_issues.sh -n     dry run: print what would be done, change nothing
#
# Each draft is Markdown with YAML front matter (title, labels, page); the body after the front matter
# becomes the issue body. The script is idempotent: a draft already in issues/filed/ is never seen again,
# and a draft whose exact title already exists as an issue (open or closed) is moved to filed/ without
# creating a duplicate. Requires the GitHub CLI (gh), authenticated with write access to the repo.
set -euo pipefail

REPO="Wiess-College/TFWKB"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRAFTS="$ROOT/issues/drafts"
FILED="$ROOT/issues/filed"
DRY=0

usage() { echo "usage: $0 [-n]   (-n = dry run)" >&2; exit 2; }
while getopts ":nh" opt; do
  case "$opt" in
    n) DRY=1 ;;
    h|*) usage ;;
  esac
done

run() {  # print in dry-run mode, execute otherwise
  if [[ $DRY -eq 1 ]]; then printf 'DRY-RUN:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

command -v gh >/dev/null 2>&1 || { echo "gh (GitHub CLI) not found" >&2; exit 1; }
[[ -d "$DRAFTS" ]] || { echo "no drafts directory: $DRAFTS" >&2; exit 1; }
mkdir -p "$FILED"

shopt -s nullglob
drafts=("$DRAFTS"/*.md)
if [[ ${#drafts[@]} -eq 0 ]]; then echo "No drafts to file."; exit 0; fi

# Labels first (--force updates color/description if the label exists, so this is safe to repeat).
run gh label create needs-source  --repo "$REPO" --force --color D93F0B --description "A claim that needs a written source"
run gh label create oral-history  --repo "$REPO" --force --color 5319E7 --description "From an oral account; to be confirmed"

tmpdir="$(mktemp -d)"; trap 'rm -rf "$tmpdir"' EXIT

filed=0; skipped=0
for f in "${drafts[@]}"; do
  name="$(basename "$f")"
  # Front matter must open on line 1 with '---'.
  if [[ "$(head -n1 "$f")" != "---" ]]; then echo "SKIP $name: no front matter" >&2; skipped=$((skipped+1)); continue; fi
  fm="$(awk 'NR==1{next} /^---[[:space:]]*$/{exit} {print}' "$f")"
  title="$(printf '%s\n' "$fm" | sed -n 's/^title:[[:space:]]*//p' | head -n1)"
  title="${title#\"}"; title="${title%\"}"; title="${title//\\\"/\"}"
  labels="$(printf '%s\n' "$fm" | sed -n 's/^labels:[[:space:]]*\[\(.*\)\][[:space:]]*$/\1/p' | head -n1 | tr -d ' ')"
  if [[ -z "$title" || -z "$labels" ]]; then echo "SKIP $name: missing title or labels" >&2; skipped=$((skipped+1)); continue; fi

  body="$tmpdir/$name"
  # Body = everything after the closing '---', with leading blank lines dropped.
  awk 'c>=2{print; next} /^---[[:space:]]*$/{c++}' "$f" | sed '/./,$!d' > "$body"

  # Duplicate guard: exact title match among all issues.
  if [[ $DRY -eq 0 ]]; then
    existing="$(gh issue list --repo "$REPO" --state all --limit 500 --search "\"$title\" in:title" --json number,title \
                --jq ".[] | select(.title == $(printf '%s' "$title" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')) | .number" | head -n1)"
    if [[ -n "$existing" ]]; then
      echo "EXISTS #$existing: $title  ($name moved to filed/)"
      mv "$f" "$FILED/$name"; skipped=$((skipped+1)); continue
    fi
  fi

  echo "FILE $name: $title  [labels: $labels]"
  run gh issue create --repo "$REPO" --title "$title" --label "$labels" --body-file "$body"
  run mv "$f" "$FILED/$name"
  filed=$((filed+1))
done

echo "Done: $filed filed, $skipped skipped$([[ $DRY -eq 1 ]] && echo ' (dry run; nothing changed)')."
