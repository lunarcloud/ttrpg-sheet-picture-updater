"""Shared "do the thing" entry point used by both the CLI and the GUI.

Keeps `cli.py` (argument parsing) and `gui.py` (Qt widgets) both thin by
giving them one non-interactive function to call: open the sheet, find the
portrait field, fit/encode the portrait image, embed it, and save.
"""

from __future__ import annotations

from set_ttrpg_portrait.fields import find_portrait_field
from set_ttrpg_portrait.image_prep import (
    DEFAULT_ICON_DPI,
    points_to_pixels,
    prepare_portrait_jpeg,
)
from set_ttrpg_portrait.pdf_ops import open_sheet, save_sheet, set_field_icon


def apply_portrait(
    sheet_path: str,
    portrait_path: str,
    output_path: str,
    *,
    field: str | None = None,
    page: int | None = None,
    fit: str = "cover",
    dpi: float = DEFAULT_ICON_DPI,
) -> str:
    """Embed ``portrait_path`` into ``sheet_path``'s portrait field, save to ``output_path``.

    Raises `set_ttrpg_portrait.errors.SetTtrpgPortraitError` (or a
    `FileNotFoundError` for a missing portrait file) on any expected
    failure; callers turn that into a CLI exit code or a GUI dialog.

    Returns ``output_path`` on success, for convenient chaining.
    """
    pdf = open_sheet(sheet_path)
    candidate = find_portrait_field(pdf, field, page)
    rect = candidate.locations[0].rect
    rect_points = (rect[2] - rect[0], rect[3] - rect[1])
    portrait_bytes = prepare_portrait_jpeg(
        portrait_path,
        target_size=points_to_pixels(rect_points, dpi=dpi),
        mode=fit,
    )
    set_field_icon(pdf, candidate, portrait_bytes)
    save_sheet(pdf, output_path)
    return output_path
