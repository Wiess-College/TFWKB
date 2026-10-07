#!/usr/bin/env python3
"""Repair the text layer of a PDF whose fonts say the wrong letters, by recognising each glyph's shape.

Some O-Week books embed subset fonts whose character codes do not say which letter each glyph draws. The
page looks right, but every text extractor (pdftotext, PyMuPDF, pdfminer) reads the codes as they are, so
"When we said" comes out as '3#+-"6+"4$0&' in the 2011 book and "the" as "WKH" in the 2014 book. Decoding
that text afterwards takes a hand-made table per font, and a table built by eye can be wrong: the one for
the 2011 book swapped "!" and ")".

The glyph outlines inside the font are intact, though, and every subset cut from the same font has
identical outlines. So this script identifies each glyph by its shape, using two kinds of reference:

    font files on this machine   a family named like the PDF's font (macOS ships Hoefler Text, Times, Optima
                                 and others), plus any file given with --ref
    other fonts in the PDF       subsets of the same typeface whose text already extracts as English

A font is judged broken when most of its glyphs that match a reference shape extract as some other
character. For each broken font it works out what every glyph really draws; a repair then gives that font a
new /ToUnicode map, which every extractor reads in preference to the codes. Nothing visible changes.

It reads one PDF. The report mode writes nothing; the repair mode writes one new PDF and never touches the
original. Both print one line per font that has text (its verdict), and for each broken font what each
garbled character should be:

    python3 tools/fix_pdf_fonts.py report  BOOK.pdf
    python3 tools/fix_pdf_fonts.py repair  BOOK.pdf BOOK-fixed.pdf
    pdftotext -layout BOOK-fixed.pdf BOOK.txt

    --ref FONT_FILE      also compare against this .ttf, .otf or .ttc file; give it once per file
    --no-installed-fonts compare only against --ref files and the PDF's own fonts

It needs PyMuPDF and fontTools, which requirements-dev.txt installs (requirements.txt, for the site, does not):
pip install -r requirements-dev.txt.

In the report, a glyph written with an unquoted ? matched no reference shape; a repair leaves it as it
was. "unchecked" means none of the font's glyphs matched a reference, so the script cannot tell whether
its text is right; give a copy of the typeface with --ref. A broken font that is neither a simple TrueType
font nor a CID font with an Identity encoding is reported, but a repair skips it and says so
("not repaired, codes cannot be traced to glyphs").

A PDF that cannot be opened stops it with a traceback before anything is written. In repair mode, an
output file that cannot be written stops it with a traceback after the report; no file is written.
"""

import argparse
import hashlib
import io
import logging
import os
import re
import sys
import unicodedata
from collections import Counter
from typing import NamedTuple

import pymupdf
from fontTools import agl
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.ttLib import TTCollection, TTFont
from fontTools.ttLib.standardGlyphOrder import standardGlyphOrder

# Folders searched for a font file of the same family as each PDF font, on macOS and Linux.
INSTALLED_FONT_ROOTS = [
    "/System/Library/Fonts",
    "/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
    "/usr/share/fonts",
    os.path.expanduser("~/.local/share/fonts"),
]
FONT_FILE_SUFFIXES = (".ttf", ".otf", ".ttc")

# Stands in for the fingerprint of a glyph with no outline. Every font's space looks like this, so it says
# nothing about which glyph it is; a broken font's empty glyphs are taken to be spaces.
EMPTY_SHAPE = "empty"

# A PDF font whose text is at least this share lowercase letters and spaces reads as English, and is used
# as a reference. Garbled text falls far below it: the 2011 cipher is mostly punctuation, and the 2014
# shifted font mostly capitals. Fonts with fewer characters than the minimum are not judged.
ENGLISH_SHARE_THRESHOLD = 0.5
ENGLISH_MINIMUM_CHARACTERS = 20
ENGLISH_CHARACTERS = set(" abcdefghijklmnopqrstuvwxyz")

# A font needs at least this many glyphs matching a reference shape before it is called broken.
MINIMUM_MATCHED_GLYPHS = 3

# The PDF's subset prefix, such as "NNMEHD+" in "NNMEHD+HoeflerText-Regular".
SUBSET_PREFIX_PATTERN = re.compile(r"^[A-Z]{6}\+")

# The name each font is given, in memory only, while its text is read. PyMuPDF drops the subset prefix from
# font names, so two subsets of one typeface would otherwise be indistinguishable.
TAGGED_FONT_NAME_PATTERN = re.compile(r"^font(?P<font_xref>\d+)tag")

