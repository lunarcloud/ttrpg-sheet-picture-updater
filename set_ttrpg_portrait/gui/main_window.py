"""`MainWindow`: business logic wiring for the GUI.

The visual layout itself lives in `main_window.ui` (a Qt Designer form,
loaded at runtime via `PyQt6.uic.loadUi()`) — this module only wires up
signals/slots and orchestrates processing, so the look can be edited
(in Qt Designer or by hand) independently of this logic.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QEvent, QObject, QThread
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMainWindow, QMessageBox

from set_ttrpg_portrait import __version__
from set_ttrpg_portrait.gui import preview
from set_ttrpg_portrait.gui.worker import ApplyWorker

#: Suffix used for the throwaway preview copy of the sheet.
_TEMP_SUFFIX = ".set-ttrpg-portrait-preview.pdf"

#: Qt Designer form filename, loaded at runtime (see module docstring).
_UI_FILENAME = "main_window.ui"

#: Extension used to recognize a dropped fillable sheet.
_SHEET_EXTENSION = ".pdf"

#: Extensions accepted as a dropped/browsed portrait image (matches the
#: `_browse_portrait()` file-picker filter below).
_PORTRAIT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}


def _ui_file_path() -> Path:
    """Locate `main_window.ui` alongside this module/binary.

    Mirrors `gui.icon.bundled_icon_path()`'s frozen-vs-source handling: in
    a PyInstaller-frozen build, `__file__` doesn't point at a real file on
    disk, so the `.ui` form must be bundled as `datas` (preserving the
    `set_ttrpg_portrait/gui` path) and looked up under `sys._MEIPASS`
    instead.
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = base / "set_ttrpg_portrait" / "gui" / _UI_FILENAME
        if candidate.is_file():
            return candidate
    return Path(__file__).resolve().parent / _UI_FILENAME


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        uic.loadUi(str(_ui_file_path()), self)
        self.setWindowTitle(f"Set TTRPG Portrait {__version__}")

        self._sheet_path: str | None = None
        self._portrait_path: str | None = None
        self._temp_output_path: str | None = None
        self._thread: QThread | None = None
        self._worker: ApplyWorker | None = None
        # Set if an input changes while a process is already running, so we
        # know to kick off a fresh one (with the latest inputs) once it
        # finishes instead of silently dropping the change.
        self._reprocess_needed = False
        # Candidate field names offered the last time an ambiguous-field
        # picker was shown, and which one is currently selected — lets
        # "Change Field…" reopen the same choice without recomputing it,
        # so a sheet with e.g. both "Pilot Appearance" and "Mech
        # Appearance" fields can be processed once per field.
        self._field_candidates: list[str] = []
        self._selected_field: str | None = None
        # Full-resolution stacked preview pixmap — kept so it can be
        # rescaled to fit the current viewport width (see
        # `_rescale_preview()`) without re-rendering the PDF on every
        # window resize.
        self._preview_pixmap: QPixmap | None = None

        self.sheet_browse_button.clicked.connect(self._browse_sheet)
        self.portrait_browse_button.clicked.connect(self._browse_portrait)
        self.sheet_clear_button.clicked.connect(self._clear_sheet)
        self.portrait_clear_button.clicked.connect(self._clear_portrait)
        self.save_button.clicked.connect(self._save_as)
        self.change_field_button.clicked.connect(self._change_field)

        # Accept dropped files on the two path fields, and on the preview
        # (sorted by extension: a dropped PDF becomes the sheet, a dropped
        # image becomes the portrait — see `_handle_drop()`).
        self._drop_targets = (
            self.sheet_line_edit,
            self.portrait_line_edit,
            self.preview_scroll_area,
            self.preview_label,
        )
        for widget in self._drop_targets:
            widget.setAcceptDrops(True)
            widget.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        """Handle drag-and-drop of files onto the path fields and preview.

        Installed on `self._drop_targets` in `__init__()` rather than
        overriding `dragEnterEvent()`/`dropEvent()` on each widget's own
        class, since those are plain stock Qt widgets (`QLineEdit`,
        `QScrollArea`, `QLabel`) loaded from the `.ui` form.
        """
        if obj in self._drop_targets:
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                if self._handle_drop(obj, event):
                    event.acceptProposedAction()
                    return True
        return super().eventFilter(obj, event)

    def _handle_drop(self, target: QObject, event: QEvent) -> bool:
        """Route a dropped file to the sheet or portrait input.

        The two path fields only accept their own file type; the preview
        (which stands in for both) sorts by extension so a dropped PDF
        always becomes the sheet and a dropped image always becomes the
        portrait, regardless of which one is currently loaded.
        """
        urls = event.mimeData().urls()
        if not urls or not urls[0].isLocalFile():
            return False
        path = urls[0].toLocalFile()
        suffix = Path(path).suffix.lower()

        if target is self.sheet_line_edit:
            accepts_sheet, accepts_portrait = True, False
        elif target is self.portrait_line_edit:
            accepts_sheet, accepts_portrait = False, True
        else:  # dropped onto the preview — sort by file type
            accepts_sheet, accepts_portrait = True, True

        if accepts_sheet and suffix == _SHEET_EXTENSION:
            self._set_sheet(path)
            return True
        if accepts_portrait and suffix in _PORTRAIT_EXTENSIONS:
            self._set_portrait(path)
            return True
        return False

    def _set_sheet(self, path: str) -> None:
        self._sheet_path = path
        self.sheet_line_edit.setText(path)
        self._reset_field_choice()
        self._maybe_auto_process()

    def _set_portrait(self, path: str) -> None:
        self._portrait_path = path
        self.portrait_line_edit.setText(path)
        self._maybe_auto_process()

    def _browse_sheet(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select fillable PDF sheet", "", "PDF files (*.pdf)"
        )
        if path:
            self._set_sheet(path)

    def _browse_portrait(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select portrait image",
            "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tiff)",
        )
        if path:
            self._set_portrait(path)

    def _clear_sheet(self) -> None:
        self._sheet_path = None
        self.sheet_line_edit.clear()
        self._reset_field_choice()
        self._reset_output()

    def _clear_portrait(self) -> None:
        self._portrait_path = None
        self.portrait_line_edit.clear()
        self._reset_output()

    def _reset_field_choice(self) -> None:
        """Forget any previously-offered ambiguous-field choice.

        Called whenever the sheet changes, since candidate field names
        from a previous sheet don't apply to a new one.
        """
        self._field_candidates = []
        self._selected_field = None
        self.change_field_button.setVisible(False)
        self.change_field_button.setEnabled(False)

    def _reset_output(self) -> None:
        """Discard any previous preview/output — inputs no longer match it."""
        self._cleanup_temp_output()
        self.save_button.setEnabled(False)
        self.change_field_button.setEnabled(False)
        self._preview_pixmap = None
        self.preview_label.setText("No preview yet.")
        self.preview_label.setPixmap(QPixmap())
        self.status_label.setText("Select a sheet and a portrait to begin.")

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
        if field is not None:
            self._selected_field = field

        fd, temp_path = tempfile.mkstemp(suffix=_TEMP_SUFFIX)
        os.close(fd)
        self._temp_output_path = temp_path

        self._set_inputs_enabled(False)
        self.save_button.setEnabled(False)
        self.change_field_button.setEnabled(False)
        self.status_label.setText("Processing…")

        self._thread = QThread(self)
        self._worker = ApplyWorker(
            self._sheet_path, self._portrait_path, temp_path, field
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._worker.ambiguous.connect(self._on_ambiguous)
        self._worker.succeeded.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.ambiguous.connect(self._thread.quit)
        self._thread.start()

    def _set_inputs_enabled(self, enabled: bool) -> None:
        """Disable Browse/Clear while a process is running to avoid races."""
        for widget in (
            self.sheet_browse_button,
            self.sheet_clear_button,
            self.portrait_browse_button,
            self.portrait_clear_button,
        ):
            widget.setEnabled(enabled)

    def _on_success(self, output_path: str) -> None:
        self._set_inputs_enabled(True)
        self._render_preview(output_path)
        self.save_button.setEnabled(True)
        if len(self._field_candidates) > 1:
            self.change_field_button.setVisible(True)
            self.change_field_button.setEnabled(True)
        self.status_label.setText("Done — preview shown below.")
        self._process_pending_reprocess()

    def _process_pending_reprocess(self) -> None:
        if self._reprocess_needed:
            self._reprocess_needed = False
            self._maybe_auto_process()

    def _render_preview(self, pdf_path: str) -> None:
        """Rasterize every page of `pdf_path` and stack them into one image."""
        try:
            page_images = preview.load_page_images(pdf_path)
        except Exception as exc:  # noqa: BLE001 - preview is best-effort
            self._preview_pixmap = None
            self.preview_label.setText(f"Could not render preview: {exc}")
            self.preview_label.setPixmap(QPixmap())
            return

        if not page_images:
            self._preview_pixmap = None
            self.preview_label.setText("Sheet has no pages to preview.")
            self.preview_label.setPixmap(QPixmap())
            return

        self.preview_label.setText("")
        self._preview_pixmap = preview.stack_images(page_images)
        self._rescale_preview()

    def _rescale_preview(self) -> None:
        """Fit the stacked preview pixmap to the scroll area's viewport width.

        Keeps scrolling to just one axis (vertical, through/between pages)
        instead of needing to scroll horizontally too. Called on every
        resize (see `resizeEvent()`) since the viewport width changes.
        """
        if self._preview_pixmap is None or self._preview_pixmap.isNull():
            return
        scroll_area = self.preview_scroll_area
        # Compute from the scroll area's own width rather than
        # `viewport().width()`: the viewport only shrinks *after* a
        # vertical scrollbar appears, which itself only happens once a
        # too-wide pixmap is set — reserving its width upfront (always,
        # since multi-page sheets almost always need one) avoids a
        # second, slightly-delayed rescale pass to correct for it.
        frame = 2 * scroll_area.frameWidth()
        scrollbar_width = scroll_area.verticalScrollBar().sizeHint().width()
        available_width = scroll_area.width() - frame - scrollbar_width
        scaled = preview.scale_to_width(self._preview_pixmap, available_width)
        self.preview_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        super().resizeEvent(event)
        self._rescale_preview()

    def _on_failure(self, message: str) -> None:
        self._set_inputs_enabled(True)
        self.status_label.setText("Failed.")
        QMessageBox.critical(self, "Could not embed portrait", message)
        self._process_pending_reprocess()

    def _on_ambiguous(self, message: str, field_names: list[str]) -> None:
        self._set_inputs_enabled(True)
        self.status_label.setText("Multiple portrait fields found.")
        self._field_candidates = field_names
        self._offer_field_picker(message)
        self._process_pending_reprocess()

    def _offer_field_picker(self, message: str) -> None:
        """Prompt the user to choose which candidate field to embed into."""
        if not self._field_candidates:
            QMessageBox.critical(self, "Could not embed portrait", message)
            return
        current = self._selected_field
        default_index = (
            self._field_candidates.index(current)
            if current in self._field_candidates
            else 0
        )
        field, ok = QInputDialog.getItem(
            self,
            "Multiple portrait fields found",
            f"{message}\n\nChoose which field to use:",
            self._field_candidates,
            default_index,
            False,
        )
        if ok and field:
            self._process(field=field)

    def _change_field(self) -> None:
        """Reopen the field picker to reprocess against a different field.

        Lets the user run the same sheet/portrait against each candidate
        field (e.g. "Pilot Appearance" then "Mech Appearance") without
        needing to clear and reselect either input.
        """
        if not self._field_candidates:
            return
        if self._thread is not None and self._thread.isRunning():
            return
        self._offer_field_picker("Choose which field to set the portrait on.")

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
        self.status_label.setText(f"Saved to {path}")

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
