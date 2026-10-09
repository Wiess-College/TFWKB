"""Copy the photo decisions in sources/photo-placements.yaml onto the site.

Editors decide where each photograph goes, and what its caption and credit say, in one file:
sources/photo-placements.yaml. The same caption has to appear in three places, and keeping them in step
by hand drifts, so this script regenerates all three from that one file. It reads the photos and galleries
listed there, checks the photo files under docs/assets/photos/, and writes these files under docs/:

    Record pages                  each <!-- GALLERY:key --> placeholder filled with a photo grid
    gallery/index.md              the Photographs page, rewritten from scratch
    assets/photos/manifest.tsv    caption, credit, date and topic columns updated in existing rows

Run it from anywhere after any change to photo-placements.yaml:

    python3 tools/apply_photos.py

Running it twice changes nothing the second time. A filled placeholder is wrapped in
<!-- GALLERY:key --> ... <!-- /GALLERY:key -->, and the next run replaces what is between the markers
instead of adding a second copy.

If it stops, the message says how far it got. Fix the cause and run it again.

    "photo-placements.yaml: ..."             the file is not valid YAML, or an entry is malformed (the
                                             message says which); nothing has been written yet.
    "missing photo: ..."                     nothing has been written yet.
    "no placeholder for ... in ..."          pages earlier in GALLERY_PAGES are written; the rest are not.
    "not in manifest: ..."                   all pages and gallery/index.md written; manifest unchanged.
    "tab or newline inside a manifest field" same as above.
"""

import html
import os
import re
import sys
from typing import NamedTuple

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_ROOT = os.path.join(REPO_ROOT, "docs")
PLACEMENTS_FILE = os.path.join(REPO_ROOT, "sources", "photo-placements.yaml")

# The fields of one photo in photo-placements.yaml, and the PhotoPlacement field each one fills. Editors see
# the short names on the left; the script uses the longer ones, which say what each value is.
PHOTO_FIELDS = {
    "photo": "photo_subpath",
    "gallery": "gallery_key",
    "caption": "caption",
    "credit": "credit_plain",
    "citation": "credit_citation",
    "date": "date",
    "topic": "topic",
}
GALLERY_FIELDS = {"page": "page_path", "heading": "heading"}

# Paths relative to docs/, the way pages link to them. Joined with "+" rather than os.path.join so they keep
# the forward slashes Markdown links and the manifest need. (The tools assume macOS or Linux.)
PHOTOS_PATH = "assets/photos/"
GALLERY_INDEX_PATH = "gallery/index.md"
MANIFEST_PATH = PHOTOS_PATH + "manifest.tsv"

# The manifest's web_path column is relative to the repo root, not to docs/.
WEB_PATH_PREFIX = "docs/" + PHOTOS_PATH

# Update when someone reviews the Photographs page; it appears in its front matter and footer.
GALLERY_INDEX_LAST_REVIEWED = "2026-10-05"


class PhotoPlacement(NamedTuple):
    """One photograph, the gallery it belongs to, and what to say about it."""

    photo_subpath: str  # relative to docs/assets/photos/, e.g. "nod/1983.jpg"
    gallery_key: str  # one of the gallery names in photo-placements.yaml
    caption: str  # plain text; also the lightbox title and the manifest caption
    credit_plain: str  # who made or published the photo, as plain text
    credit_citation: str  # Markdown citations such as "[@rhc 2012-12-04 ...]", or "" when there is nothing to cite
    date: str  # as precise as the evidence allows: "1949-03-01", "1969-09", "c.1983"
    topic: str  # short subject for the manifest, e.g. "Old Wiess, 2002"


class GalleryPage(NamedTuple):
    """The Record page a gallery sits on, and the gallery's heading on the Photographs page."""

    page_path: str  # relative to docs/, e.g. "places/old-wiess.md"
    heading: str  # the gallery's section heading on the Photographs page


def main() -> None:
    """Check the photos, then fill the Record pages, the Photographs page and the manifest, in that order.

    Every photo file is checked before anything is written, so a misspelt file name stops the run
    while the site is still unchanged. The module docstring lists what each later exit leaves written.
    """
    placements, gallery_pages = read_photo_placements()
    check_every_photo_file_exists(placements)
    placements_by_gallery = group_by_gallery(placements, gallery_pages)

    fill_record_page_galleries(placements_by_gallery, gallery_pages)
    write_gallery_index(placements_by_gallery, gallery_pages, len(placements))
    updated_row_count = update_manifest(placements, gallery_pages)

    print(
        f"placed {len(placements)} photos on {len(gallery_pages)} pages; "
        f"manifest rows updated: {updated_row_count}"
    )


