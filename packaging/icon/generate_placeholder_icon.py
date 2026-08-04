"""Generates the placeholder master icon (safe-zone guide), not real artwork.

This script produces a *guide* image — simple shapes/text marking safe
zones — so whoever draws the real icon knows exactly which file to draw it
in (`icon-source.png`) and what area is safe from cropping/rounding when
packagers turn it into a Linux app icon (hicolor theme sizes, AppImage
icon, etc. — see `generate_icons.py`).

Run once; output is committed as a placeholder until replaced with real art:

    .venv/bin/python packaging/icon/generate_placeholder_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ICON_DIR = Path(__file__).parent
SIZE = 512
MARGIN = 24


def make_placeholder_icon() -> Image.Image:
    image = Image.new("RGB", (SIZE, SIZE), color=(235, 235, 235))
    draw = ImageDraw.Draw(image)

    # Full-canvas border: the absolute edge of the icon file.
    draw.rectangle((0, 0, SIZE - 1, SIZE - 1), outline=(150, 150, 150), width=2)

    # "Safe zone" circle: many launchers/icon themes mask icons to a circle
    # or rounded square, so content outside this circle may be clipped.
    safe_r = SIZE // 2 - MARGIN
    center = SIZE // 2
    draw.ellipse(
        (center - safe_r, center - safe_r, center + safe_r, center + safe_r),
        outline=(90, 90, 200),
        width=4,
    )

    # Crosshairs through the center, for alignment.
    draw.line((center, MARGIN, center, SIZE - MARGIN), fill=(200, 120, 120), width=2)
    draw.line((MARGIN, center, SIZE - MARGIN, center), fill=(200, 120, 120), width=2)

    # Corner ticks marking the outer margin used by square-icon contexts.
    for x, y in (
        (MARGIN, MARGIN),
        (SIZE - MARGIN, MARGIN),
        (MARGIN, SIZE - MARGIN),
        (SIZE - MARGIN, SIZE - MARGIN),
    ):
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(90, 90, 200))

    label = "REPLACE WITH ARTWORK"
    bbox = draw.textbbox((0, 0), label)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (center - text_w / 2, center - text_h / 2),
        label,
        fill=(90, 90, 90),
    )
    return image


def main() -> None:
    image = make_placeholder_icon()
    image.save(ICON_DIR / "icon-source.png", format="PNG")
    print(f"Placeholder icon written to {ICON_DIR / 'icon-source.png'}")


if __name__ == "__main__":
    main()
