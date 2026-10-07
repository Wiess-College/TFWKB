#!/usr/bin/env python3
"""Make web-size copies and thumbnails of a folder of original photos, and list them in manifest.tsv.

The original photographs are too large to serve on the site, and their file names are whatever the camera or
scanner chose. This script makes the small copies the site actually shows, gives them predictable names, and
records in docs/assets/photos/manifest.tsv where each copy came from, so that every photo on the site can be
traced back to its original. It needs Pillow, which requirements-dev.txt installs (requirements.txt does not).

Run it from the repo root whenever originals are added to the photo folders, before listing the new photos in
sources/photo-placements.yaml and running tools/apply_photos.py (which needs their manifest rows):

    python3 tools/make_web_photos.py <source-root> [--out docs/assets/photos]

For every image under <source-root> whose name ends in .jpg, .jpeg, .png, .gif or .webp (in any case, and not
starting with "."), it writes two files into the --out folder:

    <folder-slug>/<name-slug>.jpg           the web copy, at most 1600 pixels on the long side, JPEG quality 82
    <folder-slug>/thumbs/<name-slug>.jpg    the thumbnail, at most 400 pixels on the long side, JPEG quality 78

The folder slug is the image's folder path under <source-root>, each folder name made lower-case with every
run of other characters turned into "-", joined with "-"; images directly in <source-root> go in "misc". The
name slug is the file name without its extension, made the same way (see slugify()), with "-2", "-3", ... added
when that name is already taken. Photos are turned upright using their EXIF orientation, and transparent areas
become white. EXIF, colour profiles and other metadata are not copied into the web copies.

It then rewrites <out>/manifest.tsv, keeping every row already there (though a caption's quotation marks can
change; see read_manifest()) and adding one per new image, with these tab-separated columns:

    web_path  thumb_path  source_path  width  height  sha256  caption  credit  date  topic

web_path and thumb_path are the --out folder joined with the paths above, so with the default --out they are
relative to the repo root. source_path is relative to <source-root>. width and height are the web copy's
size, and sha256 is the checksum of the original. caption/credit/date/topic start empty; for photos placed on
a page, tools/apply_photos.py fills them from sources/photo-placements.yaml.

Re-running skips images already done (matched by the original's sha256), so it is safe to repeat. Originals
are never modified; keep them (and an Internet Archive copy) as the preservation masters.

An image that cannot be converted or saved (Pillow cannot read it, or its web copy or thumbnail cannot be
written) is not an error: the script prints "skip <path> <reason>" to stderr, adds no manifest row for it, and
tries it again on the next run. If the script stops with a traceback instead, here is what has already been
written:

    FileExistsError or                 --out (or a folder above it) is a file, or manifest.tsv can't be read
      NotADirectoryError, or an        (no permission, a folder in its place, or bytes the system's encoding
      error reading manifest.tsv       can't decode). Nothing has been written, except perhaps the --out folder.
    KeyError: 'sha256' or 'web_path'   the manifest lacks that column; only the --out folder has been made.
    PermissionError or another error   an original could not be read or a folder could not be made. Web
      while copying images             copies made so far are on disk, but the manifest is unchanged.
                                       Running again remakes them under the same names, and lists them.
    ValueError: dict contains fields   the manifest has a column not in the list above, or a row has more
                                       fields than the header. All web copies are made, and the manifest has
                                       been cut short just before the first such row (just after the header,
                                       for an extra column): restore it from git before running again.

A <source-root> that does not exist is not an error either: it finds no images, prints "0 new images", and
rewrites the manifest with the rows it already had.
"""

import argparse
import csv
import hashlib
import os
import re
import sys

from PIL import Image, ImageOps

# Compared with the file's extension lower-cased, so ".JPG" counts too.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

MANIFEST_FILE_NAME = "manifest.tsv"
MANIFEST_COLUMNS = [
    "web_path", "thumb_path", "source_path", "width", "height", "sha256", "caption", "credit", "date", "topic"
]

# Longest side in pixels, and JPEG quality on Pillow's scale from 0 (worst) to 95 (best).
WEB_COPY_LONG_EDGE = 1600
WEB_COPY_JPEG_QUALITY = 82
THUMBNAIL_LONG_EDGE = 400
THUMBNAIL_JPEG_QUALITY = 78


