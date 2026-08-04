"""PyQt6 GUI for set_ttrpg_portrait.

Pick a sheet PDF and a portrait image, embed the portrait into a temp copy
of the sheet in the background, preview the result inline, then optionally
save it somewhere permanent.

Split into small modules so the look and the logic can change
independently:
- `main_window.ui` — the visual layout (a Qt Designer form), editable in
  Qt Designer or by hand, loaded at runtime via `PyQt6.uic.loadUi()`.
- `main_window.py` — `MainWindow`, wiring the loaded UI's widgets up to
  behavior (business logic only, no manual widget construction).
- `worker.py` — `ApplyWorker`, runs `core.apply_portrait()` off the UI
  thread.
- `preview.py` — rasterizes the resulting PDF's pages for the inline
  preview (via PyMuPDF; see that module's docstring for why not QtPdf).
- `icon.py` — best-effort window icon lookup (theme vs. bundled fallback).
- `app.py` — `main()`, the process entry point (QApplication + MainWindow).

Kept intentionally thin overall: all the real portrait-embedding work is
`core.apply_portrait()` (the same function the CLI calls) — this package
is just Qt plumbing around it.
"""

from __future__ import annotations

from set_ttrpg_portrait.gui.app import main
from set_ttrpg_portrait.gui.main_window import MainWindow

__all__ = ["main", "MainWindow"]
