"""Simple PyQt6 GUI for set_ttrpg_portrait.

Pick a sheet PDF and a portrait image, embed the portrait into a temp copy
of the sheet in the background, preview the result inline, then optionally
save it somewhere permanent.

The preview is rendered to a plain image with PyMuPDF (`fitz`) rather than
Qt's own `QtPdf`/`QPdfView` module: QtPdf does not render AcroForm field
appearances at all (neither filled-in values nor our embedded portrait
icon), so it can't show the result of what this tool just did.

Kept intentionally thin: all the real work is `core.apply_portrait()` (the
same function the CLI calls), this module is just Qt plumbing around it.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import fitz
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from set_ttrpg_portrait import __version__
from set_ttrpg_portrait.core import apply_portrait
from set_ttrpg_portrait.errors import AmbiguousFieldError, SetTtrpgPortraitError
from set_ttrpg_portrait.fields import find_button_fields
from set_ttrpg_portrait.pdf_ops import open_sheet

#: Suffix used for the throwaway preview copy of the sheet.
_TEMP_SUFFIX = ".set-ttrpg-portrait-preview.pdf"

#: DPI used to rasterize preview pages — high enough to read comfortably,
#: low enough to render/scroll quickly for typical multi-page sheets.
_PREVIEW_DPI = 150

#: Vertical gap (pixels) drawn between stacked page images in the preview.
_PREVIEW_PAGE_GAP = 8

#: Sentinel prefix used to smuggle an "ambiguous field" error across the
#: worker-thread -> UI-thread signal boundary so the UI can offer a field
#: picker instead of just showing a plain error dialog.
_AMBIGUOUS_MARKER = "__ambiguous__:"

#: freedesktop icon theme name installed by the .deb/.rpm (see
#: packaging/nfpm.yaml + packaging/set-ttrpg-portrait-gui.desktop's
#: `Icon=` key) — used first so installed packages pick up the user's
#: icon theme (light/dark variants, HiDPI sizes, etc).
_ICON_THEME_NAME = "set-ttrpg-portrait"

#: Bundled fallback icon filename, used when no matching theme icon is
#: installed (e.g. running from source, or the AppImage/PyInstaller-frozen
#: binary, neither of which registers a system-wide icon theme entry).
#: Matches the single committed `packaging/icon/icon-source.png` name so
#: the `.spec` files can bundle it unrenamed (PyInstaller's `datas` copies
#: files under their original name).
_BUNDLED_ICON_FILENAME = "icon-source.png"


def _bundled_icon_path() -> Path | None:
    """Locate the fallback icon file bundled alongside this module/binary.

    Handles three cases: a PyInstaller-frozen build (file placed next to
    the executable via the `.spec` files' `datas`), and running directly
    from the repo source tree (falls back to the single committed
    `packaging/icon/icon-source.png`).
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = base / _BUNDLED_ICON_FILENAME
        if candidate.is_file():
            return candidate
    repo_icon = (
        Path(__file__).resolve().parent.parent
        / "packaging"
        / "icon"
        / ("icon-source.png")
    )
    if repo_icon.is_file():
        return repo_icon
    return None


def _app_icon() -> QIcon:
    """Best-effort window icon so windows aren't shown with a generic X11/Wayland icon.

    Without a `.desktop` entry (or its `Icon=` key) telling the window
    manager which icon to use, unset `QIcon`s fall back to a generic
    placeholder. Prefers the installed icon theme entry (works for
    .deb/.rpm installs); falls back to a bundled/source-tree file
    otherwise (AppImage, PyInstaller-frozen binary, or running from
    source).
    """
    icon = QIcon.fromTheme(_ICON_THEME_NAME)
    if not icon.isNull():
        return icon
    path = _bundled_icon_path()
    if path is not None:
        return QIcon(str(path))
    return QIcon()


class _ApplyWorker(QObject):
    """Runs `apply_portrait()` off the UI thread so the window stays responsive."""

    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self, sheet_path: str, portrait_path: str, output_path: str, field: str | None
    ) -> None:
        super().__init__()
        self._sheet_path = sheet_path
        self._portrait_path = portrait_path
        self._output_path = output_path
        self._field = field

    def run(self) -> None:
        try:
            apply_portrait(
                self._sheet_path,
                self._portrait_path,
                self._output_path,
                field=self._field,
            )
        except AmbiguousFieldError as exc:
            self.failed.emit(f"{_AMBIGUOUS_MARKER}{exc}")
            return
        except (SetTtrpgPortraitError, FileNotFoundError) as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(self._output_path)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Set TTRPG Portrait {__version__}")
        self.resize(700, 800)

        self._sheet_path: str | None = None
        self._portrait_path: str | None = None
        self._temp_output_path: str | None = None
        self._thread: QThread | None = None
        self._worker: _ApplyWorker | None = None
        # Set if an input changes while a process is already running, so we
        # know to kick off a fresh one (with the latest inputs) once it
        # finishes instead of silently dropping the change.
        self._reprocess_needed = False

        self._sheet_edit = QLineEdit(readOnly=True)
        self._portrait_edit = QLineEdit(readOnly=True)
        self._sheet_browse = QPushButton("Browse…")
        self._portrait_browse = QPushButton("Browse…")
        self._sheet_clear = QPushButton("⌫")
        self._portrait_clear = QPushButton("⌫")
        self._sheet_browse.clicked.connect(self._browse_sheet)
        self._portrait_browse.clicked.connect(self._browse_portrait)
        self._sheet_clear.clicked.connect(self._clear_sheet)
        self._portrait_clear.clicked.connect(self._clear_portrait)

        self._save_button = QPushButton("Save As…")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._save_as)

        self._status_label = QLabel("Select a sheet and a portrait to begin.")

        self._preview_label = QLabel("No preview yet.")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._preview_scroll = QScrollArea()
        self._preview_scroll.setWidget(self._preview_label)
        self._preview_scroll.setWidgetResizable(True)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(
            self._file_row(
                "Sheet (PDF):", self._sheet_edit, self._sheet_browse, self._sheet_clear
            )
        )
        layout.addLayout(
            self._file_row(
                "Portrait (image):",
                self._portrait_edit,
                self._portrait_browse,
                self._portrait_clear,
            )
        )

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self._save_button)
        layout.addLayout(buttons_row)

        layout.addWidget(self._status_label)
        layout.addWidget(self._preview_scroll, stretch=1)
        self.setCentralWidget(central)

    @staticmethod
    def _file_row(
        label: str,
        line_edit: QLineEdit,
        browse_button: QPushButton,
        clear_button: QPushButton,
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(line_edit, stretch=1)
        row.addWidget(browse_button)
        row.addWidget(clear_button)
        return row

    def _browse_sheet(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select fillable PDF sheet", "", "PDF files (*.pdf)"
        )
        if path:
            self._sheet_path = path
            self._sheet_edit.setText(path)
            self._maybe_auto_process()

    def _browse_portrait(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select portrait image",
            "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tiff)",
        )
        if path:
            self._portrait_path = path
            self._portrait_edit.setText(path)
            self._maybe_auto_process()

    def _clear_sheet(self) -> None:
        self._sheet_path = None
        self._sheet_edit.clear()
        self._reset_output()

    def _clear_portrait(self) -> None:
        self._portrait_path = None
        self._portrait_edit.clear()
        self._reset_output()

    def _reset_output(self) -> None:
        """Discard any previous preview/output — inputs no longer match it."""
        self._cleanup_temp_output()
        self._save_button.setEnabled(False)
        self._preview_label.setText("No preview yet.")
        self._preview_label.setPixmap(QPixmap())
        self._status_label.setText("Select a sheet and a portrait to begin.")

    def _maybe_auto_process(self, field: str | None = None) -> None:
        """Process automatically once both inputs are set (no Process button)."""
        if not (self._sheet_path and self._portrait_path):
            return
        if self._thread is not None and self._thread.isRunning():
            self._reprocess_needed = True
            return
        self._process(field=field)

    def _process(self, field: str | None = None) -> None:
        assert self._sheet_path and self._portrait_path
        self._cleanup_temp_output()

        fd, temp_path = tempfile.mkstemp(suffix=_TEMP_SUFFIX)
        os.close(fd)
        self._temp_output_path = temp_path

        self._set_inputs_enabled(False)
        self._save_button.setEnabled(False)
        self._status_label.setText("Processing…")

        self._thread = QThread(self)
        self._worker = _ApplyWorker(
            self._sheet_path, self._portrait_path, temp_path, field
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._worker.succeeded.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.start()

    def _set_inputs_enabled(self, enabled: bool) -> None:
        """Disable Browse/Clear while a process is running to avoid races."""
        for widget in (
            self._sheet_browse,
            self._sheet_clear,
            self._portrait_browse,
            self._portrait_clear,
        ):
            widget.setEnabled(enabled)

    def _on_success(self, output_path: str) -> None:
        self._set_inputs_enabled(True)
        self._render_preview(output_path)
        self._save_button.setEnabled(True)
        self._status_label.setText("Done — preview shown below.")
        self._process_pending_reprocess()

    def _process_pending_reprocess(self) -> None:
        if self._reprocess_needed:
            self._reprocess_needed = False
            self._maybe_auto_process()

    def _render_preview(self, pdf_path: str) -> None:
        """Rasterize every page of `pdf_path` and stack them into one image.

        Uses PyMuPDF rather than Qt's own QtPdf module, which doesn't
        render AcroForm field appearances (see module docstring).
        """
        try:
            with fitz.open(pdf_path) as doc:
                page_images = [self._page_to_qimage(page) for page in doc]
        except Exception as exc:  # noqa: BLE001 - preview is best-effort
            self._preview_label.setText(f"Could not render preview: {exc}")
            self._preview_label.setPixmap(QPixmap())
            return

        if not page_images:
            self._preview_label.setText("Sheet has no pages to preview.")
            self._preview_label.setPixmap(QPixmap())
            return

        width = max(image.width() for image in page_images)
        height = sum(image.height() for image in page_images) + _PREVIEW_PAGE_GAP * (
            len(page_images) - 1
        )
        stacked = QImage(width, height, QImage.Format.Format_RGB32)
        stacked.fill(Qt.GlobalColor.gray)

        painter = QPainter(stacked)
        y = 0
        for image in page_images:
            x = (width - image.width()) // 2
            painter.drawImage(x, y, image)
            y += image.height() + _PREVIEW_PAGE_GAP
        painter.end()

        self._preview_label.setText("")
        self._preview_label.setPixmap(QPixmap.fromImage(stacked))

    @staticmethod
    def _page_to_qimage(page: fitz.Page) -> QImage:
        zoom = _PREVIEW_DPI / 72
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        image_format = (
            QImage.Format.Format_RGBA8888
            if pixmap.alpha
            else QImage.Format.Format_RGB888
        )
        image = QImage(
            pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, image_format
        )
        return image.copy()

    def _on_failure(self, message: str) -> None:
        self._set_inputs_enabled(True)
        self._status_label.setText("Failed.")
        if message.startswith(_AMBIGUOUS_MARKER):
            self._offer_field_picker(message[len(_AMBIGUOUS_MARKER) :])
            return
        QMessageBox.critical(self, "Could not embed portrait", message)
        self._process_pending_reprocess()

    def _offer_field_picker(self, ambiguous_message: str) -> None:
        assert self._sheet_path is not None
        try:
            pdf = open_sheet(self._sheet_path)
            candidates = find_button_fields(pdf, None)
        except SetTtrpgPortraitError:
            candidates = []
        names = [c.name for c in candidates]
        if not names:
            QMessageBox.critical(self, "Could not embed portrait", ambiguous_message)
            return
        field, ok = QInputDialog.getItem(
            self,
            "Multiple portrait fields found",
            f"{ambiguous_message}\n\nChoose which field to use:",
            names,
            0,
            False,
        )
        if ok and field:
            self._process(field=field)

    def _save_as(self) -> None:
        if not self._temp_output_path:
            return
        default_name = "character.pdf"
        if self._sheet_path:
            base = os.path.splitext(os.path.basename(self._sheet_path))[0]
            default_name = f"{base}-with-portrait.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save sheet as", default_name, "PDF files (*.pdf)"
        )
        if not path:
            return
        try:
            shutil.copyfile(self._temp_output_path, path)
        except OSError as exc:
            QMessageBox.critical(self, "Could not save file", str(exc))
            return
        self._status_label.setText(f"Saved to {path}")

    def _cleanup_temp_output(self) -> None:
        if self._temp_output_path and os.path.exists(self._temp_output_path):
            try:
                os.remove(self._temp_output_path)
            except OSError:
                pass
        self._temp_output_path = None

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        self._cleanup_temp_output()
        super().closeEvent(event)


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
    icon = _app_icon()
    app.setWindowIcon(icon)
    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
