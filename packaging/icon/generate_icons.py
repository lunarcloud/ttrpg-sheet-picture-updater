"""Derives every packaged icon size/format from the single source image.

Only `icon-source.png` is a committed, hand-edited (or placeholder) file —
every output here is generated and gitignored, so there's never more than
one icon file to keep in sync by hand. See packaging/README.md for the
full rationale.

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
APP_ICON_NAME = "set-ttrpg-portrait.png"

# Size used for the AppImage's own icon.
APPIMAGE_ICON_SIZE = 256

# Windows .ico embedded in the PyInstaller-frozen .exe and the NSIS
# installer/uninstaller (multi-resolution, matching what Windows Explorer/
# taskbar request at different DPIs).
ICO_SIZES = (16, 32, 48, 64, 128, 256)

# macOS .iconset source sizes — Apple's required name/size pairs for
# `iconutil -c icns` (see build-macos.sh). The "@2x" variants are just a
# differently-named render of the next size up (e.g. icon_16x16@2x.png ==
# icon_32x32.png's pixels), per Apple's iconset convention.
MACOS_ICONSET_SIZES = (
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
)


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


def generate_windows_ico(source: Image.Image) -> None:
    """Multi-resolution .ico embedded in the Windows build's PyInstaller
    .exe and the NSIS installer/uninstaller (build-nsis.sh)."""
    out_dir = PACKAGING_DIR / "windows"
    out_dir.mkdir(parents=True, exist_ok=True)
    source.save(out_dir / "icon.ico", format="ICO", sizes=[(s, s) for s in ICO_SIZES])


def generate_macos_iconset(source: Image.Image) -> None:
    """Iconset PNGs consumed by build-macos.sh's icns conversion step
    (`iconutil` on macOS, or `png2icns` as a cross-platform fallback for
    local testing — see packaging/lib/make-icns.sh)."""
    out_dir = PACKAGING_DIR / "macos" / "AppIcon.iconset"
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, size in MACOS_ICONSET_SIZES:
        source.resize((size, size), Image.LANCZOS).save(out_dir / filename, format="PNG")


def main() -> None:
    source = _load_source()
    generate_hicolor_icons(source)
    generate_appimage_icon(source)
    generate_windows_ico(source)
    generate_macos_iconset(source)
    print(
        f"Generated icons for sizes {HICOLOR_SIZES} + AppImage icon + "
        f"Windows .ico + macOS iconset from {SOURCE_ICON}"
    )


if __name__ == "__main__":
    main()
