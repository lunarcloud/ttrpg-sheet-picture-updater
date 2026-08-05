"""Regression test: gui/preview.py must not require the legacy `fitz` import name.

Debian/Ubuntu split PyMuPDF's legacy `fitz` alias out of `python3-pymupdf`
into a *separate* `python3-fitz` package (a "forward compatibility name"),
which is not declared as a .deb dependency (see packaging/nfpm.yaml). That's
what caused `set-ttrpg-portrait-gui` to crash with
"ModuleNotFoundError: No module named 'fitz'" before this was fixed —
gui/preview.py used to do a bare `import fitz`.

`pymupdf` is PyMuPDF's own recommended, future-proof import name and is
guaranteed present everywhere PyMuPDF itself is installed (pip, Fedora's
python3-PyMuPDF, and Debian/Ubuntu's python3-pymupdf), so gui/preview.py
now does `import pymupdf as fitz` instead.

This runs in a throwaway *subprocess* (rather than in-process sys.modules
tricks, which can corrupt module objects other test files already hold
references to — see tests/test_gui_precompiled_ui.py) with the `fitz`
module import blocked, proving gui/preview.py never needs it.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

_SUBPROCESS_SCRIPT = textwrap.dedent(
    """
    import builtins

    _real_import = builtins.__import__

    def _blocking_import(name, *args, **kwargs):
        # Simulate a Debian/Ubuntu system with only python3-pymupdf
        # installed (no python3-fitz) — see packaging/nfpm.yaml.
        if name == "fitz" or name.startswith("fitz."):
            raise ModuleNotFoundError(f"simulated: no module named '{name}' (no python3-fitz)")
        return _real_import(name, *args, **kwargs)

    builtins.__import__ = _blocking_import

    import set_ttrpg_portrait.gui.preview as preview

    assert preview.fitz.__name__ == "pymupdf", f"expected pymupdf, got {preview.fitz.__name__}"
    print("OK")
    """
)


def test_preview_module_imports_without_fitz_available() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_SCRIPT],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "OK" in result.stdout
