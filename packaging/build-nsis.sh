#!/usr/bin/env bash
# Builds a Windows installer .exe (NSIS), bundling a PyInstaller-frozen
# one-dir build of the combined CLI+GUI launcher (see
# set-ttrpg-portrait-windows.spec and set_ttrpg_portrait/launcher.py).
#
# Replaces the earlier .msix approach — see packaging/README.md's Windows
# section for the rationale: MSIX requires signing, and without a paid
# code-signing certificate end users had to manually import/trust an
# ephemeral self-signed one before Windows would even install the
# package. An unsigned NSIS .exe only triggers a dismissable SmartScreen
# "unknown publisher" prompt (click "More info" > "Run anyway") — no
# certificate import required, same tradeoff as the ad-hoc-signed macOS
# .dmg's Gatekeeper prompt.
#
# Usage (from repo root, in Git Bash on Windows, with the project .venv
# set up — see packaging/README.md):
#   ./packaging/build-nsis.sh
#
# Requires: makensis (NSIS). Already preinstalled on GitHub's
# windows-latest runners; for local builds, see fetch_makensis in
# packaging/lib/fetch-tools.sh, or install NSIS yourself from
# https://nsis.sourceforge.io/.
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
        echo "Error: build-nsis.sh must run on a native Windows host (Git Bash)." >&2
        echo "pikepdf ships platform-specific compiled wheels, so the frozen .exe" >&2
        echo "can't be cross-built from Linux/macOS — see packaging/README.md." >&2
        exit 1
        ;;
esac

MAKENSIS="$(resolve_makensis)"
if [ -z "$MAKENSIS" ]; then
    echo "Error: 'makensis' not found. Run ./setup.sh and answer 'y' to the" >&2
    echo "packaging-tools prompt (or install NSIS yourself from" >&2
    echo "https://nsis.sourceforge.io/ and put makensis on PATH)." >&2
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

mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/set-ttrpg-portrait-${VERSION}-x64-setup.exe"

"$MAKENSIS" \
    "-DVERSION=$VERSION" \
    "-DSTAGE_DIR=$(cygpath -w "$REPO_ROOT/dist/$LAUNCHER_NAME")" \
    "-DICON_FILE=$(cygpath -w "$SCRIPT_DIR/windows/icon.ico")" \
    "-DOUT_FILE=$(cygpath -w "$OUT_FILE")" \
    "$SCRIPT_DIR/windows/installer.nsi"

echo "Built $OUT_FILE"
