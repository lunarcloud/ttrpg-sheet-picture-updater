"""Tests for the GUI window title's version reporting.

Requires a Qt platform plugin to construct a QMainWindow; CI sets
QT_QPA_PLATFORM=offscreen (see .github/workflows/test.yml) so these run
headlessly. A module-scoped QApplication is created once since PyQt6 only
allows a single QApplication instance per process.
"""

from __future__ import annotations

import sys

import pytest
from PyQt6.QtWidgets import QApplication

from set_ttrpg_portrait.gui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_window_title_reports_actual_installed_version(qapp: QApplication) -> None:
    """The title bar should show whatever set_ttrpg_portrait.__version__ actually resolved to.

    Exercises the real, unmocked import chain (importlib.metadata -> the
    installed package's .dist-info, ultimately from .VERSION-PLACEHOLDER at
    build time) so a break in that wiring — not just a wrong VERSION-file
    value — would be caught here.
    """
    from set_ttrpg_portrait import __version__

    window = MainWindow()
    try:
        assert window.windowTitle() == f"Set TTRPG Portrait {__version__}"
    finally:
        window.close()


def test_window_title_reflects_whatever_version_is_resolved(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The title must track `__version__`, not a value baked in at import time."""
    monkeypatch.setattr("set_ttrpg_portrait.gui.main_window.__version__", "9.9.9-test")
    window = MainWindow()
    try:
        assert window.windowTitle() == "Set TTRPG Portrait 9.9.9-test"
    finally:
        window.close()
