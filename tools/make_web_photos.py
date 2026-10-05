#!/usr/bin/env python3
"""Make web-size copies and thumbnails of the maintainer's photo folders.

    python3 tools/make_web_photos.py <source-root> [--out docs/assets/photos]

For every image under <source-root> (jpg/jpeg/png/gif/webp), writes
  <out>/<folder-slug>/<name-slug>.jpg          long edge <= 1600 px, JPEG q82, EXIF stripped
  <out>/<folder-slug>/thumbs/<name-slug>.jpg   long edge <= 400 px
and appends a row to <out>/manifest.tsv:
  web_path  thumb_path  source_path  width  height  sha256_of_original  caption  credit  date  topic
caption/credit/date/topic start empty: fill them in, they become the gallery captions.
Re-running skips images already done (matched by the original's sha256), so it is safe to repeat.
Originals are never modified; keep them (and an Internet Archive copy) as the preservation masters.
"""
import argparse, csv, hashlib, os, re, sys
from PIL import Image, ImageOps

EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
FIELDS = ["web_path", "thumb_path", "source_path", "width", "height", "sha256", "caption", "credit", "date", "topic"]

def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "img"

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def save(img, path, edge, quality):
    im = img.copy()
    im.thumbnail((edge, edge), Image.LANCZOS)
    im.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    return im.size

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("--out", default="docs/assets/photos")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    man = os.path.join(a.out, "manifest.tsv")
    rows, done = [], set()
    if os.path.exists(man):
        with open(man, newline="") as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        done = {r["sha256"] for r in rows}
    used = {r["web_path"] for r in rows}
    n = 0
    for root, _, files in os.walk(a.src):
        for fn in sorted(files):
            base, ext = os.path.splitext(fn)
            if ext.lower() not in EXTS or fn.startswith("."):
                continue
            p = os.path.join(root, fn)
            h = sha(p)
            if h in done:
                continue
            rel_dir = os.path.relpath(root, a.src)
            folder = "-".join(slug(x) for x in rel_dir.split(os.sep)) if rel_dir != "." else "misc"
            name = slug(base)
            web = os.path.join(a.out, folder, name + ".jpg")
            k = 2
            while web in used:
                web = os.path.join(a.out, folder, f"{name}-{k}.jpg"); k += 1
            thumb = os.path.join(os.path.dirname(web), "thumbs", os.path.basename(web))
            os.makedirs(os.path.dirname(thumb), exist_ok=True)
            try:
                with Image.open(p) as im:
                    im = ImageOps.exif_transpose(im)
                    if im.mode not in ("RGB", "L"):
                        bg = Image.new("RGB", im.size, (255, 255, 255))
                        im = im.convert("RGBA"); bg.paste(im, mask=im.split()[-1]); im = bg
                    w, hgt = save(im, web, 1600, 82)
                    save(im, thumb, 400, 78)
            except Exception as e:
                print("skip", p, e, file=sys.stderr); continue
            rows.append({"web_path": web, "thumb_path": thumb, "source_path": os.path.relpath(p, a.src),
                         "width": w, "height": hgt, "sha256": h, "caption": "", "credit": "", "date": "", "topic": ""})
            used.add(web); done.add(h); n += 1
    with open(man, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t"); wr.writeheader(); wr.writerows(rows)
    print(f"{n} new images; {len(rows)} in manifest")

if __name__ == "__main__":
    main()