def main(arguments: list[str]) -> None:
    """Make web copies of the new images under the source folder, then rewrite the manifest to list them."""
    parser = argparse.ArgumentParser()
    # The metavars keep the usage text and error messages reading "[--out OUT] src", as they always have.
    parser.add_argument("source_root", metavar="src")
    parser.add_argument("--out", dest="output_root", metavar="OUT", default="docs/assets/photos")
    options = parser.parse_args(arguments)

    os.makedirs(options.output_root, exist_ok=True)
    manifest_file = os.path.join(options.output_root, MANIFEST_FILE_NAME)
    rows = read_manifest(manifest_file)
    new_image_count = add_new_images(options.source_root, options.output_root, rows)
    write_manifest(manifest_file, rows)
    print(f"{new_image_count} new images; {len(rows)} in manifest")


def read_manifest(manifest_file: str) -> list[dict[str, str | int]]:
    """Return the manifest's rows as dictionaries keyed by column name, or no rows if there is no manifest yet.

    The file is read with the csv module, which treats a field that starts with a double quote as quoted.
    tools/apply_photos.py writes fields without quoting, so a caption that starts with a quote loses its
    quotes here, and write_manifest() puts quotes around any field that contains one. tools/apply_photos.py
    rewrites the caption, credit, date and topic of placed photos, so running it afterwards repairs them.

    The file is read and written in the system's default encoding rather than explicitly as UTF-8, which
    tools/apply_photos.py uses; on a Mac or Linux machine set to UTF-8 the two agree.
    """
    if not os.path.exists(manifest_file):
        return []
    with open(manifest_file, newline="") as manifest:
        return list(csv.DictReader(manifest, delimiter="\t"))


def add_new_images(source_root: str, output_root: str, rows: list[dict[str, str | int]]) -> int:
    """Make a web copy and thumbnail of each image not yet in the manifest, add its row, and return how many.

    An image counts as done when the checksum of its original is already in the manifest, so a photo that
    has been renamed or moved in the source folder is not copied twice. Identical files are copied once.

    Folders are visited in the order the file system lists them, and the images in each folder in sorted
    order. Which of two images that would get the same name receives the "-2" depends on that order.

    source_root and output_root are the folders as given on the command line, so relative to the current folder
    unless absolute. web_path, thumb_path and every *_file path built from them are in the same frame: relative
    to the repo root when run from there with the default --out. source_path in the manifest is relative to
    source_root.
    """
    done_checksums = {row["sha256"] for row in rows}
    used_web_paths = {row["web_path"] for row in rows}
    new_image_count = 0
    for source_folder, _, file_names in os.walk(source_root):
        for file_name in sorted(file_names):
            name_stem, extension = os.path.splitext(file_name)
            if extension.lower() not in IMAGE_EXTENSIONS or file_name.startswith("."):
                continue
            source_file = os.path.join(source_folder, file_name)
            original_checksum = compute_sha256(source_file)
            if original_checksum in done_checksums:
                continue

            web_path = choose_web_path(source_root, source_folder, name_stem, output_root, used_web_paths)
            # The thumbnail has the web copy's file name, in a thumbs/ folder beside it.
            thumb_path = os.path.join(os.path.dirname(web_path), "thumbs", os.path.basename(web_path))
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            web_copy_size = make_web_copy_and_thumbnail(source_file, web_path, thumb_path)
            if web_copy_size is None:
                continue
            width, height = web_copy_size

            rows.append({
                "web_path": web_path,
                "thumb_path": thumb_path,
                "source_path": os.path.relpath(source_file, source_root),
                "width": width,
                "height": height,
                "sha256": original_checksum,
                "caption": "",
                "credit": "",
                "date": "",
                "topic": "",
            })
            used_web_paths.add(web_path)
            done_checksums.add(original_checksum)
            new_image_count += 1
    return new_image_count


