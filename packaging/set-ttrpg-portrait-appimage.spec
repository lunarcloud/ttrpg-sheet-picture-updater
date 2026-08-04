# PyInstaller spec for a reproducible one-file build of the AppImage's
# combined CLI+GUI launcher binary (set-ttrpg-portrait-launcher).
#
# Usage (from repo root, with the project .venv active):
#   .venv/bin/pyinstaller packaging/set-ttrpg-portrait-appimage.spec
#
# Produces dist/set-ttrpg-portrait-launcher — bundles PyQt6 + pikepdf +
# Pillow, since the AppImage ships a single executable that defaults to the
# GUI when given no arguments (see set_ttrpg_portrait/launcher.py) but
# behaves like the CLI otherwise. Kept as its own spec/binary name (rather
# than reusing set-ttrpg-portrait.spec's output name) so it never collides
# with the separate, lighter-weight CLI binary built for .deb/.rpm. See
# packaging/README.md for design rationale.

import pathlib

block_cipher = None

REPO_ROOT = pathlib.Path(SPECPATH).parent

a = Analysis(
    [str(REPO_ROOT / "set_ttrpg_portrait_launcher.py")],
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
    name="set-ttrpg-portrait-launcher",
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
