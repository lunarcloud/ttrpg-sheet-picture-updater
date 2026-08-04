"""Portrait/image field discovery on fillable PDF sheets.

Character sheets authored in Adobe Acrobat use a "pushbutton" form field as
the portrait/photo placeholder (there's no plain image field type in the
AcroForm spec) — the button's on-page icon is normally set via Acrobat's
"Select Icon" UI (``/MK/I`` + ``/AP/N``, see `pdf_ops.py`). This module finds
that field by name heuristics so the rest of the tool knows which field(s)
to set the icon on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pikepdf

from set_ttrpg_portrait.errors import (
    AmbiguousFieldError,
    FieldNotFoundError,
    NoCandidateFieldError,
)

# Bit 17 (value 1<<16 = 65536) of a button field's /Ff flags marks it as a
# pushbutton (as opposed to a checkbox or radio button, which use other Ff
# bits). This matches every real-world sheet inspected while researching
# this tool.
PDF_PUSHBUTTON_FLAG = 1 << 16

# Field names that plausibly hold a character portrait/photo, matched
# case-insensitively against the whole field name. Only ever applied to
# fields already filtered down to pushbuttons (see `_is_pushbutton_field`),
# so a broad word like "appearance" is safe here — it can't accidentally
# match an unrelated text field.
PORTRAIT_FIELD_NAME_PATTERN = re.compile(
    r"portrait|character\s*image|photo|headshot|player\s*image|appearance|^image$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FieldLocation:
    """Where one widget annotation for a field is drawn."""

    page_index: int
    rect: tuple[float, float, float, float]  # (x0, y0, x1, y1)


@dataclass(frozen=True)
class FieldCandidate:
    """A pushbutton field found on the sheet, by name + every place it's drawn.

    A field is usually a single widget annotation (one location), but some
    sheets attach the same field to several widget annotations (e.g. one
    field repeated across pages, or stacked on one page) — every such
    "kid" is captured in ``locations`` so the icon can be set on all of
    them.
    """

    name: str
    locations: tuple[FieldLocation, ...]


def is_portrait_field_name(name: str) -> bool:
    """Return True if ``name`` looks like a portrait/photo field name.

    Pure string check (no PDF I/O) so the heuristic itself is trivial to
    unit test without constructing a real document.
    """
    return bool(PORTRAIT_FIELD_NAME_PATTERN.search(name))


def _is_pushbutton_field(field: pikepdf.Object) -> bool:
    field_type = field.get("/FT")
    flags = int(field.get("/Ff", 0))
    return (
        field_type is not None
        and str(field_type) == "/Btn"
        and bool(flags & PDF_PUSHBUTTON_FLAG)
    )


def _page_index_by_objgen(pdf: pikepdf.Pdf) -> dict[tuple[int, int], int]:
    """Map every widget annotation's objgen to its owning page's 0-based index.

    Built from each page's ``/Annots`` array rather than an annotation's
    ``/P`` entry, because ``/P`` is optional in the PDF spec and not every
    PDF author (including some of our own test-fixture generation code)
    sets it — walking ``/Annots`` works regardless.
    """
    lookup: dict[tuple[int, int], int] = {}
    for index, page in enumerate(pdf.pages):
        for annot in page.get("/Annots", []):
            lookup[annot.objgen] = index
    return lookup


def _field_locations(
    field: pikepdf.Object, page_lookup: dict[tuple[int, int], int]
) -> tuple[FieldLocation, ...]:
    """Collect every widget annotation's page/rect for a top-level field.

    A field is either "merged" (the field dict is itself the one widget
    annotation, carrying its own ``/Rect``) or has ``/Kids`` (a list of
    separate widget annotation dicts, each with their own ``/Rect``).
    """
    if "/Rect" in field:
        annots = [field]
    elif "/Kids" in field:
        annots = list(field.Kids)
    else:
        return ()

    locations = []
    for annot in annots:
        if "/Rect" not in annot:
            continue
        page_index = page_lookup.get(annot.objgen)
        if page_index is None:
            continue
        rect = tuple(float(v) for v in annot.Rect)
        locations.append(FieldLocation(page_index=page_index, rect=rect))
    return tuple(locations)


def find_button_fields(
    pdf: pikepdf.Pdf, page_index: int | None = None
) -> list[FieldCandidate]:
    """Return every pushbutton form field in ``pdf``.

    If ``page_index`` is given, only widget annotations on that page are
    considered, and fields with no annotation on that page are omitted.
    """
    page_lookup = _page_index_by_objgen(pdf)
    candidates: list[FieldCandidate] = []
    acroform = pdf.Root.get("/AcroForm")
    if acroform is None or "/Fields" not in acroform:
        return candidates

    for field in acroform.Fields:
        if "/T" not in field or not _is_pushbutton_field(field):
            continue
        locations = _field_locations(field, page_lookup)
        if page_index is not None:
            locations = tuple(loc for loc in locations if loc.page_index == page_index)
        if not locations:
            continue
        candidates.append(FieldCandidate(name=str(field.T), locations=locations))
    return candidates


def find_portrait_field(
    pdf: pikepdf.Pdf,
    field_name: str | None = None,
    page_index: int | None = None,
) -> FieldCandidate:
    """Locate the single field to set the portrait icon on.

    If ``field_name`` is given, an exact (case-sensitive) name match is
    required. Otherwise, all pushbutton fields are scored against the
    portrait-name heuristic; exactly one match is required to proceed
    automatically.
    """
    all_buttons = find_button_fields(pdf, page_index)

    if field_name is not None:
        for candidate in all_buttons:
            if candidate.name == field_name:
                return candidate
        raise FieldNotFoundError(
            f"No pushbutton field named {field_name!r} was found on the sheet."
        )

    matches = [c for c in all_buttons if is_portrait_field_name(c.name)]

    if not matches:
        raise NoCandidateFieldError(
            "No portrait/image field could be auto-detected on this sheet. "
            "Use --list-fields to see all pushbutton fields, then rerun with "
            "--field NAME."
        )
    if len(matches) > 1:
        match_names = tuple(c.name for c in matches)
        names = ", ".join(repr(name) for name in match_names)
        raise AmbiguousFieldError(
            f"Multiple candidate portrait fields were found ({names}). "
            "Rerun with --field NAME to disambiguate.",
            field_names=match_names,
        )
    return matches[0]
