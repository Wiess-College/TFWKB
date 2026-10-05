#!/usr/bin/env python3
"""Check that every citation on the site still resolves.

Collects URLs from sources/bibliography/*.yaml and every [@wb ...] / [@portal ...] / [@rhc ...]
short form in docs/, HEADs each one politely (one request per second, 20 s timeout), and
reports failures. Wayback URLs are checked through the availability API so a 200 means "a
capture exists", not merely "the Wayback Machine is up".

    python3 tools/check_links.py                 # print failures
    python3 tools/check_links.py --report out.md # also write a Markdown report
Exit status 1 if anything failed. Needs network; stdlib + PyYAML only.
"""
import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "familypedia-link-check/1.0 (+https://github.com/Wiess-College/TFWKB)"
CITE_RE = re.compile(r"\[@(wb|portal|rhc)\s+([^\]]+)\]")


def wayback_ok(ts: str, url: str):
    api = f"https://archive.org/wayback/available?url={urllib.parse.quote(url, safe='')}&timestamp={ts}"
    req = urllib.request.Request(api, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    snap = data.get("archived_snapshots", {}).get("closest")
    return bool(snap and snap.get("available")), (snap or {}).get("timestamp")


def head(url: str):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        if e.code in (403, 405):  # some hosts refuse HEAD; try GET
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        return e.code


def collect():
    import yaml
    items = []  # (where, kind, url or (ts,url))
    for f in sorted(glob.glob(os.path.join(ROOT, "sources", "bibliography", "*.yaml"))):
        for e in yaml.safe_load(open(f)) or []:
            u = e.get("url")
            if u and "*" not in u:
                m = re.match(r"https://web\.archive\.org/web/(\d{4,14})(?:id_)?/(.*)$", u)
                items.append((f"bib:{e['key']}", "wb" if m else "http", (m.group(1), m.group(2)) if m else u))
            for pu in (e.get("parts") or {}).values():
                m = re.match(r"https://web\.archive\.org/web/(\d{4,14})(?:id_)?/(.*)$", pu)
                items.append((f"bib:{e['key']}", "wb" if m else "http", (m.group(1), m.group(2)) if m else pu))
    for f in sorted(glob.glob(os.path.join(ROOT, "docs", "**", "*.md"), recursive=True)):
        rel = os.path.relpath(f, ROOT)
        for m in CITE_RE.finditer(open(f, encoding="utf-8").read()):
            kind, loc = m.group(1), m.group(2).split()
            if kind == "wb" and len(loc) >= 2:
                items.append((rel, "wb", (loc[0], loc[1])))
            elif kind == "portal" and loc:
                pm = re.search(r"p\.?\s*(\d+)", m.group(2))
                items.append((rel, "http", f"https://texashistory.unt.edu/ark:/67531/{loc[0]}/" + (f"m1/{pm.group(1)}/" if pm else "")))
            elif kind == "rhc" and len(loc) >= 2 and re.match(r"\d{4}-\d{2}-\d{2}$", loc[0]):
                y, mo, d = loc[0].split("-")
                items.append((rel, "http", f"https://ricehistorycorner.com/{y}/{mo}/{d}/{loc[1]}/"))
    # dedupe
    seen, out = set(), []
    for it in items:
        k = (it[1], it[2] if isinstance(it[2], str) else tuple(it[2]))
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    items = collect()
    if args.limit:
        items = items[: args.limit]
    print(f"{len(items)} distinct links to check", file=sys.stderr)
    failures, lines = [], []
    for where, kind, target in items:
        try:
            if kind == "wb":
                ok, closest = wayback_ok(*target)
                status = f"capture {closest}" if ok else "NO CAPTURE"
            else:
                code = head(target)
                ok = code < 400
                status = str(code)
        except Exception as e:  # noqa: BLE001
            ok, status = False, f"error: {e.__class__.__name__}"
        shown = target if isinstance(target, str) else f"{target[0]} {target[1]}"
        lines.append(f"| {'ok' if ok else 'FAIL'} | {status} | `{where}` | {shown} |")
        if not ok:
            failures.append((where, shown, status))
            print(f"FAIL {status:14} {where}  {shown}")
        time.sleep(1.0)
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(f"# Link check {time.strftime('%Y-%m-%d')}\n\n{len(items)} links, {len(failures)} failures\n\n")
            fh.write("| result | status | cited in | target |\n|---|---|---|---|\n" + "\n".join(lines) + "\n")
    print(f"{len(failures)} failures of {len(items)}", file=sys.stderr)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    import urllib.parse  # noqa: E402
    main()