def read_photo_placements() -> tuple[list[PhotoPlacement], dict[str, GalleryPage]]:
    """Return the photos and galleries in photo-placements.yaml, stopping with a message if one is malformed.

    Editors write this file by hand, so a mistake should stop the run with a message naming the photo,
    before anything is written, rather than with a traceback or a page that is quietly wrong. Each photo
    and gallery must have exactly its fields, and each photo's gallery must be listed. Galleries keep the
    order they are listed in, which is the order of sections on the Photographs page.
    """
    try:
        with open(PLACEMENTS_FILE, encoding="utf-8") as placements_yaml:
            placement_data = yaml.safe_load(placements_yaml)
    except yaml.YAMLError as yaml_error:
        # PyYAML's message gives the line and column where reading stopped.
        sys.exit(f"photo-placements.yaml: not valid YAML: {yaml_error}")
    gallery_pages = {
        gallery_key: GalleryPage(**read_fields(gallery, GALLERY_FIELDS, f"gallery {gallery_key}"))
        for gallery_key, gallery in placement_data["galleries"].items()
    }
    placements = []
    for photo in placement_data["photos"]:
        photo_name = f"photo {photo.get('photo') if isinstance(photo, dict) else photo}"
        placement = PhotoPlacement(**read_fields(photo, PHOTO_FIELDS, photo_name))
        if placement.gallery_key not in gallery_pages:
            sys.exit(f"photo-placements.yaml: {photo_name}: no gallery named {placement.gallery_key}")
        placements.append(placement)
    return placements, gallery_pages


def read_fields(entry: dict, field_names: dict[str, str], entry_name: str) -> dict[str, str]:
    """Return an entry's values as text, keyed by record field name; stop if a field is missing or extra.

    YAML reads some unquoted values as other types: 1969 as a number, 1949-03-01 as a date, and an empty
    value as nothing. Those are turned back into the text the editor typed (nothing becomes ""), so a
    forgotten pair of quotation marks does no harm. A list or a set of fields where text belongs stops it.
    """
    if not isinstance(entry, dict) or set(entry) != set(field_names):
        sys.exit(f"photo-placements.yaml: {entry_name}: needs exactly the fields {', '.join(field_names)}")
    values = {}
    for yaml_name, field_name in field_names.items():
        value = entry[yaml_name]
        if isinstance(value, (list, dict)):
            sys.exit(f"photo-placements.yaml: {entry_name}: {yaml_name} should be text")
        values[field_name] = "" if value is None else str(value)
    return values


def check_every_photo_file_exists(placements: list[PhotoPlacement]) -> None:
    """Stop with "missing photo: ..." if a listed photo file is not on disk."""
    for placement in placements:
        if not os.path.exists(os.path.join(DOCS_ROOT, PHOTOS_PATH + placement.photo_subpath)):
            sys.exit(f"missing photo: {placement.photo_subpath}")


def group_by_gallery(
    placements: list[PhotoPlacement],
    gallery_pages: dict[str, GalleryPage],
) -> dict[str, list[PhotoPlacement]]:
    """Return each gallery's photos in listed order, with an empty list for a gallery that has none."""
    placements_by_gallery: dict[str, list[PhotoPlacement]] = {gallery_key: [] for gallery_key in gallery_pages}
    for placement in placements:
        placements_by_gallery[placement.gallery_key].append(placement)
    return placements_by_gallery


def fill_record_page_galleries(
    placements_by_gallery: dict[str, list[PhotoPlacement]],
    gallery_pages: dict[str, GalleryPage],
) -> None:
    """Write each gallery's photo grid into its Record page, at its placeholder.

    Editors write Record pages by hand and choose where the photos go by typing
    <!-- GALLERY:key --> there. The script never adds a placeholder: a page without one is an
    error, so a gallery cannot silently fail to appear.

    Two galleries may share a page. Each is filled in its own pass that re-reads the page, so the
    second pass keeps the first pass's work.
    """
    for gallery_key, gallery_page in gallery_pages.items():
        page_file = os.path.join(DOCS_ROOT, gallery_page.page_path)
        with open(page_file, encoding="utf-8") as page:
            page_text = page.read()

        photo_grid = render_photo_grid(placements_by_gallery[gallery_key], gallery_page.page_path, gallery_key)
        marked_photo_grid = f"<!-- GALLERY:{gallery_key} -->\n{photo_grid}<!-- /GALLERY:{gallery_key} -->"

        # Matches the opening marker alone (never filled) or the opening marker through its closing
        # marker (filled by an earlier run): the trailing "(...)?" makes the closing part optional.
        # ".*?" is non-greedy, so it stops at the first closing marker; re.DOTALL lets it cross lines.
        gallery_pattern = re.compile(
            rf"<!-- GALLERY:{gallery_key} -->(?:.*?<!-- /GALLERY:{gallery_key} -->)?",
            re.DOTALL,
        )
        if not gallery_pattern.search(page_text):
            sys.exit(f"no placeholder for {gallery_key} in {gallery_page.page_path}")

        # The replacement is a function, not a string, so backslashes in captions are written as-is
        # instead of being read as regex escapes such as "\1".
        page_text = gallery_pattern.sub(lambda _match: marked_photo_grid, page_text, count=1)
        with open(page_file, "w", encoding="utf-8") as page:
            page.write(page_text)


