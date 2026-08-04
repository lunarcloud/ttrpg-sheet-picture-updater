"""Portrait image preparation: orientation fix, resizing/cropping to fit.

Kept independent of PDF/`fitz` code so the resize/fit math is a plain,
pure-ish transform on Pillow ``Image`` objects and is easy to unit test in
isolation from any PDF handling.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps

#: Default JPEG quality used when re-encoding the fitted portrait for
#: embedding into the sheet.
JPEG_QUALITY = 90

#: Background color used to flatten transparent images (JPEG has no alpha
#: channel), and to letterbox "contain"-fit images.
WHITE_BACKGROUND = (255, 255, 255)

FitMode = str  # "cover" or "contain"


def load_portrait(path: str) -> Image.Image:
    """Open a portrait image file and normalize its orientation/color mode.

    Applies EXIF-based auto-rotation (many phone cameras store portrait
    photos rotated with an EXIF orientation tag rather than pre-rotated
    pixels) and converts to RGB so JPEG re-encoding always works, regardless
    of the input format (JPEG, PNG, etc.).

    Images with an alpha channel (e.g. transparent PNGs — the likely case
    for portraits cut out from a background) are **composited onto an
    opaque white background** rather than naively dropped. JPEG/DCTDecode
    (used for the embedded icon) has no alpha support, and a plain
    ``.convert("RGB")`` on an RGBA image discards the alpha channel without
    blending, which can leave garbage-colored pixels showing through
    fully- or partially-transparent regions.
    """
    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
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
    image.save(buffer, format="JPEG", quality=quality)
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
