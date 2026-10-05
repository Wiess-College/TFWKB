"""Fill the <!-- GALLERY:key --> placeholders on Record pages, write docs/gallery/index.md and
update docs/assets/photos/manifest.tsv from tools/photo_placements.py.

Idempotent: a filled gallery is wrapped in <!-- GALLERY:key --> ... <!-- /GALLERY:key --> and is
regenerated in place on every run.
"""
import html
import os
import re
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from photo_placements import P, PAGES  # noqa: E402

DOCS = os.path.join(ROOT, "docs")
PHOTOS = "assets/photos/"


def attr(s: str) -> str:
    return html.escape(s, quote=True)


def figure(entry, page_rel, gallery, thumb=False, link=None):
    f, _key, caption, credit_plain, credit_cite, date, _topic = entry
    src = PHOTOS + f
    if thumb:
        d, n = os.path.split(f)
        cand = PHOTOS + d + "/thumbs/" + n
        if os.path.exists(os.path.join(DOCS, cand)):
            src = cand
    rel = os.path.relpath(src, os.path.dirname(page_rel))
    alt = re.sub(r"[\[\]]", "", caption)
    desc = credit_plain + (f" · {date}" if date else "")
    cap = caption
    if credit_cite:
        cap += f" <small>{html.escape(credit_plain)} {credit_cite}</small>"
    else:
        cap += f" <small>{html.escape(credit_plain)}</small>"
    if link:
        cap += f" <small>On {link}.</small>"
    return (
        '<figure markdown="span">\n'
        f'  ![{alt}]({rel}){{ loading=lazy data-title="{attr(caption)}" '
        f'data-description="{attr(desc)}" data-gallery="{gallery}" }}\n'
        f"  <figcaption>{cap}</figcaption>\n"
        "</figure>\n"
    )


def block(entries, page_rel, gallery, **kw):
    out = ['<div class="grid photo-grid" markdown>\n']
    for e in entries:
        out.append(figure(e, page_rel, gallery, **kw))
    out.append("</div>\n")
    return "\n".join(out)


def main():
    by_key = OrderedDict((k, []) for k in PAGES)
    for e in P:
        if not os.path.exists(os.path.join(DOCS, PHOTOS + e[0])):
            sys.exit(f"missing photo: {e[0]}")
        by_key[e[1]].append(e)

    # 1. pages
    for key, (page_rel, _label) in PAGES.items():
        path = os.path.join(DOCS, page_rel)
        t = open(path, encoding="utf-8").read()
        content = block(by_key[key], page_rel, key)
        filled = f"<!-- GALLERY:{key} -->\n{content}<!-- /GALLERY:{key} -->"
        pat = re.compile(rf"<!-- GALLERY:{key} -->(?:.*?<!-- /GALLERY:{key} -->)?", re.S)
        if not pat.search(t):
            sys.exit(f"no placeholder for {key} in {page_rel}")
        t = pat.sub(lambda m: filled, t, count=1)
        open(path, "w", encoding="utf-8").write(t)

    # 2. gallery index
    g_rel = "gallery/index.md"
    os.makedirs(os.path.join(DOCS, "gallery"), exist_ok=True)
    parts = [
        "---\ntitle: Photographs\nstatus: draft\nlast_reviewed: 2026-10-05\nreviewed_by: unreviewed\n---\n\n"
        "# Photographs\n\n"
        f"Every photograph and graphic placed on a Record page, {len(P)} in all, grouped by the page it illustrates. "
        "Click any image to enlarge it; the caption under each says what it shows, where it came from and how we know "
        "the date. Where the source is a capture of a college website, the citation opens that capture in the Wayback "
        "Machine. Where a caption says *source not recorded*, the image reached the Historian's collection without a "
        "note of where it was first published, and its date comes from its file name or its content; treat those "
        "dates as provisional.\n\n"
        "**Preservation.** These are web-size copies (at most 1,600 pixels on the long side) with thumbnails. The "
        "originals, at full size, are kept by the Historian, and an Internet Archive collection of them is planned so "
        "that every photograph here has a permanent public home that does not depend on this site. "
        "The list of files, with sizes, checksums and these captions, is `docs/assets/photos/manifest.tsv`. "
        "Photographs are chosen to show places and customs; students are not named in captions unless the "
        "[Core Team](../people/core-team.md) table or a public record names them as office-holders, and nothing "
        "revealing from Night of Decadence is shown. See [Rights](../contributing/rights.md).\n\n"
    ]
    for key, (page_rel, label) in PAGES.items():
        link_rel = os.path.relpath(page_rel, "gallery")
        parts.append(f"## {label}\n\nOn [{label}]({link_rel}#photographs).\n\n")
        parts.append(block(by_key[key], g_rel, "index-" + key, thumb=True))
        parts.append("\n")
    parts.append('<div class="reviewed" markdown>Last reviewed 2026-10-05 by unreviewed · [Edit this page](#)</div>\n')
    open(os.path.join(DOCS, g_rel), "w", encoding="utf-8").write("".join(parts))

    # 3. manifest
    mpath = os.path.join(DOCS, PHOTOS, "manifest.tsv")
    with open(mpath, encoding="utf-8") as fh:
        rows = [ln.rstrip("\n").split("\t") for ln in fh if ln.strip()]
    head = rows[0]
    idx = {h: i for i, h in enumerate(head)}
    info = {"docs/" + PHOTOS + e[0]: e for e in P}
    seen = set()
    for r in rows[1:]:
        e = info.get(r[idx["web_path"]])
        if not e:
            continue
        seen.add(r[idx["web_path"]])
        page_rel = PAGES[e[1]][0]
        cite = re.findall(r"\[@([^\]]+)\]", e[4])
        credit = e[3] + ((" — " + "; ".join("@" + c for c in cite)) if cite else "")
        r[idx["caption"]] = e[2]
        r[idx["credit"]] = credit
        r[idx["date"]] = e[5]
        r[idx["topic"]] = f"{e[6]} ({page_rel})"
    missing = set(info) - seen
    if missing:
        sys.exit(f"not in manifest: {sorted(missing)}")
    for r in rows:
        if any("\t" in c or "\n" in c for c in r):
            sys.exit("tab or newline inside a manifest field")
    with open(mpath, "w", encoding="utf-8") as fh:
        fh.write("".join("\t".join(r) + "\n" for r in rows))
    print(f"placed {len(P)} photos on {len(PAGES)} pages; manifest rows updated: {len(seen)}")


if __name__ == "__main__":
    main()