def write_gallery_index(
    placements_by_gallery: dict[str, list[PhotoPlacement]],
    gallery_pages: dict[str, GalleryPage],
    photo_count: int,
) -> None:
    """Rewrite the Photographs page (docs/gallery/index.md) with every photo, one section per gallery.

    Readers browsing for pictures, and editors checking captions, want the whole collection on one
    page. The page is generated, so hand edits to it are lost on the next run; change the
    introduction in render_gallery_index_introduction() instead.

    Uses thumbnails so the page loads quickly. Each section gets its own lightbox group, so clicking
    through the enlarged photos stays within one section.
    """
    os.makedirs(os.path.join(DOCS_ROOT, "gallery"), exist_ok=True)
    sections = [render_gallery_index_introduction(photo_count)]
    for gallery_key, gallery_page in gallery_pages.items():
        # Record page paths are relative to docs/; links from this page must be relative to docs/gallery/.
        record_page_link = os.path.relpath(gallery_page.page_path, "gallery")
        sections.append(
            f"## {gallery_page.heading}\n\n"
            f"On [{gallery_page.heading}]({record_page_link}#photographs).\n\n"
        )
        sections.append(
            render_photo_grid(
                placements_by_gallery[gallery_key],
                GALLERY_INDEX_PATH,
                "index-" + gallery_key,
                use_thumbnails=True,
            )
        )
        sections.append("\n")
    sections.append(
        f'<div class="reviewed" markdown>Last reviewed {GALLERY_INDEX_LAST_REVIEWED} by unreviewed'
        " · [Edit this page](#)</div>\n"
    )
    with open(os.path.join(DOCS_ROOT, GALLERY_INDEX_PATH), "w", encoding="utf-8") as index_page:
        index_page.write("".join(sections))


def render_gallery_index_introduction(photo_count: int) -> str:
    """Return the Photographs page's front matter, title and opening paragraphs."""
    return (
        "---\n"
        "title: Photographs\n"
        "status: draft\n"
        f"last_reviewed: {GALLERY_INDEX_LAST_REVIEWED}\n"
        "reviewed_by: unreviewed\n"
        "---\n\n"
        "# Photographs\n\n"
        f"Every photograph and graphic placed on a Record page, {photo_count} in all, grouped by the page it "
        "illustrates. Click any image to enlarge it; the caption under each says what it shows, where it came "
        "from and how we know the date. Where the source is a capture of a college website, the citation opens "
        "that capture in the Wayback Machine. Where a caption says *source not recorded*, the image reached the "
        "collection without a note of where it was first published, and its date comes from its file name or "
        "its content; treat those dates as provisional.\n\n"
        "**Preservation:** These are web-size copies (at most 1,600 pixels on the long side) with thumbnails. "
        "The originals, at full size, are kept by the maintainers, and an Internet Archive collection of them "
        "is planned so that every photograph here has a permanent public home that does not depend on this "
        "site. The list of files, with sizes, checksums and these captions, is "
        "`docs/assets/photos/manifest.tsv`. Photographs are chosen to show places and customs; students are "
        "not named in captions unless the [Core Team](../people/core-team.md) table or a public record names "
        "them as office-holders, and nothing revealing from Night of Decadence is shown. See "
        "[Rights](../contributing/rights.md).\n\n"
    )


