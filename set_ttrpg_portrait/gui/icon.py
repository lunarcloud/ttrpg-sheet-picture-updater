"""Window icon lookup so the GUI isn't shown with a generic X11/Wayland icon."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon

#: freedesktop icon theme name installed by the .deb/.rpm (see
#: packaging/nfpm.yaml + packaging/set-ttrpg-portrait-gui.desktop's
#: `Icon=` key) — used first so installed packages pick up the user's
#: icon theme (light/dark variants, HiDPI sizes, etc).
ICON_THEME_NAME = "set-ttrpg-portrait"

#: Bundled fallback icon filename, used when no matching theme icon is
#: installed (e.g. running from source, or the AppImage/PyInstaller-frozen
#: binary, neither of which registers a system-wide icon theme entry).
#: Matches the single committed `packaging/icon/icon-source.png` name so
#: the `.spec` files can bundle it unrenamed (PyInstaller's `datas` copies
#: files under their original name).
BUNDLED_ICON_FILENAME = "icon-source.png"


def bundled_icon_path() -> Path | None:
    """Locate the fallback icon file bundled alongside this module/binary.

    Handles three cases: a PyInstaller-frozen build (file placed next to
    the executable via the `.spec` files' `datas`), and running directly
    from the repo source tree (falls back to the single committed
    `packaging/icon/icon-source.png`).
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = base / BUNDLED_ICON_FILENAME
        if candidate.is_file():
            return candidate
    # This file lives at set_ttrpg_portrait/gui/icon.py, so three `.parent`s
    # reach the repo root.
    repo_icon = Path(__file__).resolve().parent.parent.parent / "packaging" / "icon" / BUNDLED_ICON_FILENAME
    if repo_icon.is_file():
        return repo_icon
    return None


def app_icon() -> QIcon:
    """Best-effort window icon so windows aren't shown with a generic X11/Wayland icon.

    Without a `.desktop` entry (or its `Icon=` key) telling the window
    manager which icon to use, unset `QIcon`s fall back to a generic
    placeholder. Prefers the installed icon theme entry (works for
    .deb/.rpm installs); falls back to a bundled/source-tree file
    otherwise (AppImage, PyInstaller-frozen binary, or running from
    source).
    """
    icon = QIcon.fromTheme(ICON_THEME_NAME)
    if not icon.isNull():
        return icon
    path = bundled_icon_path()
    if path is not None:
        return QIcon(str(path))
    return QIcon()
