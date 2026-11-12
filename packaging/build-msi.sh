#!/usr/bin/env bash
# Builds a Windows installer .msi with nfpm, bundling a PyInstaller-frozen
# one-dir build of the combined CLI+GUI launcher (see
# set-ttrpg-portrait-windows.spec and set_ttrpg_portrait/launcher.py).
#
# Must run on a native Windows host (pikepdf ships platform-specific
# compiled wheels — see packaging/README.md).
#
# Usage (from repo root, in Git Bash on Windows, with the project .venv
# set up — see packaging/README.md):
#   ./packaging/build-msi.sh
#
# Requires nfpm 2.49.0 or newer (fetchable via ./setup.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$REPO_ROOT/dist/packages"
VERSION="$(tr -d ' \t\n\r' < "$REPO_ROOT/.VERSION-PLACEHOLDER")"
LAUNCHER_NAME="set-ttrpg-portrait-launcher"
PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"

# shellcheck source=lib/fetch-tools.sh
source "$SCRIPT_DIR/lib/fetch-tools.sh"

case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*) ;;
    *)
        echo "Error: build-msi.sh must run on a native Windows host (Git Bash)." >&2
        echo "pikepdf ships platform-specific compiled wheels, so the frozen .exe" >&2
        echo "can't be cross-built from Linux/macOS — see packaging/README.md." >&2
        exit 1
        ;;
esac

NFPM="$(resolve_nfpm)"
if [ -z "$NFPM" ]; then
    echo "Error: 'nfpm' not found. Run ./setup.sh and answer 'y' to the" >&2
    echo "packaging-tools prompt (or install nfpm yourself and put it on PATH)." >&2
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $REPO_ROOT/.venv — run ./setup.sh first." >&2
    exit 1
fi

echo "Generating packaging icons (including the Windows .ico) from the master source icon..."
"$PYTHON" "$SCRIPT_DIR/icon/generate_icons.py"

echo "Building the combined CLI+GUI launcher .exe with PyInstaller..."
(cd "$REPO_ROOT" && "$PYTHON" -m PyInstaller "$SCRIPT_DIR/set-ttrpg-portrait-windows.spec" --noconfirm)

# Qt6Core.dll hard-imports icuuc.dll/icuin.dll/icudt*.dll (ICU, for
# Unicode/locale support) — PyInstaller's own dependency scan usually
# finds and bundles these automatically from the build machine's
# C:\Windows\System32 (where they ship as a base OS component on Windows
# 10 1703+/11), but we copy them in explicitly too so the installer stays
# self-contained even if that auto-detection ever misses them, or the
# *target* machine is missing/has an older copy (e.g. Windows Sandbox,
# Server Core, older LTSC builds) — see packaging/README.md.
QT_BIN_DIR="$(find "$REPO_ROOT/dist/$LAUNCHER_NAME" -type d -path '*/PyQt6/Qt6/bin' -print -quit)"
if [ -n "$QT_BIN_DIR" ]; then
    for pattern in icuuc icuin icudt; do
        for f in /c/Windows/System32/"$pattern"*.dll; do
            if [ -f "$f" ]; then
                cp -n "$f" "$QT_BIN_DIR/"
            fi
        done
    done
else
    echo "Warning: couldn't find PyQt6/Qt6/bin in the PyInstaller output — skipping ICU DLL bundling." >&2
fi

mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/set-ttrpg-portrait-${VERSION}-x64.msi"

# nfpm resolves contents[].src relative to its working directory.
export VERSION
(cd "$REPO_ROOT" && "$NFPM" package \
    --config "$SCRIPT_DIR/nfpm-windows.yaml" \
    --packager msi \
    --target "$OUT_FILE")

echo "Built $OUT_FILE"
