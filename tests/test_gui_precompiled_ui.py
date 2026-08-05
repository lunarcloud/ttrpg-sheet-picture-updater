"""Regression test for the .deb/.rpm packages' precompiled-UI code path.

packaging/lib/stage-files.sh precompiles main_window.ui into a plain
main_window_ui.py (via pyuic6) so the installed package never needs
PyQt6.uic at runtime — Debian/Ubuntu split that submodule out of
python3-pyqt6 into the separate pyqt6-dev-tools package, which is exactly
what caused `set-ttrpg-portrait-gui` to crash with
"ImportError: cannot import name 'uic' from 'PyQt6'" before this was added
(python3-pyqt6 alone was declared as the .deb's dependency, but
main_window.py unconditionally called PyQt6.uic.loadUi()).

This drives pyuic6 directly (no real .deb install needed) and exercises
MainWindow in a throwaway *subprocess* (rather than reimporting
set_ttrpg_portrait.gui.main_window in-process, which would corrupt the
module object other test files already hold a `MainWindow` reference to)
with PyQt6.uic import blocked, proving the precompiled path is used and
never touches PyQt6.uic.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_WINDOW_UI = REPO_ROOT / "set_ttrpg_portrait" / "gui" / "main_window.ui"

_SUBPROCESS_SCRIPT = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, {lib_dir!r})

    # Simulate PyQt6.uic being unavailable, as on a Debian/Ubuntu system
    # with only python3-pyqt6 installed (no pyqt6-dev-tools) — see
    # packaging/nfpm.yaml's .deb `depends`.
    import builtins

    _real_import = builtins.__import__

    def _blocking_import(name, *args, **kwargs):
        if name == "PyQt6.uic" or name.startswith("PyQt6.uic."):
            raise ImportError(f"simulated: {{name}} not installed (no pyqt6-dev-tools)")
        return _real_import(name, *args, **kwargs)

    builtins.__import__ = _blocking_import

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    from set_ttrpg_portrait.gui.main_window import MainWindow, _HAS_PRECOMPILED_UI

    assert _HAS_PRECOMPILED_UI, "expected the precompiled main_window_ui.py to be picked up"

    window = MainWindow()
    # Widget attributes must land directly on `self` (not `self.ui.*`),
    # matching what uic.loadUi() would have done, so the rest of
    # main_window.py's widget references keep working unchanged.
    assert window.sheet_browse_button is not None
    window.close()
    print("OK")
    """
)


@pytest.fixture
def staged_lib_dir(tmp_path: Path) -> Path:
    """Stage this project's own code plus a freshly-pyuic6-compiled main_window_ui.py.

    Mirrors packaging/lib/stage-files.sh's real staging layout closely
    enough for set_ttrpg_portrait.gui.main_window's import-time detection
    to pick up the precompiled module, without needing an actual .deb/.rpm
    build or install.
    """
    pyuic6 = Path(sys.executable).parent / "pyuic6"
    if not pyuic6.is_file():
        pytest.skip("pyuic6 not found next to the test interpreter (pip install PyQt6 provides it)")

    lib_dir = tmp_path / "lib"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-compile",
            "--target",
            str(lib_dir),
            str(REPO_ROOT),
        ],
        check=True,
        capture_output=True,
    )
    generated = lib_dir / "set_ttrpg_portrait" / "gui" / "main_window_ui.py"
    subprocess.run([str(pyuic6), "-o", str(generated), str(MAIN_WINDOW_UI)], check=True, capture_output=True)
    return lib_dir


def test_gui_launches_via_precompiled_ui_without_pyqt6_uic(
    staged_lib_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    script = _SUBPROCESS_SCRIPT.format(lib_dir=str(staged_lib_dir))
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "OK" in result.stdout
