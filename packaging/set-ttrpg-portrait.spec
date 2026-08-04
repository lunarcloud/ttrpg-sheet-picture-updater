# PyInstaller spec for a reproducible one-file build of set-ttrpg-portrait.
#
# Usage (from repo root, with the project .venv active):
#   .venv/bin/pyinstaller packaging/set-ttrpg-portrait.spec
#
# Produces dist/set-ttrpg-portrait — a standalone executable bundling the
# interpreter plus pikepdf/Pillow native extensions, so downstream .deb/
# .rpm/AppImage packages don't need Python or pip installed at all.
# See packaging/README.md for design rationale.

import pathlib

block_cipher = None

REPO_ROOT = pathlib.Path(SPECPATH).parent

a = Analysis(
    [str(REPO_ROOT / "set_ttrpg_portrait.py")],
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
    name="set-ttrpg-portrait",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