# Ligature characters (U+FB00 "ﬀ" to U+FB06) are written into the repaired text as the letters they join.
LIGATURE_CHARACTERS = range(0xFB00, 0xFB07)

# What an extractor gives for a code it cannot map: the replacement character, or a control character.
UNPRINTABLE_EXTRACTIONS = {"\ufffd"} | {chr(code_point) for code_point in range(0x20)}

# A character used too rarely to print in the report; the commonest garbled characters are listed.
REPORT_MAP_LIMIT = 120


class PdfFont(NamedTuple):
    """One font in the PDF: its glyph shapes, and what its glyphs extract as on the pages."""

    font_xref: int  # object number of the font dictionary, as PyMuPDF numbers it
    base_font: str  # its /BaseFont, subset prefix included, e.g. "NNMEHD+HoeflerText-Regular"
    font_format: str  # "ttf", "otf" or "cff" for a font this script can read; anything else has no shapes
    shape_by_glyph_id: dict[int, str]  # fingerprint of each glyph's outline, or EMPTY_SHAPE
    extracted_by_glyph_id: dict[int, Counter[str]]  # what each glyph currently extracts as, with counts


class FontVerdict(NamedTuple):
    """What the script concluded about one font, and for a broken one, what each of its glyphs draws."""

    font: PdfFont
    matched_glyph_count: int  # glyphs used on the pages whose shape matched a reference
    agreeing_glyph_count: int  # of those, the ones already extracting as the reference's character
    is_broken: bool
    character_by_glyph_id: dict[int, str]  # for a broken font, every glyph identified; empty otherwise
    unidentified_glyph_ids: list[int]  # for a broken font, glyphs no reference identified


def main(arguments: list[str]) -> None:
    """Read the PDF's fonts, identify their glyphs by shape, report, and write a repaired copy if asked."""
    options = parse_arguments(arguments)
    # fontTools warns about every slightly malformed table, and embedded subsets have many; none matter here.
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    fonts = read_pdf_fonts(options.pdf)
    reference_files = options.ref + ([] if options.no_installed_fonts else find_installed_font_files(fonts))
    shape_table = build_shape_table(fonts, reference_files)
    verdicts = [judge_font(font, shape_table) for font in fonts if font.extracted_by_glyph_id]
    print_report(verdicts, reference_files)
    if options.command == "repair":
        repaired_count = write_repaired_pdf(options.pdf, options.output, verdicts)
        print(f"wrote {options.output} with {repaired_count} font(s) repaired")


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    """Return the command line's mode, files and options."""
    parser = argparse.ArgumentParser(description="Repair PDF fonts whose glyphs extract as the wrong letters.")
    parser.add_argument("command", choices=["report", "repair"])
    parser.add_argument("pdf", help="the PDF to check")
    parser.add_argument("output", nargs="?", help="where repair writes the repaired copy")
    parser.add_argument("--ref", action="append", default=[], help="a .ttf, .otf or .ttc file to compare against")
    parser.add_argument("--no-installed-fonts", action="store_true", help="ignore the font files on this machine")
    options = parser.parse_args(arguments)
    if options.command == "repair" and not options.output:
        parser.error("repair needs an output file")
    return options


def read_pdf_fonts(pdf_file: str) -> list[PdfFont]:
    """Return every font in the PDF with the shapes of its glyphs and what each glyph extracts as.

    The PDF is opened in memory only. Each font is renamed there before any page is read, so the text
    PyMuPDF extracts says which font object drew it.
    """
    document = pymupdf.open(pdf_file)
    base_font_by_xref = {
        font_xref: base_font for page in document for font_xref, _, _, base_font, *_ in page.get_fonts(full=True)
    }
    for font_xref in base_font_by_xref:
        tag_font_name(document, font_xref)
    extracted_by_font = read_extracted_glyphs(document)
    fonts = []
    for font_xref, base_font in base_font_by_xref.items():
        _, font_format, _, font_bytes = document.extract_font(font_xref)
        fonts.append(
            PdfFont(
                font_xref,
                base_font,
                font_format,
                fingerprint_glyph_shapes(font_format, font_bytes),
                extracted_by_font.get(font_xref, {}),
            )
        )
    return fonts