def update_manifest(
    placements: list[PhotoPlacement],
    gallery_pages: dict[str, GalleryPage],
) -> int:
    """Copy captions, credits, dates and topics into manifest.tsv, and return how many rows it rewrote.

    The manifest is the record that will travel with the photos to the Internet Archive, so it must
    say what each photo shows to someone who never sees this site.

    Rows are created by tools/make_web_photos.py, not here. This only overwrites four columns of rows
    that already exist, and leaves sizes, checksums and unplaced photos alone. Columns are found by
    header name, so reordering them in the file is safe. Both exits happen before the file is
    rewritten.
    """
    manifest_file = os.path.join(DOCS_ROOT, MANIFEST_PATH)
    with open(manifest_file, encoding="utf-8") as manifest:
        rows = [line.rstrip("\n").split("\t") for line in manifest if line.strip()]
    header = rows[0]
    column_position = {column_name: position for position, column_name in enumerate(header)}

    # If photo-placements.yaml lists the same file twice, the later entry wins.
    placement_by_web_path = {WEB_PATH_PREFIX + placement.photo_subpath: placement for placement in placements}
    updated_web_paths = set()
    for row in rows[1:]:
        web_path = row[column_position["web_path"]]
        placement = placement_by_web_path.get(web_path)
        if placement is None:
            continue
        updated_web_paths.add(web_path)
        page_path = gallery_pages[placement.gallery_key].page_path
        row[column_position["caption"]] = placement.caption
        row[column_position["credit"]] = format_manifest_credit(placement)
        row[column_position["date"]] = placement.date
        row[column_position["topic"]] = f"{placement.topic} ({page_path})"

    web_paths_without_rows = set(placement_by_web_path) - updated_web_paths
    if web_paths_without_rows:
        sys.exit(f"not in manifest: {sorted(web_paths_without_rows)}")
    # A tab or newline inside a field would shift every later column, or split the row, on the next read.
    for row in rows:
        if any("\t" in field or "\n" in field for field in row):
            sys.exit("tab or newline inside a manifest field")
    with open(manifest_file, "w", encoding="utf-8") as manifest:
        manifest.write("".join("\t".join(row) + "\n" for row in rows))
    return len(updated_web_paths)


def format_manifest_credit(placement: PhotoPlacement) -> str:
    """Return the credit with bare citation keys ("@rhc ...") in place of Markdown citations ("[@rhc ...]").

    The manifest is read outside the site, where citation links do not render.
    """
    # Captures the text between "[@" and the next "]" in each citation.
    citation_keys = re.findall(r"\[@([^\]]+)\]", placement.credit_citation)
    if not citation_keys:
        return placement.credit_plain
    return placement.credit_plain + " — " + "; ".join("@" + citation_key for citation_key in citation_keys)


def render_photo_grid(
    placements: list[PhotoPlacement],
    page_path: str,
    lightbox_group: str,
    use_thumbnails: bool = False,
) -> str:
    """Return a grid of figures, one per photo, for the page at page_path.

    "grid" is Material for MkDocs' generic grid; "photo-grid" (docs/assets/familykb.css) sets its columns
    and the size of each photo. The markdown attribute asks the md_in_html extension to render the
    Markdown inside. Joining lines that already end in a newline with another newline leaves a blank line
    between figures, which keeps each one a separate HTML block.
    """
    lines = ['<div class="grid photo-grid" markdown>\n']
    for placement in placements:
        lines.append(render_figure(placement, page_path, lightbox_group, use_thumbnails))
    lines.append("</div>\n")
    return "\n".join(lines)


def render_figure(
    placement: PhotoPlacement,
    page_path: str,
    lightbox_group: str,
    use_thumbnails: bool = False,
) -> str:
    """Return one photo as a <figure>, with its caption and credit under it.

    The { ... } after the image is attr_list syntax, which sets these attributes on the <img>. The
    glightbox plugin then reads them: the lightbox shows data-title and data-description, and lets
    readers click through photos sharing a data-gallery.
    """
    image_path = PHOTOS_PATH + placement.photo_subpath
    if use_thumbnails:
        # thumbs/ sits next to each photo ("nod/1983.jpg" -> "nod/thumbs/1983.jpg"). Fall back to the
        # full-size photo if make_web_photos.py made no thumbnail.
        folder, file_name = os.path.split(placement.photo_subpath)
        thumbnail_path = PHOTOS_PATH + folder + "/thumbs/" + file_name
        if os.path.exists(os.path.join(DOCS_ROOT, thumbnail_path)):
            image_path = thumbnail_path
    # Both paths are relative to docs/; the link must be relative to the folder of the page it sits on.
    image_link = os.path.relpath(image_path, os.path.dirname(page_path))
    # Square brackets in alt text would end the Markdown image syntax early.
    alt_text = re.sub(r"[\[\]]", "", placement.caption)
    lightbox_description = placement.credit_plain + (f" · {placement.date}" if placement.date else "")

    caption_html = placement.caption
    if placement.credit_citation:
        caption_html += f" <small>{html.escape(placement.credit_plain)} {placement.credit_citation}</small>"
    else:
        caption_html += f" <small>{html.escape(placement.credit_plain)}</small>"

    return (
        '<figure markdown="span">\n'
        f'  ![{alt_text}]({image_link}){{ loading=lazy data-title="{escape_html_attribute(placement.caption)}" '
        f'data-description="{escape_html_attribute(lightbox_description)}" data-gallery="{lightbox_group}" }}\n'
        f"  <figcaption>{caption_html}</figcaption>\n"
        "</figure>\n"
    )


def escape_html_attribute(text: str) -> str:
    """Escape text for a double-quoted HTML attribute (captions contain quotes and ampersands)."""
    return html.escape(text, quote=True)


if __name__ == "__main__":
    main()
