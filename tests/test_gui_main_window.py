"""Tests for the GUI window title's version reporting, and background-job
thread lifecycle (QThread cleanup on close).

Requires a Qt platform plugin to construct a QMainWindow; CI sets
QT_QPA_PLATFORM=offscreen (see .github/workflows/test.yml) so these run
headlessly. A module-scoped QApplication is created once since PyQt6 only
allows a single QApplication instance per process.
"""

from __future__ import annotations

import sys

import pytest
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QAction, QKeySequence
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


def test_close_after_finished_job_does_not_crash(qapp: QApplication) -> None:
    """Closing the window after a job's QThread has already finished must not raise.

    Regression test: `QThread.finished` schedules `deleteLater()` on the
    thread/worker, but previously left `self._thread`/`self._worker`
    pointing at the (eventually deleted) Qt objects. `_shutdown_thread()`
    (called from `closeEvent()`) would then touch an already-destroyed
    C++ QThread and raise "RuntimeError: wrapped C/C++ object ... has
    been deleted" if that deletion had already happened by the time the
    window closed.
    """
    window = MainWindow()
    try:
        thread = QThread(window)
        thread.finished.connect(thread.deleteLater)
        window._thread = thread
        window._worker = object()
        window._clear_thread_refs()

        # Force the scheduled deleteLater() to actually run now, so the
        # underlying C++ QThread is gone before close() is called below —
        # reproducing the original race without needing a real worker job.
        thread.deleteLater()
        qapp.sendPostedEvents(None, 0)
        qapp.processEvents()

        assert window._thread is None
        window.close()  # must not raise
    finally:
        window.close()


def test_menu_actions_follow_button_state(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """Menus cannot browse or save while the corresponding buttons are disabled."""
    window = MainWindow()
    try:
        assert window.menuBar().actions()
        assert window.quit_action.menuRole() == QAction.MenuRole.QuitRole
        assert window.about_action.menuRole() == QAction.MenuRole.AboutRole
        assert window.open_sheet_action.shortcut() == QKeySequence(QKeySequence.StandardKey.Open)
        assert window.open_portrait_action.shortcut() == QKeySequence("Ctrl+Shift+O")
        assert window.save_as_action.shortcut() == QKeySequence(QKeySequence.StandardKey.SaveAs)
        assert window.quit_action.shortcut() == QKeySequence(QKeySequence.StandardKey.Quit)
        assert not window.save_as_action.isEnabled()
        window._set_inputs_enabled(False)
        assert not window.open_sheet_action.isEnabled()
        assert not window.open_portrait_action.isEnabled()
        window._set_inputs_enabled(True)
        assert window.open_sheet_action.isEnabled()
        assert window.open_portrait_action.isEnabled()
        monkeypatch.setattr(window, "_render_preview", lambda path: None)
        window._on_success("synthetic-output.pdf")
        assert window.save_button.isEnabled()
        assert window.save_as_action.isEnabled()
        window._reset_output()
        assert not window.save_as_action.isEnabled()
    finally:
        window.close()


def test_menu_browse_uses_existing_file_picker(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """The File menu routes through the same picker and input logic as Browse."""
    from unittest.mock import Mock

    from PyQt6.QtCore import QStandardPaths
    from PyQt6.QtWidgets import QFileDialog

    picker = Mock(return_value=("synthetic-sheet.pdf", "PDF files (*.pdf)"))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", picker)
    window = MainWindow()
    try:
        window.open_sheet_action.trigger()
        assert window._sheet_path == "synthetic-sheet.pdf"
        documents_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        picker.assert_called_once_with(window, "Select fillable PDF sheet", documents_dir, "PDF files (*.pdf)")
    finally:
        window.close()