def tag_font_name(document: pymupdf.Document, font_xref: int) -> None:
    """Rename the font, its descendant font and their descriptors to "font<xref>tag", in memory only."""
    tagged_name = f"/font{font_xref}tag"
    font_xrefs = [font_xref] + referenced_xrefs(document, font_xref, "DescendantFonts")
    for each_font_xref in font_xrefs:
        document.xref_set_key(each_font_xref, "BaseFont", tagged_name)
        for descriptor_xref in referenced_xrefs(document, each_font_xref, "FontDescriptor"):
            document.xref_set_key(descriptor_xref, "FontName", tagged_name)


def read_extracted_glyphs(document: pymupdf.Document) -> dict[int, dict[int, Counter[str]]]:
    """Return, for each tagged font, what each of its glyph ids extracts as on every page, with counts."""
    extracted_by_font: dict[int, dict[int, Counter[str]]] = {}
    for page in document:
        for span in page.get_texttrace():
            tag_match = TAGGED_FONT_NAME_PATTERN.match(span["font"])
            if not tag_match:
                continue
            extracted_by_glyph_id = extracted_by_font.setdefault(int(tag_match["font_xref"]), {})
            # Each character is (Unicode code point, glyph id, origin, bounding box); a glyph id below 0
            # continues the character before it, as when one glyph extracts as two letters.
            for code_point, glyph_id, _, _ in span["chars"]:
                if glyph_id >= 0:
                    extracted_by_glyph_id.setdefault(glyph_id, Counter())[chr(code_point)] += 1
    return extracted_by_font


def find_installed_font_files(fonts: list[PdfFont]) -> list[str]:
    """Return the font files on this machine whose names start like the family of a font in the PDF.

    A family is the PDF font's name without its subset prefix or style ("HoeflerText-Black" becomes
    "hoeflertext"), and a file matches when its name, lowercased without spaces or punctuation, starts
    with the family or the family starts with it. A wrong match costs time but not accuracy, since a
    glyph is identified only by an exact shape.
    """
    families = {squash_name(SUBSET_PREFIX_PATTERN.sub("", font.base_font).split("-")[0]) for font in fonts}
    families.discard("")
    font_files = []
    for font_root in INSTALLED_FONT_ROOTS:
        for folder, _, file_names in os.walk(font_root):
            for file_name in file_names:
                stem, suffix = os.path.splitext(file_name)
                squashed_stem = squash_name(stem)
                if suffix.lower() in FONT_FILE_SUFFIXES and any(
                    squashed_stem.startswith(family) or (len(squashed_stem) >= 4 and family.startswith(squashed_stem))
                    for family in families
                ):
                    font_files.append(os.path.join(folder, file_name))
    return sorted(font_files)


def squash_name(name: str) -> str:
    """Return the name lowercased with everything but letters and digits removed."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def build_shape_table(fonts: list[PdfFont], reference_files: list[str]) -> dict[str, str]:
    """Return the character each known glyph shape draws, from font files first and then readable PDF fonts.

    Font files come first because their character maps are authoritative; a PDF font's text is trusted
    only when it reads as English. Where two references disagree about a shape, the first one wins.
    """
    shape_table: dict[str, str] = {}
    for reference_file in reference_files:
        for reference_font in open_font_file(reference_file):
            add_font_file_shapes(reference_font, shape_table)
    for font in fonts:
        if reads_as_english(font):
            for glyph_id, extracted in font.extracted_by_glyph_id.items():
                shape = font.shape_by_glyph_id.get(glyph_id, EMPTY_SHAPE)
                if shape != EMPTY_SHAPE:
                    shape_table.setdefault(shape, extracted.most_common(1)[0][0])
    return shape_table


def open_font_file(font_file: str) -> list[TTFont]:
    """Return the fonts in a .ttf, .otf or .ttc file, or none if it cannot be read as one."""
    try:
        if font_file.lower().endswith(".ttc"):
            return list(TTCollection(font_file).fonts)
        return [TTFont(font_file)]
    except Exception:  # pylint: disable=broad-except  # an unreadable file should not stop the others
        return []


def add_font_file_shapes(reference_font: TTFont, shape_table: dict[str, str]) -> None:
    """Add the shape of every glyph in the font's character map, with the character it stands for.

    One glyph can be mapped from several characters: Helvetica Neue draws both the apostrophe "’" and the
    modifier letter "ʼ" with one glyph. The glyph's name says which the designer meant ("quoteright"), so
    that character is used when it is one of them, and otherwise the lowest.
    """
    characters_by_glyph_name: dict[str, list[str]] = {}
    for code_point, glyph_name in sorted((reference_font.getBestCmap() or {}).items()):
        characters_by_glyph_name.setdefault(glyph_name, []).append(chr(code_point))
    glyph_set = reference_font.getGlyphSet()
    for glyph_name, characters in characters_by_glyph_name.items():
        named_character = agl.toUnicode(glyph_name)
        character = named_character if named_character in characters else characters[0]
        shape = fingerprint_glyph(glyph_set[glyph_name], DecomposingRecordingPen(glyph_set))
        if shape != EMPTY_SHAPE:
            shape_table.setdefault(shape, character)


def reads_as_english(font: PdfFont) -> bool:
    """Return whether the font's extracted text is mostly lowercase letters and spaces."""
    extracted_total = Counter()
    for extracted in font.extracted_by_glyph_id.values():
        extracted_total.update(extracted)
    character_count = sum(extracted_total.values())
    english_count = sum(count for character, count in extracted_total.items() if character in ENGLISH_CHARACTERS)
    return character_count >= ENGLISH_MINIMUM_CHARACTERS and english_count >= ENGLISH_SHARE_THRESHOLD * character_count


