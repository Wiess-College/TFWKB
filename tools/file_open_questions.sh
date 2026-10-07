#!/usr/bin/env bash
# File the vetted rows of issues/open-questions.tsv as GitHub issues.
#
#   tools/file_open_questions.sh -n          dry run: print what would be done, change nothing
#   tools/file_open_questions.sh             create missing labels, then one issue per row with keep=y
#   tools/file_open_questions.sh -n FILE     use another TSV with the same columns
#
# Only rows whose `keep` column is y/Y/yes are filed. The issue body is built from the row:
# detail, then "Pages:" (links to the published site), "Sources:" (the cite keys, verbatim),
# "Where to look:" and "Merged from:". Labels come from the `labels` column ("; "-separated).
# A row whose exact title already exists as an open issue is skipped, so the script is safe
# to run again after marking more rows. Requires python3 and the GitHub CLI (gh), authenticated
# with write access to the repo (the dry run works without gh).
set -euo pipefail

REPO="Wiess-College/TFWKB"
SITE="https://wiess-college.github.io/TFWKB"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY=0

usage() { echo "usage: $0 [-n] [TSV]   (-n = dry run; default TSV: issues/open-questions.tsv)" >&2; exit 2; }
while getopts ":nh" opt; do
  case "$opt" in
    n) DRY=1 ;;
    h|*) usage ;;
  esac
done
shift $((OPTIND - 1))
TSV="${1:-$ROOT/issues/open-questions.tsv}"
[[ -f "$TSV" ]] || { echo "no such file: $TSV" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 not found" >&2; exit 1; }

run() {  # print in dry-run mode, execute otherwise
  if [[ $DRY -eq 1 ]]; then printf 'DRY-RUN:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

HAVE_GH=0
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then HAVE_GH=1; fi
if [[ $DRY -eq 0 && $HAVE_GH -eq 0 ]]; then
  echo "gh (GitHub CLI) not found or not authenticated; run 'gh auth login' or use -n" >&2; exit 1
fi

tmpdir="$(mktemp -d)"; trap 'rm -rf "$tmpdir"' EXIT

# Parse the TSV with python: one body file per kept row, plus a manifest of
# id <TAB> title <TAB> comma-separated labels <TAB> body file.
python3 - "$TSV" "$tmpdir" "$SITE" <<'PY'
import csv, os, sys
tsv, out, site = sys.argv[1:4]
need = ["id", "keep", "title", "type", "pages", "detail", "cites",
        "where_to_look", "labels", "priority", "merged_from"]

def split(s):
    return [x.strip() for x in (s or "").split("; ") if x.strip()]

def page_url(p):
    p = p.strip().lstrip("/")
    if p.startswith("docs/"):
        p = p[5:]
    stem = p[:-3] if p.endswith(".md") else p
    if stem == "index":
        stem = ""
    elif stem.endswith("/index"):
        stem = stem[: -len("/index")]
    return f"{site}/{stem}/" if stem else f"{site}/"

with open(tsv, encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f, delimiter="\t"))  # default quoting: also reads spreadsheet-saved TSV
missing = [c for c in need if rows and c not in rows[0]]
if missing:
    sys.exit(f"TSV is missing columns: {', '.join(missing)}")

kept = 0
with open(os.path.join(out, "manifest.tsv"), "w", encoding="utf-8") as man:
    for r in rows:
        if (r.get("keep") or "").strip().lower() not in ("y", "yes"):
            continue
        rid, title = r["id"].strip(), r["title"].strip()
        if not title:
            print(f"SKIP {rid}: empty title", file=sys.stderr)
            continue
        labels = split(r["labels"])
        if r["type"].strip() == "disagreement" and "disagreement" not in labels:
            labels.append("disagreement")
        parts = [r["detail"].strip(), ""]
        pages = split(r["pages"])
        parts.append("**Pages:**")
        parts += [f"- [{p}]({page_url(p)}) (`docs/{p}`)" for p in pages] or ["- (no page yet)"]
        cites = split(r["cites"])
        if cites:
            parts += ["", "**Sources:**"] + [f"- `{c}`" for c in cites]
        if r["where_to_look"].strip():
            parts += ["", "**Where to look:**"] + [f"- {w}" for w in split(r["where_to_look"])]
        if r["merged_from"].strip():
            parts += ["", "**Merged from:**"] + [f"- {m}" for m in split(r["merged_from"])]
        parts += ["", f"_From `issues/open-questions.tsv` row {rid} (type: {r['type'].strip()}, "
                      f"priority: {r['priority'].strip()})._"]
        body = os.path.join(out, f"{rid}.md")
        with open(body, "w", encoding="utf-8") as b:
            b.write("\n".join(parts) + "\n")
        man.write("\t".join([rid, title, ",".join(labels), body]) + "\n")
        kept += 1
print(f"{kept} row(s) marked keep=y in {tsv}", file=sys.stderr)
PY

manifest="$tmpdir/manifest.tsv"
if [[ ! -s "$manifest" ]]; then echo "Nothing to file: no rows with keep=y."; exit 0; fi

# Labels first. --force updates color/description if the label exists, so this is safe to repeat.
label_color() {
  case "$1" in
    needs-source) echo D93F0B ;; disagreement) echo B60205 ;; oral-history) echo 5319E7 ;;
    archives) echo 795548 ;; thresher) echo 0E8A16 ;; web-archive) echo 1D76DB ;;
    photos) echo FBCA04 ;; people) echo C5DEF5 ;; places) echo BFD4F2 ;;
    traditions) echo DAA520 ;; governance) echo 006B75 ;; dates) echo F9D0C4 ;; *) echo EDEDED ;;
  esac
}
label_desc() {
  case "$1" in
    needs-source) echo "A claim that needs a written source" ;;
    disagreement) echo "Sources disagree; find the deciding evidence" ;;
    oral-history) echo "From an oral account; to be confirmed" ;;
    archives) echo "Answer likely in the Woodson or other archives" ;;
    thresher) echo "Answer likely in the Rice Thresher" ;;
    web-archive) echo "Answer likely in web captures" ;;
    photos) echo "Photographs wanted" ;;
    people) echo "About people and offices" ;;
    places) echo "About buildings and spaces" ;;
    traditions) echo "About a tradition" ;;
    governance) echo "About the Constitution, Cabinet, Court or Rules" ;;
    dates) echo "A date to pin down" ;;
    *) echo "Open question" ;;
  esac
}
cut -f3 "$manifest" | tr ',' '\n' | sed '/^$/d' | sort -u > "$tmpdir/labels"
while IFS= read -r l; do
  run gh label create "$l" --repo "$REPO" --force --color "$(label_color "$l")" --description "$(label_desc "$l")"
