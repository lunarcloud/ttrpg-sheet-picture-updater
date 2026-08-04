"""PDF-level operations: opening sheets and setting a pushbutton's icon.

Character sheets keep the portrait/photo field as a live, still-clickable
pushbutton after the image is applied (matching how Adobe Acrobat's own
"Select Icon" feature works) rather than flattening the portrait into the
page content and discarding the field. This is done by building:

  1. An Image XObject holding the portrait's raw JPEG bytes.
  2. A small Form XObject ("FRM") that draws that image at its native size
     — this becomes the field's ``/MK/I`` (icon) entry.
  3. A Form XObject appearance ("AP/N") that clips to the widget's
     rectangle and scales/positions the icon within it.

This mirrors the exact object structure produced by Acrobat itself (found
by inspecting real sheets while researching this tool — see plan.md).
"""

from __future__ import annotations

import io

import pikepdf
from pikepdf import Dictionary, Name, Stream
from PIL import Image

from update_portrait.errors import InvalidPdfError
from update_portrait.fields import FieldCandidate


def open_sheet(path: str) -> pikepdf.Pdf:
    """Open the fillable PDF sheet, raising a clear error if that fails."""
    try:
        pdf = pikepdf.open(path)
    except FileNotFoundError as exc:
        raise InvalidPdfError(f"Sheet PDF not found: {path!r}") from exc
    except pikepdf.PasswordError as exc:
        raise InvalidPdfError(
            f"{path!r} is password-protected; decrypt it first."
        ) from exc
    except pikepdf.PdfError as exc:
        raise InvalidPdfError(f"Could not open PDF {path!r}: {exc}") from exc
    if pdf.is_encrypted:
        raise InvalidPdfError(
            f"{path!r} is password-protected/encrypted; decrypt it first."
        )
    return pdf


def _find_field(pdf: pikepdf.Pdf, name: str) -> pikepdf.Object:
    """Re-locate the live field object matching a `FieldCandidate`'s name."""
    acroform = pdf.Root.get("/AcroForm")
    if acroform is not None and "/Fields" in acroform:
        for field in acroform.Fields:
            if "/T" in field and str(field.T) == name:
                return field
    raise InvalidPdfError(
        f"Field {name!r} could not be re-located; the document may have "
        "changed since it was scanned."
    )


def _widget_annotations(field: pikepdf.Object) -> list[pikepdf.Object]:
    """Return the widget annotation dict(s) to set an icon on for `field`.

    A field is either "merged" (the field dict is itself the widget
    annotation) or has ``/Kids`` (separate widget annotation dicts).
    """
    if "/Rect" in field:
        return [field]
    if "/Kids" in field:
        return list(field.Kids)
    return []


def _build_image_xobject(
    pdf: pikepdf.Pdf, jpeg_bytes: bytes, width: int, height: int
) -> pikepdf.Object:
    image = Stream(pdf, jpeg_bytes)
    image.Type = Name.XObject
    image.Subtype = Name.Image
    image.Width = width
    image.Height = height
    image.ColorSpace = Name.DeviceRGB
    image.BitsPerComponent = 8
    image.Filter = Name.DCTDecode
    return image


def _build_icon_form(
    pdf: pikepdf.Pdf, image_xobject: pikepdf.Object, width: int, height: int
) -> pikepdf.Object:
    """Build the Form XObject used as the field's ``/MK/I`` icon.

    Draws the image at its native pixel size into a unit-per-pixel BBox;
    the appearance form (`_build_appearance_form`) scales it down to fit
    the widget's actual on-page rectangle.
    """
    content = f"q\n{width} 0 0 {height} 0 0 cm\n/Im0 Do\nQ\n".encode()
    form = Stream(pdf, content)
    form.Type = Name.XObject
    form.Subtype = Name.Form
    form.FormType = 1
    form.BBox = [0, 0, width, height]
    form.Resources = Dictionary(
        ProcSet=[Name.PDF, Name.ImageC], XObject=Dictionary(Im0=image_xobject)
    )
    form.Name = Name("/FRM")
    return form


def _build_appearance_form(
    pdf: pikepdf.Pdf,
    icon_form: pikepdf.Object,
    rect_width: float,
    rect_height: float,
    image_width: int,
    image_height: int,
) -> pikepdf.Object:
    """Build the field's ``/AP/N`` appearance stream: clip + scale the icon."""
    scale_x = rect_width / image_width
    scale_y = rect_height / image_height
    content = (
        f"q\n0 0 {rect_width} {rect_height} re\nW\nn\n"
        f"{scale_x} 0 0 {scale_y} 0 0 cm\n/FRM Do\nQ\n"
    ).encode()
    form = Stream(pdf, content)
    form.Type = Name.XObject
    form.Subtype = Name.Form
    form.FormType = 1
    form.BBox = [0, 0, rect_width, rect_height]
    form.Matrix = [1, 0, 0, 1, 0, 0]
    form.Resources = Dictionary(ProcSet=[Name.PDF], XObject=Dictionary(FRM=icon_form))
    return form


def set_field_icon(
    pdf: pikepdf.Pdf,
    candidate: FieldCandidate,
    portrait_jpeg_bytes: bytes,
) -> None:
    """Set the portrait as the icon on every widget annotation for a field.

    The field stays a fully live, clickable pushbutton field afterwards —
    exactly like Acrobat's own "Select Icon" feature — so it remains
    replaceable later (in Acrobat or by re-running this tool). Every other
    form field in the document is left untouched.

    The image's pixel dimensions are read from the JPEG bytes themselves
    (via Pillow), so callers never need to track width/height separately
    from the encoded bytes.
    """
    field = _find_field(pdf, candidate.name)
    annotations = _widget_annotations(field)
    if not annotations:
        raise InvalidPdfError(
            f"Field {candidate.name!r} has neither /Rect nor /Kids; can't "
            "place an icon on it."
        )

    image_width, image_height = Image.open(io.BytesIO(portrait_jpeg_bytes)).size
    image_xobject = _build_image_xobject(
        pdf, portrait_jpeg_bytes, image_width, image_height
    )
    icon_form = _build_icon_form(pdf, image_xobject, image_width, image_height)

    for annotation in annotations:
        rect = [float(v) for v in annotation.Rect]
        rect_width, rect_height = rect[2] - rect[0], rect[3] - rect[1]
        appearance_form = _build_appearance_form(
            pdf, icon_form, rect_width, rect_height, image_width, image_height
        )
        annotation.MK = Dictionary(I=icon_form, TP=1)
        annotation.AP = Dictionary(N=appearance_form)


def save_sheet(pdf: pikepdf.Pdf, output_path: str) -> None:
    """Save the edited document."""
    pdf.save(output_path)
