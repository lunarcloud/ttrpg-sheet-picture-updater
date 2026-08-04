"""Shared "do the thing" entry point used by both the CLI and the GUI.

Keeps `cli.py` (argument parsing) and `gui.py` (Qt widgets) both thin by
giving them one non-interactive function to call: open the sheet, find the
portrait field, fit/encode the portrait image, embed it, and save.
"""

from __future__ import annotations

from set_ttrpg_portrait.fields import find_portrait_field
from set_ttrpg_portrait.image_prep import (
    DEFAULT_ICON_DPI,
    fit_image,
    image_to_jpeg_bytes,
    load_portrait,
    points_to_pixels,
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
    with open_sheet(sheet_path) as pdf:
        candidate = find_portrait_field(pdf, field, page)
        portrait_image = load_portrait(portrait_path)
        # Fit/crop the portrait separately to each widget annotation's own
        # rectangle, rather than sharing one fit across all of them — a field
        # can have more than one location (see `FieldCandidate.locations`),
        # and those locations aren't guaranteed to share the same aspect
        # ratio (e.g. the same field repeated across pages at different
        # sizes). Sharing a single fit would force `set_field_icon` to stretch
        # it non-uniformly to cover a differently-shaped rectangle.
        portrait_jpegs = tuple(
            image_to_jpeg_bytes(
                fit_image(
                    portrait_image,
                    target_size=points_to_pixels(_rect_size(loc.rect), dpi=dpi),
                    mode=fit,
                )
            )
            for loc in candidate.locations
        )
        set_field_icon(pdf, candidate, portrait_jpegs)
        save_sheet(pdf, output_path)
    return output_path


def _rect_size(rect: tuple[float, float, float, float]) -> tuple[float, float]:
    """Return a field rectangle's ``(width, height)`` in PDF points."""
    return (rect[2] - rect[0], rect[3] - rect[1])
