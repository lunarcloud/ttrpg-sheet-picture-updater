"""Simple PyQt6 GUI for set_ttrpg_portrait.

Pick a sheet PDF and a portrait image, embed the portrait into a temp copy
of the sheet in the background, preview the result inline (via Qt's
built-in `QtPdf`/`QtPdfWidgets`, so no extra PDF-rendering dependency is
needed), then optionally save it somewhere permanent.

Kept intentionally thin: all the real work is `core.apply_portrait()` (the
same function the CLI calls), this module is just Qt plumbing around it.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
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

#: Sentinel prefix used to smuggle an "ambiguous field" error across the
#: worker-thread -> UI-thread signal boundary so the UI can offer a field
#: picker instead of just showing a plain error dialog.
_AMBIGUOUS_MARKER = "__ambiguous__:"


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

        self._sheet_edit = QLineEdit(readOnly=True)
        self._portrait_edit = QLineEdit(readOnly=True)
        sheet_browse = QPushButton("Browse…")
        portrait_browse = QPushButton("Browse…")
        sheet_browse.clicked.connect(self._browse_sheet)
        portrait_browse.clicked.connect(self._browse_portrait)

        self._process_button = QPushButton("Process")
        self._process_button.setEnabled(False)
        self._process_button.clicked.connect(self._process)

        self._save_button = QPushButton("Save As…")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._save_as)

        self._status_label = QLabel("Select a sheet and a portrait to begin.")

        self._pdf_document = QPdfDocument(self)
        self._pdf_view = QPdfView(None)
        self._pdf_view.setDocument(self._pdf_document)
        self._pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(self._file_row("Sheet (PDF):", self._sheet_edit, sheet_browse))
        layout.addLayout(
            self._file_row("Portrait (image):", self._portrait_edit, portrait_browse)
        )

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self._process_button)
        buttons_row.addWidget(self._save_button)
        layout.addLayout(buttons_row)

        layout.addWidget(self._status_label)
        layout.addWidget(self._pdf_view, stretch=1)
        self.setCentralWidget(central)

    @staticmethod
    def _file_row(
        label: str, line_edit: QLineEdit, browse_button: QPushButton
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(line_edit, stretch=1)
        row.addWidget(browse_button)
        return row

    def _browse_sheet(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select fillable PDF sheet", "", "PDF files (*.pdf)"
        )
        if path:
            self._sheet_path = path
            self._sheet_edit.setText(path)
            self._update_process_enabled()

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
            self._update_process_enabled()

    def _update_process_enabled(self) -> None:
        self._process_button.setEnabled(
            bool(self._sheet_path) and bool(self._portrait_path)
        )

    def _process(self, field: str | None = None) -> None:
        assert self._sheet_path and self._portrait_path
        self._cleanup_temp_output()

        fd, temp_path = tempfile.mkstemp(suffix=_TEMP_SUFFIX)
        os.close(fd)
        self._temp_output_path = temp_path

        self._process_button.setEnabled(False)
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

    def _on_success(self, output_path: str) -> None:
        self._process_button.setEnabled(True)
        self._pdf_document.load(output_path)
        self._pdf_view.setDocument(self._pdf_document)
        self._save_button.setEnabled(True)
        self._status_label.setText("Done — preview shown below.")

    def _on_failure(self, message: str) -> None:
        self._process_button.setEnabled(True)
        self._status_label.setText("Failed.")
        if message.startswith(_AMBIGUOUS_MARKER):
            self._offer_field_picker(message[len(_AMBIGUOUS_MARKER) :])
            return
        QMessageBox.critical(self, "Could not embed portrait", message)

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
        self._pdf_document.close()
        self._cleanup_temp_output()
        super().closeEvent(event)


def main(argv: list[str] | None = None) -> int:
    """Entry point used by both `set_ttrpg_portrait_gui.py` and `python -m set_ttrpg_portrait.gui`."""
    app = QApplication(argv if argv is not None else sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
