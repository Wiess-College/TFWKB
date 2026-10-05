#!/usr/bin/env python3
"""Turn a corpus path into a citation, or a citation into a URL.

    python3 tools/cite.py teamwiess.com/mirror/teamwiess.com/traditions/20140711230531__index.html
      → [@wb 20140711230531 http://teamwiess.com/traditions/index.html]
    python3 tools/cite.py riceinfo.rice.edu-wiess/text/traditions__ubangee.html__20020107020729.md
      → [@wb 20020107020729 http://riceinfo.rice.edu/projects/colleges/wiess/traditions/ubangee.html]
    python3 tools/cite.py --url "[@wb 20020107020729 http://riceinfo.rice.edu/...]"
      → https://web.archive.org/web/20020107020729/http://riceinfo.rice.edu/...
    python3 tools/cite.py --url "[@oweek-2006 p.84]"       (looks the key up in sources/bibliography/)

The corpus layout is <site>/mirror/<host>/<path>/<timestamp>__<file>; riceinfo text files are
<section>__<page>.html__<timestamp>.md under riceinfo.rice.edu-wiess/text/ (or rice.edu-projects-wiess/text/).
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RICEINFO_BASE = {"riceinfo.rice.edu-wiess": "http://riceinfo.rice.edu/projects/colleges/wiess",
                 "rice.edu-projects-wiess": "http://www.rice.edu/projects/colleges/wiess"}


def path_to_cite(p: str) -> str:
    p = p.replace("\\", "/")
    p = re.sub(r"^.*?/corpus/", "", p)
    p = re.sub(r"^.*?wiess-archive/", "", p)
    m = re.match(r"^(?P<site>[^/]+)/mirror/(?P<host>[^/]+)/(?P<rest>.*?)(?P<ts>\d{14})__(?P<file>[^/]+)$", p)
    if m:
        rest = m.group("rest")
        url = f"http://{m.group('host')}/{rest}{m.group('file')}"
        return f"[@wb {m.group('ts')} {url}]"
    m = re.match(r"^(?P<site>riceinfo\.rice\.edu-wiess|rice\.edu-projects-wiess)/text/(?P<page>.+?)__(?P<ts>\d{14})\.md$", p)
    if m:
        page = m.group("page").replace("__", "/")
        return f"[@wb {m.group('ts')} {RICEINFO_BASE[m.group('site')]}/{page}]"
    m = re.match(r"^teamwiess\.com/oweek-books/(?:text(?:-raw)?/)?(\d{4})-oweek", p)
    if m:
        return f"[@oweek-{m.group(1)} p.N]"
    m = re.match(r"^ricehistorycorner\.com/posts/(\d{4})-(\d{2})-(\d{2})_(.+?)\.md$", p)
    if m:
        y, mo, d, slug = m.groups()
        return f"[@rhc {y}-{mo}-{d} {slug}]  → https://ricehistorycorner.com/{y}/{mo}/{d}/{slug}/"
    return f"(no rule for {p})"


def cite_to_url(c: str) -> str:
    c = c.strip().strip("[]")
    if c.startswith("@wb "):
        _, ts, url = c.split(None, 2)[:3]
        return f"https://web.archive.org/web/{ts}/{url.split()[0]}"
    if c.startswith("@portal "):
        parts = c.split()
        ark = parts[1]
        pm = re.search(r"p\.?\s*(\d+)", c)
        return f"https://texashistory.unt.edu/ark:/67531/{ark}/" + (f"m1/{pm.group(1)}/" if pm else "")
    key = c.split()[0].lstrip("@")
    import yaml  # PyYAML ships with mkdocs
    for f in glob.glob(os.path.join(ROOT, "sources", "bibliography", "*.yaml")):
        for e in yaml.safe_load(open(f)) or []:
            if e.get("key") == key:
                url = e.get("url") or "(no url; local: %s)" % e.get("local")
                pm = re.search(r"p\.?\s*(\d+)", c)
                if pm and str(url).lower().endswith(".pdf"):
                    url += f"#page={pm.group(1)}"
                return url
    return f"(unknown key {key})"


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    if args[0] == "--url":
        print(cite_to_url(" ".join(args[1:])))
    else:
        for a in args:
            print(path_to_cite(a))
