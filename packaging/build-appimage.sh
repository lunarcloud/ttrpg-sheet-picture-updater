#!/usr/bin/env bash
# Builds a standalone AppImage from the PyInstaller-frozen binary.
# See "Distribution / Packaging" in plan.md.
#
# Usage: ./packaging/build-appimage.sh
# Requires: appimagetool, a standalone binary — run ./setup.sh and answer
# "y" to the packaging-tools prompt to fetch it (or have `appimagetool` on
# PATH yourself).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
APPDIR="$REPO_ROOT/build/update-portrait.AppDir"
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
(cd "$REPO_ROOT" && "$PYTHON" -m PyInstaller "$SCRIPT_DIR/update-portrait.spec" --noconfirm)

echo "Generating packaging icons from the master source icon..."
"$PYTHON" "$SCRIPT_DIR/icon/generate_icons.py"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp "$REPO_ROOT/dist/update-portrait" "$APPDIR/usr/bin/update-portrait"
chmod 755 "$APPDIR/usr/bin/update-portrait"

cp "$SCRIPT_DIR/appimage/update-portrait.desktop" "$APPDIR/update-portrait.desktop"
cp "$SCRIPT_DIR/appimage/icon.png" "$APPDIR/update-portrait.png"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "$HERE/usr/bin/update-portrait" "$@"
EOF
chmod 755 "$APPDIR/AppRun"

mkdir -p "$OUT_DIR"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUT_DIR/update-portrait-${VERSION}-x86_64.AppImage"

echo "Built $OUT_DIR/update-portrait-${VERSION}-x86_64.AppImage"