done < "$tmpdir/labels"

json_str() { printf '%s' "$1" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))'; }

filed=0; skipped=0
while IFS=$'\t' read -r rid title labels body; do
  # Duplicate guard: an open issue with exactly this title.
  if [[ $HAVE_GH -eq 1 ]]; then
    q="${title//\"/}"   # inner quotes would break GitHub's search syntax; the jq filter still matches exactly
    existing="$(gh issue list --repo "$REPO" --state open --limit 200 --search "$q in:title" \
                --json number,title --jq ".[] | select(.title == $(json_str "$title")) | .number" | head -n1 || true)"
    if [[ -n "$existing" ]]; then
      echo "EXISTS #$existing: $rid $title (skipped)"; skipped=$((skipped+1)); continue
    fi
  elif [[ $DRY -eq 1 ]]; then
    echo "NOTE: gh not available/authenticated; open-issue duplicate check not run for $rid"
  fi
  echo "FILE $rid: $title  [labels: $labels]"
  if [[ $DRY -eq 1 ]]; then sed 's/^/    | /' "$body"; fi
  run gh issue create --repo "$REPO" --title "$title" --label "$labels" --body-file "$body"
  filed=$((filed+1))
done < "$manifest"

echo "Done: $filed to file, $skipped skipped$([[ $DRY -eq 1 ]] && echo ' (dry run; nothing changed)')."
