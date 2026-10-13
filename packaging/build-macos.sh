#!/usr/bin/env bash
# Builds a macOS .dmg (Apple Silicon/arm64 only -- no Intel) containing a
# PyInstaller-frozen one-dir .app bundle of the combined CLI+GUI launcher.
# See set-ttrpg-portrait-macos.spec and packaging/README.md's macOS
# section for design rationale.
#
# Usage (from repo root, on a native macOS arm64 host, with the project
# .venv set up -- see packaging/README.md):
#   ./packaging/build-macos.sh
#
# Env vars:
#   MACOS_SIGN_IDENTITY  codesign identity to use (default: "-", i.e.
#                        ad-hoc signing -- no paid Apple Developer
#                        certificate is available, see
#                        packaging/README.md's macOS section for the
#                        resulting Gatekeeper-warning trade-off).
#
# Requires: Xcode Command Line Tools (codesign, hdiutil, iconutil -- all
# preinstalled on every macOS GitHub Actions runner).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
STAGE_DIR="$REPO_ROOT/build/macos-stage"
OUT_DIR="$REPO_ROOT/dist/packages"
VERSION="$(tr -d ' \t\n\r' < "$REPO_ROOT/.VERSION-PLACEHOLDER")"
APP_NAME="set-ttrpg-portrait.app"
PYTHON="$REPO_ROOT/.venv/bin/python"
MACOS_SIGN_IDENTITY="${MACOS_SIGN_IDENTITY:--}"

# shellcheck source=lib/make-icns.sh
source "$SCRIPT_DIR/lib/make-icns.sh"

if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
    echo "Error: build-macos.sh must run on a native macOS arm64 (Apple" >&2
    echo "Silicon) host -- pikepdf ships platform-specific compiled" >&2
    echo "wheels, so the frozen .app can't be cross-built. This project" >&2
    echo "only targets Apple Silicon, not Intel Macs." >&2
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $REPO_ROOT/.venv -- run ./setup.sh first." >&2
    exit 1
fi

echo "Generating packaging icons (including the macOS iconset) from the master source icon..."
"$PYTHON" "$SCRIPT_DIR/icon/generate_icons.py"

echo "Converting the iconset to .icns..."
make_icns "$SCRIPT_DIR/macos/AppIcon.iconset" "$SCRIPT_DIR/macos/AppIcon.icns"

echo "Building the combined CLI+GUI launcher .app with PyInstaller..."
(cd "$REPO_ROOT" && "$PYTHON" -m PyInstaller "$SCRIPT_DIR/set-ttrpg-portrait-macos.spec" --noconfirm)

echo "Ad-hoc signing the .app (identity: $MACOS_SIGN_IDENTITY)..."
# No paid Apple Developer certificate is available -- ad-hoc signing lets
# the .app run at all on Apple Silicon (unsigned arm64 binaries are
# refused outright), but Gatekeeper still flags it as quarantined/from an
# unidentified developer on first launch after download. See
# packaging/README.md's macOS section for the documented user workaround.
codesign --force --deep --sign "$MACOS_SIGN_IDENTITY" "$REPO_ROOT/dist/$APP_NAME"

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"
cp -R "$REPO_ROOT/dist/$APP_NAME" "$STAGE_DIR/$APP_NAME"
ln -s /Applications "$STAGE_DIR/Applications"

mkdir -p "$OUT_DIR"
DMG_PATH="$OUT_DIR/set-ttrpg-portrait-${VERSION}-arm64.dmg"
rm -f "$DMG_PATH"
hdiutil create -volname "set-ttrpg-portrait" -srcfolder "$STAGE_DIR" -ov -format UDZO "$DMG_PATH"

echo "Built $DMG_PATH"
