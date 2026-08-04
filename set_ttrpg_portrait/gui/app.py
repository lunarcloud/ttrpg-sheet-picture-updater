"""GUI entry point: builds the QApplication and shows `MainWindow`."""

from __future__ import annotations

import os
import sys

from PyQt6.QtWidgets import QApplication

from set_ttrpg_portrait.gui.icon import app_icon
from set_ttrpg_portrait.gui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    """Entry point used by both `set_ttrpg_portrait_gui.py` and `python -m set_ttrpg_portrait.gui`."""
    # Prefer the XDG Desktop Portal's file chooser (org.freedesktop.portal.
    # FileChooser) over Qt's own built-in dialog, so "Browse…"/"Save As…"
    # show the user's actual desktop environment's native file picker (GTK
    # file chooser on GNOME, Dolphin's on KDE, etc.) under both X11 and
    # Wayland — this also matches what Flatpak/sandboxed apps do. Only set
    # as a *default*: an explicit QT_QPA_PLATFORMTHEME from the user's
    # environment (e.g. "gtk3", "qt6ct") always wins. Requires the
    # `xdg-desktop-portal` service (+ a desktop-specific backend) to be
    # running, which is standard on modern desktop Linux distros; falls
    # back to Qt's own dialog if it isn't available.
    os.environ.setdefault("QT_QPA_PLATFORMTHEME", "xdgdesktopportal")
    app = QApplication(argv if argv is not None else sys.argv)
    # Without this, launching outside a `.desktop` entry (e.g. running the
    # AppImage/frozen binary directly, or `python -m set_ttrpg_portrait.gui`
    # in dev) shows a generic X11/Wayland window icon instead of our own.
    icon = app_icon()
    app.setWindowIcon(icon)
    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    return app.exec()
