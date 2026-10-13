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
