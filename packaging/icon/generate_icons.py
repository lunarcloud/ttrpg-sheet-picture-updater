"""Derives every packaged icon size/format from the single source image.

Only `icon-source.png` is a committed, hand-edited (or placeholder) file —
every output here is generated and gitignored, so there's never more than
one icon file to keep in sync by hand. See "Distribution / Packaging" in
plan.md for the full rationale.

Run before building `.deb`/`.rpm`/AppImage packages:

    .venv/bin/python packaging/icon/generate_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ICON_DIR = Path(__file__).parent
PACKAGING_DIR = ICON_DIR.parent
SOURCE_ICON = ICON_DIR / "icon-source.png"

# freedesktop hicolor icon theme sizes installed by the .deb/.rpm so the
# icon renders correctly in Linux app menus/file managers at every size
# they request.
HICOLOR_SIZES = (16, 32, 48, 64, 128, 256)
APP_ICON_NAME = "update-portrait.png"

# Size used for the AppImage's own icon.
APPIMAGE_ICON_SIZE = 256


def _load_source() -> Image.Image:
    if not SOURCE_ICON.exists():
        raise FileNotFoundError(
            f"{SOURCE_ICON} not found. Run "
            "packaging/icon/generate_placeholder_icon.py first (or supply "
            "real artwork) before generating derived icon sizes."
        )
    return Image.open(SOURCE_ICON).convert("RGBA")


def generate_hicolor_icons(source: Image.Image) -> None:
    for size in HICOLOR_SIZES:
        out_dir = PACKAGING_DIR / "icons" / "hicolor" / f"{size}x{size}" / "apps"
        out_dir.mkdir(parents=True, exist_ok=True)
        resized = source.resize((size, size), Image.LANCZOS)
        resized.save(out_dir / APP_ICON_NAME, format="PNG")


def generate_appimage_icon(source: Image.Image) -> None:
    out_dir = PACKAGING_DIR / "appimage"
    out_dir.mkdir(parents=True, exist_ok=True)
    resized = source.resize((APPIMAGE_ICON_SIZE, APPIMAGE_ICON_SIZE), Image.LANCZOS)
    resized.save(out_dir / "icon.png", format="PNG")


def main() -> None:
    source = _load_source()
    generate_hicolor_icons(source)
    generate_appimage_icon(source)
    print(
        f"Generated icons for sizes {HICOLOR_SIZES} + AppImage icon from {SOURCE_ICON}"
    )


if __name__ == "__main__":
    main()