def judge_font(font: PdfFont, shape_table: dict[str, str]) -> FontVerdict:
    """Return whether the font is broken and, if so, what each of its glyphs really draws.

    Only glyphs that appear on the pages are counted, and empty glyphs are skipped, since every space
    looks alike. A broken font's glyphs are then identified all at once, including any not on the pages.
    """
    matched_count = agreeing_count = 0
    for glyph_id, extracted in font.extracted_by_glyph_id.items():
        reference_character = shape_table.get(font.shape_by_glyph_id.get(glyph_id, EMPTY_SHAPE))
        if reference_character is None:
            continue
        matched_count += 1
        extracted_text = extracted.most_common(1)[0][0]
        if extracted_text in (reference_character, expand_ligature(reference_character)[0]):
            agreeing_count += 1
    is_broken = matched_count >= MINIMUM_MATCHED_GLYPHS and agreeing_count * 2 < matched_count
    if not is_broken:
        return FontVerdict(font, matched_count, agreeing_count, False, {}, [])
    character_by_glyph_id, unidentified_glyph_ids = identify_glyphs(font, shape_table)
    return FontVerdict(font, matched_count, agreeing_count, True, character_by_glyph_id, unidentified_glyph_ids)


def identify_glyphs(font: PdfFont, shape_table: dict[str, str]) -> tuple[dict[int, str], list[int]]:
    """Return what each of a broken font's glyphs draws, and the glyph ids nothing identified.

    Glyphs not matched by shape are named from the standard Macintosh glyph order when the matched ones
    follow it. Fonts made on a Mac often keep that order: it is why the 2014 book's text is shifted by 29,
    the distance from a letter's code in ASCII to its place in that order.
    """
    character_by_glyph_id = {}
    for glyph_id, shape in font.shape_by_glyph_id.items():
        if glyph_id == 0:
            continue  # glyph 0 is .notdef, drawn for a missing character
        character = " " if shape == EMPTY_SHAPE else shape_table.get(shape)
        if character is not None:
            character_by_glyph_id[glyph_id] = character
    if follows_standard_macintosh_order(character_by_glyph_id):
        for glyph_id in font.shape_by_glyph_id:
            if glyph_id not in character_by_glyph_id and 0 < glyph_id < len(standardGlyphOrder):
                standard_character = agl.toUnicode(standardGlyphOrder[glyph_id])
                if standard_character:
                    character_by_glyph_id[glyph_id] = standard_character
    unidentified_glyph_ids = sorted(set(font.shape_by_glyph_id) - set(character_by_glyph_id) - {0})
    return character_by_glyph_id, unidentified_glyph_ids


def follows_standard_macintosh_order(character_by_glyph_id: dict[int, str]) -> bool:
    """Return whether at least nine in ten glyphs identified by shape sit where the Macintosh order puts them."""
    checkable = [
        (glyph_id, character)
        for glyph_id, character in character_by_glyph_id.items()
        if glyph_id < len(standardGlyphOrder) and character != " "
    ]
    in_place_count = sum(
        1 for glyph_id, character in checkable if agl.toUnicode(standardGlyphOrder[glyph_id]) == character
    )
    return len(checkable) >= MINIMUM_MATCHED_GLYPHS and in_place_count * 10 >= len(checkable) * 9


