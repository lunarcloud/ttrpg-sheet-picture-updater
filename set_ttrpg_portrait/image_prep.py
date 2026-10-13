"""Portrait image preparation: orientation fix, resizing/cropping to fit.

Kept independent of PDF/`fitz` code so the resize/fit math is a plain,
pure-ish transform on Pillow ``Image`` objects and is easy to unit test in
isolation from any PDF handling.
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageOps

from set_ttrpg_portrait.errors import SvgSupportUnavailableError

#: Default JPEG quality used when re-encoding the fitted portrait for
#: embedding into the sheet. Adobe Acrobat's own "Select Icon" feature
#: embeds icons at quality 100 with no chroma subsampling (4:4:4) — using
#: the same here keeps sharp edges/text in the portrait (e.g. faction
#: symbols, line art) crisp instead of visibly softened by 4:2:0 color
#: blur, matching that reference output.
JPEG_QUALITY = 100

#: Chroma subsampling mode passed to Pillow's JPEG encoder: 0 = 4:4:4 (no
#: chroma downsampling). Pillow's default (4:2:0) halves color resolution,
#: which noticeably blurs saturated color edges compared to Acrobat's
#: output.
JPEG_SUBSAMPLING = 0

#: Background color used to flatten transparent images (JPEG has no alpha
#: channel), and to letterbox "contain"-fit images.
WHITE_BACKGROUND = (255, 255, 255)

#: PDF page geometry (field ``/Rect`` values) is in points (1/72 inch).
#: Fitting the portrait to that pixel-for-point size would embed a
#: postage-stamp-resolution image (e.g. ~137x151px for a typical portrait
#: field) that looks visibly soft/blurry once zoomed in or printed —
#: noticeably softer than Adobe Acrobat's own "Select Icon" output, which
#: embeds the icon at a much higher pixel density than the on-page
#: rectangle and scales it down for display. Oversampling to this DPI
#: before fitting keeps the embedded icon sharp at zoom/print time; the
#: PDF appearance stream still scales it down to the exact field size, so
#: on-screen layout is unaffected.
DEFAULT_ICON_DPI = 300

#: Points per inch, per the PDF spec (used to convert a field's ``/Rect``
#: size in points to a target pixel size at a given DPI).
POINTS_PER_INCH = 72.0

#: DPI used to rasterize SVG portraits (see `_rasterize_svg`) before the
#: normal fit/encode pipeline runs. SVGs have no intrinsic pixel size, so
#: this is just a generously high fixed resolution — `fit_image()` still
#: downscales/crops to the field's actual target size afterward.
SVG_RASTER_DPI = 300

#: DPI an SVG's unitless (plain-number, e.g. ``width="300"``) dimensions
#: are defined in, per the CSS/SVG spec. cairosvg's own ``dpi`` argument
#: only rescales *physical*-unit dimensions (mm/cm/in/pt); unitless ones
#: (the common case for exported character-builder SVGs) need `scale`
#: instead, computed relative to this baseline.
CSS_REFERENCE_DPI = 96.0

FitMode = str  # "cover" or "contain"


def points_to_pixels(points: tuple[float, float], dpi: float = DEFAULT_ICON_DPI) -> tuple[float, float]:
    """Convert a ``(width, height)`` pair in PDF points to pixels at ``dpi``."""
    scale = dpi / POINTS_PER_INCH
    return (points[0] * scale, points[1] * scale)


@lru_cache(maxsize=1)
def svg_support_available() -> bool:
    """Whether SVG portraits can be rasterized on this machine.

    Attempts the same import `_rasterize_svg()` needs, cached so the
    (slow-ish, native-library-probing) check only happens once per process.
    Callers that want to preemptively hide/reject SVG input (e.g. the GUI's
    file picker/drag-and-drop) can check this instead of waiting for
    `_rasterize_svg()` to raise.
    """
    try:
        import cairosvg  # noqa: F401
    except OSError:
        return False
    return True


def _rasterize_svg(path: str, dpi: float = SVG_RASTER_DPI) -> Image.Image:
    """Rasterize an SVG file to a Pillow RGBA image at ``dpi``.

    Pillow can't open SVGs (a vector format, not a bitmap). cairosvg is
    used instead of PyMuPDF's own (also-available) SVG renderer because
    the latter ignores embedded ``<style>`` CSS blocks and doesn't resolve
    ``currentColor`` — both common in character-builder-exported SVGs —
    silently rendering every such fill as black.

    cairosvg is imported here, not at module scope, because it loads its
    native Cairo library via ``ctypes`` as soon as it's imported. The
    frozen AppImage/MSIX/.dmg builds don't bundle or declare that native
    library, so importing it eagerly would crash the whole app on startup
    on a machine without Cairo installed, instead of only failing to load
    this one SVG.
    """
    if not svg_support_available():
        raise SvgSupportUnavailableError(
            "SVG support requires Cairo's native library, which isn't "
            "installed/loadable on this machine. Install Cairo (e.g. via "
            "Homebrew on macOS, or your Linux distro's libcairo2/cairo "
            "package) or convert the portrait to PNG/JPEG instead."
        )
    import cairosvg

    png_bytes = cairosvg.svg2png(url=path, scale=dpi / CSS_REFERENCE_DPI)
    return Image.open(io.BytesIO(png_bytes))


def load_portrait(path: str) -> Image.Image:
    """Open a portrait image file and normalize its orientation/color mode.

    Applies EXIF-based auto-rotation (many phone cameras store portrait
    photos rotated with an EXIF orientation tag rather than pre-rotated
    pixels) and converts to RGB so JPEG re-encoding always works, regardless
    of the input format (JPEG, PNG, SVG, etc.).

    Images with an alpha channel (e.g. transparent PNGs — the likely case
    for portraits cut out from a background) are **composited onto an
    opaque white background** rather than naively dropped. JPEG/DCTDecode
    (used for the embedded icon) has no alpha support, and a plain
    ``.convert("RGB")`` on an RGBA image discards the alpha channel without
    blending, which can leave garbage-colored pixels showing through
    fully- or partially-transparent regions.
    """
    image = _rasterize_svg(path) if Path(path).suffix.lower() == ".svg" else Image.open(path)
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, WHITE_BACKGROUND)
        background.paste(image, mask=image.getchannel("A"))
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    return image


def fit_image(
    image: Image.Image,
    target_size: tuple[float, float],
    mode: FitMode = "cover",
) -> Image.Image:
    """Resize ``image`` to exactly ``target_size``, per ``mode``.

    - "cover": scale to fill the target, cropping any overflow (no
      letterboxing; some of the image's edges may be trimmed).
    - "contain": scale to fit entirely within the target, padding with
      white letterboxing bars so nothing is cropped.
    """
    if mode not in ("cover", "contain"):
        raise ValueError(f"Unknown fit mode: {mode!r}")

    target_w, target_h = (round(target_size[0]), round(target_size[1]))
    if target_w <= 0 or target_h <= 0:
        raise ValueError(f"Invalid target size: {target_size!r}")

    if mode == "cover":
        fitted = ImageOps.fit(image, (target_w, target_h), method=Image.LANCZOS)
    else:
        contained = ImageOps.contain(image, (target_w, target_h), method=Image.LANCZOS)
        fitted = Image.new("RGB", (target_w, target_h), color=WHITE_BACKGROUND)
        offset = (
            (target_w - contained.width) // 2,
            (target_h - contained.height) // 2,
        )
        fitted.paste(contained, offset)
    return fitted


def image_to_jpeg_bytes(image: Image.Image, quality: int = JPEG_QUALITY) -> bytes:
    """Encode ``image`` as JPEG bytes suitable for embedding into a PDF page."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, subsampling=JPEG_SUBSAMPLING)
    return buffer.getvalue()


def prepare_portrait_jpeg(
    path: str,
    target_size: tuple[float, float],
    mode: FitMode = "cover",
) -> bytes:
    """Load, orient, fit, and encode a portrait file in one step."""
    image = load_portrait(path)
    fitted = fit_image(image, target_size, mode)
    return image_to_jpeg_bytes(fitted)
