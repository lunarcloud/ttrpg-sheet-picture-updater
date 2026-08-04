"""Unit tests for set_ttrpg_portrait.pdf_ops (icon embedding on the AcroForm)."""

from __future__ import annotations

from pathlib import Path

import pikepdf
import pytest

from set_ttrpg_portrait.core import apply_portrait
from set_ttrpg_portrait.errors import InvalidPdfError
from set_ttrpg_portrait.fields import find_portrait_field
from set_ttrpg_portrait.pdf_ops import set_field_icon

FIXTURES = Path(__file__).parent / "fixtures"


def _icon_size(widget: pikepdf.Object) -> tuple[int, int]:
    image = widget.MK.I.Resources.XObject.Im0
    return int(image.Width), int(image.Height)


def test_multi_location_field_gets_undistorted_icon_per_location(tmp_path) -> None:
    """A field with differently-shaped `/Kids` gets a separately-fit icon each.

    `multi_location_sheet.pdf` has one "Portrait" field with two widget
    annotations: a 160x160 square (page 0) and a 320x80 wide rectangle
    (page 1). Each embedded icon's pixel aspect ratio should match its own
    widget's rectangle aspect ratio — sharing one fit across both would
    force one of them to be stretched non-uniformly.
    """
    output = tmp_path / "out.pdf"
    apply_portrait(
        str(FIXTURES / "multi_location_sheet.pdf"),
        str(FIXTURES / "portrait.jpg"),
        str(output),
        field="Portrait",
    )

    pdf = pikepdf.open(output)
    field = next(f for f in pdf.Root.AcroForm.Fields if str(f.T) == "Portrait")
    assert len(field.Kids) == 2

    for widget in field.Kids:
        rect = [float(v) for v in widget.Rect]
        rect_ratio = (rect[2] - rect[0]) / (rect[3] - rect[1])
        image_width, image_height = _icon_size(widget)
        icon_ratio = image_width / image_height
        assert icon_ratio == pytest.approx(rect_ratio, rel=0.02)


def test_set_field_icon_rejects_mismatched_jpeg_count() -> None:
    """A wrong-length ``portrait_jpegs`` sequence is a clear, caught error.

    `set_field_icon()` expects one already-fitted JPEG per widget
    annotation (see `core.apply_portrait`); passing the wrong count is a
    programming error we want to fail loudly with a specific message
    rather than silently zip()-truncating or raising an unrelated
    `IndexError`.
    """
    pdf = pikepdf.open(FIXTURES / "multi_location_sheet.pdf")
    candidate = find_portrait_field(pdf, field_name="Portrait")
    one_jpeg = (Path(FIXTURES / "portrait.jpg").read_bytes(),)

    with pytest.raises(InvalidPdfError, match="2 widget annotation"):
        set_field_icon(pdf, candidate, one_jpeg)