def print_report(verdicts: list[FontVerdict], reference_files: list[str]) -> None:
    """Print the reference files used, a verdict line for each font, and each broken font's character map."""
    print(f"reference font files: {', '.join(reference_files) or 'none'}")
    for verdict in sorted(verdicts, key=lambda verdict: (not verdict.is_broken, verdict.font.base_font)):
        font = verdict.font
        if verdict.is_broken:
            status = (
                f"BROKEN, {verdict.agreeing_glyph_count} of {verdict.matched_glyph_count} matched glyphs right; "
                f"{len(verdict.character_by_glyph_id)} glyphs identified, {len(verdict.unidentified_glyph_ids)} not"
            )
        elif verdict.matched_glyph_count:
            status = f"ok, {verdict.agreeing_glyph_count} of {verdict.matched_glyph_count} matched glyphs right"
        else:
            status = "unchecked, no glyph matched a reference"
        print(f"{font.base_font} (object {font.font_xref}, {font.font_format or 'no font file'}): {status}")
        if verdict.is_broken:
            print("    " + format_character_map(verdict))


def format_character_map(verdict: FontVerdict) -> str:
    """Return the broken font's glyphs as 'garbled'→'real' pairs, commonest first, with ? for unidentified."""
    pairs = []
    glyph_ids_by_frequency = sorted(
        verdict.font.extracted_by_glyph_id,
        key=lambda glyph_id: -sum(verdict.font.extracted_by_glyph_id[glyph_id].values()),
    )
    for glyph_id in glyph_ids_by_frequency[:REPORT_MAP_LIMIT]:
        extracted = verdict.font.extracted_by_glyph_id[glyph_id]
        garbled_character = extracted.most_common(1)[0][0]
        # A character the extractor could not map at all is shown by its glyph id instead.
        garbled = f"glyph {glyph_id}" if garbled_character in UNPRINTABLE_EXTRACTIONS else repr(garbled_character)
        real = verdict.character_by_glyph_id.get(glyph_id)
        pairs.append(f"{garbled}→{expand_ligature(real)!r}" if real else f"{garbled}→?")
    return " ".join(pairs)


def write_repaired_pdf(pdf_file: str, output_file: str, verdicts: list[FontVerdict]) -> int:
    """Write a copy of the PDF with a new /ToUnicode map on each repairable broken font; return how many.

    The map goes from the codes in the page content to the characters found, through each code's glyph.
    Fonts whose codes cannot be traced to glyphs are left alone and named on standard output.
    """
    document = pymupdf.open(pdf_file)
    repaired_count = 0
    for verdict in verdicts:
        if not verdict.is_broken:
            continue
        glyph_mapping = map_codes_to_glyph_ids(document, verdict.font)
        if glyph_mapping is None:
            print(f"not repaired, codes cannot be traced to glyphs: {verdict.font.base_font}")
            continue
        glyph_id_by_code, code_width = glyph_mapping
        character_by_code = {
            code: verdict.character_by_glyph_id[glyph_id]
            for code, glyph_id in glyph_id_by_code.items()
            if glyph_id in verdict.character_by_glyph_id
        }
        cmap_xref = document.get_new_xref()
        document.update_object(cmap_xref, "<<>>")
        document.update_stream(cmap_xref, render_to_unicode_cmap(character_by_code, code_width))
        document.xref_set_key(verdict.font.font_xref, "ToUnicode", f"{cmap_xref} 0 R")
        repaired_count += 1
    document.save(output_file, garbage=1, deflate=True)
    return repaired_count


def map_codes_to_glyph_ids(document: pymupdf.Document, font: PdfFont) -> tuple[dict[int, int], int] | None:
    """Return which glyph id each character code draws and how many bytes a code is, or None if unknown.

    Two kinds of font are handled. A CID font with an Identity encoding uses two-byte codes that are its
    CIDs, which are glyph ids unless a /CIDToGIDMap stream says otherwise. A simple TrueType font uses
    one-byte codes, looked up in the font file's own Macintosh or Windows-symbol character map.
    """
    subtype = document.xref_get_key(font.font_xref, "Subtype")[1]
    if subtype == "/Type0":
        if document.xref_get_key(font.font_xref, "Encoding")[1] not in ("/Identity-H", "/Identity-V"):
            return None
        descendant_xref = referenced_xrefs(document, font.font_xref, "DescendantFonts")[0]
        cid_to_glyph_kind, _ = document.xref_get_key(descendant_xref, "CIDToGIDMap")
        if cid_to_glyph_kind == "xref":
            cid_to_glyph_bytes = document.xref_stream(referenced_xrefs(document, descendant_xref, "CIDToGIDMap")[0])
            # The stream holds one two-byte, big-endian glyph id per CID, starting from CID 0.
            glyph_ids = [
                int.from_bytes(cid_to_glyph_bytes[offset : offset + 2])
                for offset in range(0, len(cid_to_glyph_bytes), 2)
            ]
            return {cid: glyph_id for cid, glyph_id in enumerate(glyph_ids) if glyph_id}, 2
        return {glyph_id: glyph_id for glyph_id in font.shape_by_glyph_id}, 2
    if subtype == "/TrueType" and font.font_format == "ttf":
        _, _, _, font_bytes = document.extract_font(font.font_xref)
        return map_simple_truetype_codes(TTFont(io.BytesIO(font_bytes))), 1
    return None


