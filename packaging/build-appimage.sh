#!/usr/bin/env bash
# Builds a standalone AppImage from the PyInstaller-frozen binary.
# See packaging/README.md for design rationale.
#
# Usage: ./packaging/build-appimage.sh
# Requires: appimagetool, a standalone binary — run ./setup.sh and answer
# "y" to the packaging-tools prompt to fetch it (or have `appimagetool` on
# PATH yourself).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
APPDIR="$REPO_ROOT/build/set-ttrpg-portrait.AppDir"
OUT_DIR="$REPO_ROOT/dist/packages"
PYTHON="$REPO_ROOT/.venv/bin/python"
VERSION="$(tr -d ' \t\n\r' < "$REPO_ROOT/VERSION")"

# shellcheck source=lib/fetch-tools.sh
source "$SCRIPT_DIR/lib/fetch-tools.sh"

APPIMAGETOOL="$(resolve_appimagetool)"
if [ -z "$APPIMAGETOOL" ]; then
    echo "Error: 'appimagetool' not found. Run ./setup.sh and answer 'y' to the" >&2
    echo "packaging-tools prompt (or install appimagetool yourself and put it on PATH)." >&2
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $REPO_ROOT/.venv — run ./setup.sh first." >&2
    exit 1
fi

echo "Building the frozen binary with PyInstaller..."
(cd "$REPO_ROOT" && "$PYTHON" -m PyInstaller "$SCRIPT_DIR/set-ttrpg-portrait.spec" --noconfirm)

echo "Generating packaging icons from the master source icon..."
"$PYTHON" "$SCRIPT_DIR/icon/generate_icons.py"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp "$REPO_ROOT/dist/set-ttrpg-portrait" "$APPDIR/usr/bin/set-ttrpg-portrait"
chmod 755 "$APPDIR/usr/bin/set-ttrpg-portrait"

cp "$SCRIPT_DIR/appimage/set-ttrpg-portrait.desktop" "$APPDIR/set-ttrpg-portrait.desktop"
cp "$SCRIPT_DIR/appimage/icon.png" "$APPDIR/set-ttrpg-portrait.png"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "$HERE/usr/bin/set-ttrpg-portrait" "$@"
EOF
chmod 755 "$APPDIR/AppRun"

mkdir -p "$OUT_DIR"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUT_DIR/set-ttrpg-portrait-${VERSION}-x86_64.AppImage"

echo "Built $OUT_DIR/set-ttrpg-portrait-${VERSION}-x86_64.AppImage"
