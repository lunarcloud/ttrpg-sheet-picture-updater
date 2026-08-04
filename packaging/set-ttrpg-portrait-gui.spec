# PyInstaller spec for a reproducible one-file build of the GUI:
# set-ttrpg-portrait-gui.
#
# Usage (from repo root, with the project .venv active):
#   .venv/bin/pyinstaller packaging/set-ttrpg-portrait-gui.spec
#
# Produces dist/set-ttrpg-portrait-gui — a standalone executable bundling
# the interpreter plus PyQt6/pikepdf/Pillow, so downstream .deb/.rpm
# packages don't need Python or pip installed at all. Kept as a separate
# binary/spec from set-ttrpg-portrait.spec (the CLI) so CLI-only installs
# don't pull in the much heavier Qt runtime. See packaging/README.md for
# design rationale.

import pathlib

block_cipher = None

REPO_ROOT = pathlib.Path(SPECPATH).parent

a = Analysis(
    [str(REPO_ROOT / "set_ttrpg_portrait_gui.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="set-ttrpg-portrait-gui",
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
)