def compute_sha256(source_file: str) -> str:
    """Return the SHA-256 checksum of a file as hex, reading it a megabyte at a time.

    Reading in pieces means a large scan is never held in memory whole.
    """
    checksum = hashlib.sha256()
    with open(source_file, "rb") as original:
        for chunk in iter(lambda: original.read(1 << 20), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def choose_web_path(
    source_root: str,
    source_folder: str,
    name_stem: str,
    output_root: str,
    used_web_paths: set[str],
) -> str:
    """Return the web copy's path: the output folder, the folder slug and the name slug, numbered if taken.

    A name counts as taken only if the manifest, or an image earlier in this run, already has it, compared
    as text. A file already in the output folder that the manifest does not list is overwritten, and so is
    one listed under a different spelling of --out (for example "./docs/assets/photos").
    """
    folder_subpath = os.path.relpath(source_folder, source_root)  # relative to source_root
    if folder_subpath == ".":
        folder_slug = "misc"
    else:
        folder_slug = "-".join(slugify(folder_name) for folder_name in folder_subpath.split(os.sep))
    name_slug = slugify(name_stem)
    web_path = os.path.join(output_root, folder_slug, name_slug + ".jpg")
    copy_number = 2
    while web_path in used_web_paths:
        web_path = os.path.join(output_root, folder_slug, f"{name_slug}-{copy_number}.jpg")
        copy_number += 1
    return web_path


def slugify(name: str) -> str:
    """Return the name lower-cased with each run of characters other than a-z and 0-9 as "-", trimmed.

    An empty result becomes "img". Accented and non-Latin letters count as other characters, so "Café" becomes
    "caf", or "cafe" if the disk stores the accent as a separate character.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "img"


def make_web_copy_and_thumbnail(source_file: str, web_path: str, thumb_path: str) -> tuple[int, int] | None:
    """Write one image's web copy and thumbnail, and return the web copy's size, or None if Pillow failed.

    Any exception while opening, converting or saving skips the image with a message rather than stopping
    the run, so one damaged scan does not hold up the rest. If the thumbnail fails after the web copy was
    saved, the web copy stays on disk without a manifest row, and the next run tries the image again.
    """
    try:
        with Image.open(source_file) as original:
            # Cameras store "rotate this" in EXIF rather than rotating the pixels; apply it, since the copies
            # carry no EXIF.
            image = flatten_onto_white(ImageOps.exif_transpose(original))
            web_copy_size = save_resized_jpeg(image, web_path, WEB_COPY_LONG_EDGE, WEB_COPY_JPEG_QUALITY)
            save_resized_jpeg(image, thumb_path, THUMBNAIL_LONG_EDGE, THUMBNAIL_JPEG_QUALITY)
    except Exception as error:  # Pillow raises many kinds of exception for damaged or unusual files.
        print("skip", source_file, error, file=sys.stderr)
        return None
    return web_copy_size


def flatten_onto_white(image: Image.Image) -> Image.Image:
    """Return the image as colour or greyscale, with any transparency laid over white (JPEG has no transparency).

    Every other mode, including palette GIFs and greyscale with transparency, is converted to RGBA first and
    becomes an RGB image.
    """
    if image.mode in ("RGB", "L"):
        return image
    flattened_image = Image.new("RGB", image.size, (255, 255, 255))
    rgba_image = image.convert("RGBA")
    flattened_image.paste(rgba_image, mask=rgba_image.getchannel("A"))
    return flattened_image


def save_resized_jpeg(image: Image.Image, output_file: str, long_edge: int, quality: int) -> tuple[int, int]:
    """Save a copy of the image shrunk to fit long_edge pixels as a JPEG, and return its width and height.

    thumbnail() keeps the proportions and never enlarges, so a small image is saved at its own size.
    """
    resized_image = image.copy()
    resized_image.thumbnail((long_edge, long_edge), Image.LANCZOS)
    resized_image.save(output_file, "JPEG", quality=quality, optimize=True, progressive=True)
    return resized_image.size


def write_manifest(manifest_file: str, rows: list[dict[str, str | int]]) -> None:
    """Rewrite the manifest with a header row and every row, in the order they were read or added.

    The file is rewritten even when no image was added. The csv module ends each line with a carriage return
    and a newline, and tools/apply_photos.py with a newline alone, so a run after apply_photos.py shows every
    line of the manifest as changed in git.
    """
    with open(manifest_file, "w", newline="") as manifest:
        writer = csv.DictWriter(manifest, fieldnames=MANIFEST_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
