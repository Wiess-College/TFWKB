#!/usr/bin/env bash
# Set up this repository on a new machine (macOS or Linux). Run it from anywhere:
#
#     ./setup.sh
#
# It does four things, and is safe to run again:
#
#   1. checks for git and Python 3.12 or newer, and stops if either is missing
#   2. makes a virtual environment in .venv/ and installs requirements.txt into it (what the site needs)
#   3. asks where your research corpus and governance checkout are, and writes tfwkb.config.yml
#      (it offers to keep the file if there is one already)
#   4. lists the optional tools that are missing, without installing them, and builds the site once
#
# It installs nothing outside .venv/ and changes no file but tfwkb.config.yml. When it is not run in a
# terminal (stdin is not a terminal), it takes every default instead of asking.

set -u

REPOSITORY_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPOSITORY_ROOT" || exit 1
CONFIG_FILE="tfwkb.config.yml"
VENV_PYTHON=".venv/bin/python"

say() { printf '%s\n' "$*"; }
heading() { printf '\n== %s\n' "$*"; }
stop() { printf 'setup.sh: %s\n' "$*" >&2; exit 1; }

# ask "Question" "default" -> prints the answer, or the default for an empty answer or no terminal.
ask() {
    local answer=""
    if [ -t 0 ]; then
        read -r -p "$1 [$2]: " answer
    fi
    printf '%s' "${answer:-$2}"
}

# Expand a leading "~" the way the shell would.
expand_home() {
    case "$1" in
        "~") printf '%s' "$HOME" ;;
        "~/"*) printf '%s' "$HOME/${1#\~/}" ;;
        *) printf '%s' "$1" ;;
    esac
}

heading "1. git and Python"
command -v git >/dev/null 2>&1 || stop "git is not installed. Install it (macOS: xcode-select --install) and run this again."

PYTHON=""
for candidate in python3.14 python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
[ -n "$PYTHON" ] || stop "Python 3.12 or newer is needed. Install it (macOS: brew install python; Linux: your package manager) and run this again."
say "Using $("$PYTHON" --version) ($(command -v "$PYTHON"))"

heading "2. Virtual environment (.venv/)"
if [ -x "$VENV_PYTHON" ]; then
    say "Found .venv/; updating its packages."
else
    "$PYTHON" -m venv .venv || stop "could not make .venv/. On Debian or Ubuntu, install python3-venv first."
fi
"$VENV_PYTHON" -m pip install --quiet --upgrade pip || stop "pip could not upgrade itself in .venv/."
"$VENV_PYTHON" -m pip install --quiet -r requirements.txt || stop "pip could not install requirements.txt; see the messages above."
say "Installed requirements.txt into .venv/."

heading "3. Where your folders are ($CONFIG_FILE)"
write_config=yes
if [ -f "$CONFIG_FILE" ]; then
    say "$CONFIG_FILE already says:"
    sed 's/^/    /' "$CONFIG_FILE"
    case "$(ask "Keep it?" "y")" in
        [nN]*) write_config=yes ;;
        *) write_config=no ;;
    esac
fi

if [ "$write_config" = yes ]; then
    say "Paths can be absolute, start with ~, or be relative to this repository."
    say "The site builds without them; only the tools in tools/ use them."

    while :; do
        corpus="$(ask "Research corpus folder (wiess-archive)" "../wiess-archive")"
        if [ -d "$(expand_home "$corpus")" ]; then
            for expected in teamwiess.com historian-collection riceinfo.rice.edu-wiess; do
                [ -d "$(expand_home "$corpus")/$expected" ] \
                    || say "  Note: $corpus has no $expected/ folder, which tools/glossary-extraction/ reads."
            done
            break
        fi
        say "  $corpus is not a folder."
        case "$(ask "Use it anyway (you can fix $CONFIG_FILE later)?" "n")" in
            [yY]*) break ;;
        esac
        [ -t 0 ] || break
    done

    governance_default=""
    [ -d "$(expand_home "$corpus")/wiess-governance/.git" ] && governance_default="$corpus/wiess-governance"
    while :; do
        governance="$(ask "Governance checkout folder (leave empty if none)" "$governance_default")"
        if [ -z "$governance" ] || [ -d "$(expand_home "$governance")/.git" ]; then
            break
        fi
        say "  $governance is not a git checkout (no .git folder)."
        case "$(ask "Use it anyway?" "n")" in
            [yY]*) break ;;
        esac
        [ -t 0 ] || { governance=""; break; }
    done

    "$VENV_PYTHON" - "$CONFIG_FILE" "$corpus" "$governance" <<'PYTHON' || stop "could not write $CONFIG_FILE."
import sys
import yaml

config_file, corpus, governance_repo = sys.argv[1:]
with open(config_file, "w", encoding="utf-8") as config:
    config.write("# Written by setup.sh; see tfwkb.config.example.yml. Not committed.\n")
    yaml.safe_dump({"corpus": corpus, "governance_repo": governance_repo or None}, config, sort_keys=False)
PYTHON
    say "Wrote $CONFIG_FILE."
fi

heading "4. Optional tools"
missing=0
report_missing() { say "  missing: $1"; say "      $2"; missing=$((missing + 1)); }

for linter in ruff pylint; do
    [ -x ".venv/bin/$linter" ] || command -v "$linter" >/dev/null 2>&1 \
        || report_missing "$linter (lints tools/ and hooks/, as CI does)" "$VENV_PYTHON -m pip install -r requirements-dev.txt"
done
"$VENV_PYTHON" -c 'import fitz' 2>/dev/null \
    || report_missing "pymupdf (tools/fix_pdf_fonts.py)" "$VENV_PYTHON -m pip install -r requirements-dev.txt"
"$VENV_PYTHON" -c 'import fontTools' 2>/dev/null \
    || report_missing "fonttools (tools/fix_pdf_fonts.py)" "$VENV_PYTHON -m pip install -r requirements-dev.txt"
command -v pdftotext >/dev/null 2>&1 \
    || report_missing "pdftotext (text layers of new O-Week books)" "macOS: brew install poppler; Linux: install poppler-utils"
command -v gh >/dev/null 2>&1 \
    || report_missing "gh (tools/file_issues.sh and tools/tsv_to_issues.sh file GitHub issues)" "macOS: brew install gh; Linux: https://github.com/cli/cli#installation"
[ "$missing" -eq 0 ] && say "  All found."

heading "Building the site once (mkdocs build --strict)"
if .venv/bin/mkdocs build --strict --quiet; then
    say "Built into site/."
else
    say "The build failed; the messages above say which page or citation. Setup itself is done."
fi

cat <<'NEXT'

== Next steps

    source .venv/bin/activate     # once per terminal; your prompt shows (.venv)
    mkdocs serve                  # preview at http://127.0.0.1:8000, reloading as you edit

Run ./setup.sh again after requirements.txt changes, or to change your folders.
NEXT
