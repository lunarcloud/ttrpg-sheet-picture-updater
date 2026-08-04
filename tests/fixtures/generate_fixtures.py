"""Generates the small, IP-free, synthetic PDF/image fixtures used by tests.

These fixtures are our own originally-authored content — plain placeholder
text fields and pushbutton fields we construct ourselves with PyMuPDF, and a
simple programmatically-drawn image (not a real photo). They deliberately
mirror the *shapes* of real-world sheets we researched without copying any
of their layout, art, or text, so they're safe to commit and run in public
CI.

This script is run once, output is committed to `tests/fixtures/`; keep it
around so fixtures can be regenerated/extended later:

    .venv/bin/python tests/fixtures/generate_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pikepdf
from PIL import Image, ImageDraw

FIXTURES_DIR = Path(__file__).parent

PDF_WIDGET_TYPE_TEXT = fitz.PDF_WIDGET_TYPE_TEXT
PDF_WIDGET_TYPE_PUSHBUTTON = fitz.PDF_WIDGET_TYPE_BUTTON

PAGE_SIZE = (400, 500)


def _add_text_field(page: fitz.Page, name: str, rect: tuple[float, float, float, float]) -> None:
    widget = fitz.Widget()
    widget.field_name = name
    widget.field_type = PDF_WIDGET_TYPE_TEXT
    widget.rect = fitz.Rect(rect)
    page.add_widget(widget)


def _add_button_field(page: fitz.Page, name: str, rect: tuple[float, float, float, float]) -> None:
    widget = fitz.Widget()
    widget.field_name = name
    widget.field_type = PDF_WIDGET_TYPE_PUSHBUTTON
    widget.field_flags = 65536  # pushbutton flag, matches real-world sheets
    widget.rect = fitz.Rect(rect)
    page.add_widget(widget)


def make_simple_sheet() -> None:
    """One text field + one pushbutton field named "Portrait" (the common case)."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    _add_text_field(page, "Character Name", (20, 20, 300, 45))
    _add_button_field(page, "Portrait", (20, 60, 180, 220))
    doc.save(FIXTURES_DIR / "simple_sheet.pdf")
    doc.close()


def make_multi_field_sheet() -> None:
    """Several text fields + a less-obviously-named pushbutton field."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    _add_text_field(page, "Character Name", (20, 20, 300, 45))
    _add_text_field(page, "Class", (20, 50, 300, 75))
    _add_text_field(page, "Level", (20, 80, 300, 105))
    _add_button_field(page, "Pic1", (20, 120, 180, 280))
    doc.save(FIXTURES_DIR / "multi_field_sheet.pdf")
    doc.close()


def make_no_image_sheet() -> None:
    """Text fields only, no pushbutton field (mirrors ION HEART example)."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    _add_text_field(page, "Pilot Name", (20, 20, 300, 45))
    _add_text_field(page, "Mech Name", (20, 50, 300, 75))
    doc.save(FIXTURES_DIR / "no_image_sheet.pdf")
    doc.close()


def make_ambiguous_sheet() -> None:
    """Two pushbutton fields that both match the portrait-name heuristic."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    _add_text_field(page, "Character Name", (20, 20, 300, 45))
    _add_button_field(page, "Character Photo", (20, 60, 180, 220))
    _add_button_field(page, "Player Image", (200, 60, 360, 220))
    doc.save(FIXTURES_DIR / "ambiguous_sheet.pdf")
    doc.close()


def make_multi_location_sheet() -> None:
    """One "Portrait" field with two `/Kids` widgets of different shapes.

    Mirrors sheets where the same field is repeated across pages (see
    `fields.FieldCandidate`'s docstring) — here with deliberately
    different aspect ratios (a square vs. a wide rectangle) so tests can
    assert the portrait is fit/cropped separately per location instead of
    one shared fit being stretched to cover both.
    """
    pdf = pikepdf.new()
    page1 = pdf.add_blank_page(page_size=PAGE_SIZE)
    page2 = pdf.add_blank_page(page_size=PAGE_SIZE)

    field = pdf.make_indirect(pikepdf.Dictionary(FT=pikepdf.Name.Btn, Ff=65536, T="Portrait"))
    widget1 = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Annot,
            Subtype=pikepdf.Name.Widget,
            Rect=[20, 60, 180, 220],  # 160x160 square
            Parent=field,
            P=page1.obj,
        )
    )
    widget2 = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Annot,
            Subtype=pikepdf.Name.Widget,
            Rect=[20, 60, 340, 140],  # 320x80 wide rectangle
            Parent=field,
            P=page2.obj,
        )
    )
    field.Kids = [widget1, widget2]

    pdf.Root.AcroForm = pikepdf.Dictionary(Fields=[field])
    page1.obj.Annots = [widget1]
    page2.obj.Annots = [widget2]
    pdf.save(FIXTURES_DIR / "multi_location_sheet.pdf")
    pdf.close()


def make_portrait_images() -> None:
    """A small, original, programmatically-drawn placeholder "portrait".

    Simple shapes/gradient only — not a real photo, not project artwork,
    just a synthetic test fixture (see .github/copilot-instructions.md).
    """
    width, height = 300, 400
    image = Image.new("RGB", (width, height), color=(200, 220, 240))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        shade = int(120 + 100 * (y / height))
        draw.line([(0, y), (width, y)], fill=(shade, shade, 255))
    draw.ellipse((width * 0.25, height * 0.15, width * 0.75, height * 0.55), fill=(240, 200, 160))
    draw.rectangle((width * 0.2, height * 0.6, width * 0.8, height), fill=(80, 80, 200))
    image.save(FIXTURES_DIR / "portrait.jpg", format="JPEG", quality=90)
    image.save(FIXTURES_DIR / "portrait.png", format="PNG")
    # Lossless WebP so pixel values match the PNG exactly (see
    # make_transparent_portrait_image for the transparent counterpart) —
    # WebP is a fairly common export format for cut-out portraits and
    # should be handled identically to PNG.
    image.save(FIXTURES_DIR / "portrait.webp", format="WEBP", lossless=True)


def make_transparent_portrait_image() -> None:
    """A synthetic RGBA portrait with real transparency (fully + partial).

    Exercises the "flatten transparency onto white" behavior in
    `image_prep.load_portrait` (transparent PNGs/WebPs are the likely
    real-world case, e.g. a portrait cut out from its background). Simple
    shapes only — not a real photo, not project artwork.
    """
    width, height = 300, 400
    image = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Fully opaque circle "head".
    draw.ellipse(
        (width * 0.25, height * 0.15, width * 0.75, height * 0.55),
        fill=(240, 200, 160, 255),
    )
    # Fully transparent border stays transparent (should flatten to white).
    # Semi-transparent rectangle "body" to exercise alpha blending.
    draw.rectangle((width * 0.2, height * 0.6, width * 0.8, height), fill=(80, 80, 200, 128))
    image.save(FIXTURES_DIR / "portrait_transparent.png", format="PNG")
    # Lossless WebP keeps the same pixel values (including alpha) as the
    # PNG above, so both formats can be asserted against identically.
    image.save(FIXTURES_DIR / "portrait_transparent.webp", format="WEBP", lossless=True)


def main() -> None:
    make_simple_sheet()
    make_multi_field_sheet()
    make_multi_location_sheet()
    make_no_image_sheet()
    make_ambiguous_sheet()
    make_portrait_images()
    make_transparent_portrait_image()
    print(f"Fixtures written to {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
