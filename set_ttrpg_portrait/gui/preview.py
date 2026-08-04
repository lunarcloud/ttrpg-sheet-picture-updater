"""Renders a fillable PDF sheet's pages to an in-memory preview image.

Uses PyMuPDF (`fitz`) rather than Qt's own `QtPdf`/`QPdfView` module:
QtPdf does not render AcroForm field appearances at all (neither filled-in
values nor an embedded portrait icon), so it can't show the result of
what this tool just did.
"""

from __future__ import annotations

import fitz
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap

#: DPI used to rasterize preview pages — high enough to read comfortably,
#: low enough to render/scroll quickly for typical multi-page sheets.
PREVIEW_DPI = 150

#: Vertical gap (pixels) drawn between stacked page images in the preview.
PREVIEW_PAGE_GAP = 8


def load_page_images(pdf_path: str) -> list[QImage]:
    """Rasterize every page of `pdf_path` into a list of `QImage`s.

    May raise (e.g. `fitz`'s own exceptions) if the file can't be opened
    or rendered — left to the caller to handle as a best-effort preview.
    """
    with fitz.open(pdf_path) as doc:
        return [_page_to_qimage(page) for page in doc]


def stack_images(page_images: list[QImage]) -> QPixmap:
    """Stack page images vertically, centered, into one combined `QPixmap`."""
    width = max(image.width() for image in page_images)
    height = sum(image.height() for image in page_images) + PREVIEW_PAGE_GAP * (
        len(page_images) - 1
    )
    stacked = QImage(width, height, QImage.Format.Format_RGB32)
    stacked.fill(Qt.GlobalColor.gray)

    painter = QPainter(stacked)
    y = 0
    for image in page_images:
        x = (width - image.width()) // 2
        painter.drawImage(x, y, image)
        y += image.height() + PREVIEW_PAGE_GAP
    painter.end()

    return QPixmap.fromImage(stacked)


def scale_to_width(pixmap: QPixmap, width: int) -> QPixmap:
    """Scale `pixmap` to `width`, preserving aspect ratio.

    Used to fit the (potentially much higher-resolution) stacked preview
    to the scroll area's viewport width, so only vertical scrolling
    (between/through pages) is needed — never horizontal.
    """
    if width <= 0 or pixmap.isNull() or pixmap.width() == width:
        return pixmap
    return pixmap.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)


def _page_to_qimage(page: fitz.Page) -> QImage:
    zoom = PREVIEW_DPI / 72
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    image_format = (
        QImage.Format.Format_RGBA8888 if pixmap.alpha else QImage.Format.Format_RGB888
    )
    image = QImage(
        pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, image_format
    )
    return image.copy()