def map_simple_truetype_codes(truetype_font: TTFont) -> dict[int, int]:
    """Return the glyph id for each one-byte code in the font's (1,0) or (3,0) character map.

    A Windows-symbol (3,0) map puts codes at 0xF000 and up, so only the low byte is kept.
    """
    glyph_id_by_name = {name: glyph_id for glyph_id, name in enumerate(truetype_font.getGlyphOrder())}
    for platform_id, encoding_id in ((1, 0), (3, 0)):
        character_map = truetype_font["cmap"].getcmap(platform_id, encoding_id) if "cmap" in truetype_font else None
        if character_map:
            return {code & 0xFF: glyph_id_by_name[name] for code, name in character_map.cmap.items()}
    return {}


def render_to_unicode_cmap(character_by_code: dict[int, str], code_width: int) -> bytes:
    """Return a /ToUnicode CMap stream mapping each code to its character, ligatures as their letters.

    The format is Adobe's (PDF reference, section 9.10.3): codes and UTF-16BE text in hexadecimal, in
    blocks of at most 100 "bfchar" entries.
    """
    hex_digits = code_width * 2
    entries = [
        f"<{code:0{hex_digits}X}> <{expand_ligature(character).encode('utf-16-be').hex().upper()}>"
        for code, character in sorted(character_by_code.items())
    ]
    blocks = []
    for block_start in range(0, len(entries), 100):
        block = entries[block_start : block_start + 100]
        blocks.append(f"{len(block)} beginbfchar\n" + "\n".join(block) + "\nendbfchar")
    lowest_code, highest_code = "0" * hex_digits, "F" * hex_digits
    return (
        "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
        f"1 begincodespacerange\n<{lowest_code}> <{highest_code}>\nendcodespacerange\n"
        + "\n".join(blocks)
        + "\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"
    ).encode("ascii")


def referenced_xrefs(document: pymupdf.Document, xref: int, key: str) -> list[int]:
    """Return the object numbers that a dictionary's key refers to, whether one reference or an array of them."""
    _, value_text = document.xref_get_key(xref, key)
    return [int(number) for number in re.findall(r"(\d+) 0 R", value_text)]


def fingerprint_glyph_shapes(font_format: str, font_bytes: bytes) -> dict[int, str]:
    """Return a fingerprint of each glyph's outline by glyph id, or nothing for a font this cannot read."""
    try:
        if font_format in ("ttf", "otf"):
            font_file = TTFont(io.BytesIO(font_bytes))
            glyph_set = font_file.getGlyphSet()
            return {
                glyph_id: fingerprint_glyph(glyph_set[glyph_name], DecomposingRecordingPen(glyph_set))
                for glyph_id, glyph_name in enumerate(font_file.getGlyphOrder())
            }
        if font_format == "cff":
            font_set = CFFFontSet()
            font_set.decompile(io.BytesIO(font_bytes), None)
            top_dict = font_set[font_set.fontNames[0]]
            return {
                glyph_id: fingerprint_glyph(top_dict.CharStrings[glyph_name], RecordingPen())
                for glyph_id, glyph_name in enumerate(top_dict.charset)
            }
    except Exception:  # pylint: disable=broad-except  # a damaged embedded font should not stop the others
        return {}
    return {}


def fingerprint_glyph(glyph: object, pen: RecordingPen) -> str:
    """Return a hash of the glyph's outline drawing commands, or EMPTY_SHAPE when it draws nothing."""
    glyph.draw(pen)
    if not pen.value:
        return EMPTY_SHAPE
    return hashlib.sha1(repr(pen.value).encode()).hexdigest()


def expand_ligature(character: str) -> str:
    """Return a ligature character as the letters it joins ("ﬁ" as "fi"), and any other character as it is."""
    if len(character) == 1 and ord(character) in LIGATURE_CHARACTERS:
        return unicodedata.normalize("NFKC", character)
    return character


if __name__ == "__main__":
    main(sys.argv[1:])
