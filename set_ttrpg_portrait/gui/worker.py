"""Background worker that runs `apply_portrait()` off the GUI thread."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from set_ttrpg_portrait.core import apply_portrait
from set_ttrpg_portrait.errors import AmbiguousFieldError, SetTtrpgPortraitError


class ApplyWorker(QObject):
    """Runs `apply_portrait()` off the UI thread so the window stays responsive."""

    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)
    #: Emitted instead of `failed` when multiple candidate portrait fields
    #: match (message, candidate field names) so the UI can offer a picker.
    ambiguous = pyqtSignal(str, list)

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
            self.ambiguous.emit(str(exc), list(exc.field_names))
            return
        except (SetTtrpgPortraitError, FileNotFoundError) as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(self._output_path)
