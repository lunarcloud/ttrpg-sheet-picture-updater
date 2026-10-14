# PyInstaller spec for a reproducible one-dir build of the Windows NSIS
# installer's combined CLI+GUI launcher binary (set-ttrpg-portrait-launcher.exe).
#
# Must run on a native Windows host (pikepdf ships platform-specific
# compiled wheels — see packaging/README.md's "Build natively per
# architecture" note).
#
# Usage (from repo root, with the project .venv active):
#   .venv/Scripts/pyinstaller packaging/set-ttrpg-portrait-windows.spec
#
# Produces dist/set-ttrpg-portrait-launcher/ (a directory, NOT a single
# file) — mirrors set-ttrpg-portrait-appimage.spec's one-dir Linux build
# (same combined CLI+GUI entry point, see set_ttrpg_portrait/launcher.py),
# just with a Windows .exe and .ico instead of a Linux binary.
#
# `console=False` (windowed subsystem) so double-clicking the .exe (GUI
# mode) doesn't flash a console window open first, unlike Linux/macOS
# where no such OS-level subsystem concept exists for the AppImage/.dmg
# builds. CLI usage (args other than none/`--gui`) still needs its
# output visible, so set_ttrpg_portrait/launcher.py's `main()` attaches to
# the invoking terminal's existing console in that case instead — see its
# `_attach_windows_console()` docstring.

import pathlib

block_cipher = None

REPO_ROOT = pathlib.Path(SPECPATH).parent

a = Analysis(
    [str(REPO_ROOT / "set_ttrpg_portrait_launcher.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    # Bundles the single committed source icon so gui/icon.py's app_icon()
    # has a fallback window icon when no installed icon theme entry is
    # found, plus the Qt Designer `.ui` form gui/main_window.py loads at
    # runtime.
    datas=[
        (str(REPO_ROOT / "packaging" / "icon" / "icon-source.png"), "."),
        (
            str(REPO_ROOT / "set_ttrpg_portrait" / "gui" / "main_window.ui"),
            "set_ttrpg_portrait/gui",
        ),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="set-ttrpg-portrait-launcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(REPO_ROOT / "packaging" / "windows" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="set-ttrpg-portrait-launcher",
)
