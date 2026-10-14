# PyInstaller spec for a one-dir macOS .app bundle (Apple Silicon/arm64
# only — no Intel) of the combined CLI+GUI launcher
# (set-ttrpg-portrait-launcher), wrapped in a BUNDLE() so it installs/runs
# like any other Mac app. See set_ttrpg_portrait/launcher.py: no args or
# --gui launches the GUI, any other args behave like the CLI — advanced
# users can also invoke Contents/MacOS/set-ttrpg-portrait-launcher
# directly (or symlink it onto PATH) for CLI use.
#
# Must run on a native macOS arm64 host (pikepdf ships platform-specific
# compiled wheels — see packaging/README.md's "Build natively per
# architecture" note).
#
# Usage (from repo root, with the project .venv active):
#   .venv/bin/pyinstaller packaging/set-ttrpg-portrait-macos.spec
#
# Produces dist/set-ttrpg-portrait-launcher/ (one-dir, same as the
# AppImage/Windows installer specs) AND dist/set-ttrpg-portrait.app (the
# BUNDLE() wrapping it) — build-macos.sh packages the latter into the
# final .dmg.

import pathlib

block_cipher = None

REPO_ROOT = pathlib.Path(SPECPATH).parent
ICNS_PATH = REPO_ROOT / "packaging" / "macos" / "AppIcon.icns"
VERSION = (REPO_ROOT / ".VERSION-PLACEHOLDER").read_text().strip()

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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
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

app = BUNDLE(
    coll,
    name="set-ttrpg-portrait.app",
    icon=str(ICNS_PATH) if ICNS_PATH.exists() else None,
    bundle_identifier="com.lunarcloud.set-ttrpg-portrait",
    info_plist={
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "lunarcloud",
        "LSApplicationCategoryType": "public.app-category.utilities",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
    },
)
