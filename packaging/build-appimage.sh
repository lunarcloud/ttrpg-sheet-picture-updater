#!/usr/bin/env bash
# Builds a standalone AppImage bundling a single combined CLI+GUI binary
# (see set_ttrpg_portrait/launcher.py: no args or --gui launches the GUI,
# any other args behave like the CLI).
# See packaging/README.md for design rationale.
#
# Usage: ./packaging/build-appimage.sh
# Requires: appimagetool and linuxdeploy, both standalone binaries — run
# ./setup.sh and answer "y" to the packaging-tools prompt to fetch them (or
# have them on PATH yourself).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
APPDIR="$REPO_ROOT/build/set-ttrpg-portrait.AppDir"
OUT_DIR="$REPO_ROOT/dist/packages"
PYTHON="$REPO_ROOT/.venv/bin/python"
VERSION="$(tr -d ' \t\n\r' < "$REPO_ROOT/VERSION")"
LAUNCHER_NAME="set-ttrpg-portrait-launcher"

# shellcheck source=lib/fetch-tools.sh
source "$SCRIPT_DIR/lib/fetch-tools.sh"

APPIMAGETOOL="$(resolve_appimagetool)"
if [ -z "$APPIMAGETOOL" ]; then
    echo "Error: 'appimagetool' not found. Run ./setup.sh and answer 'y' to the" >&2
    echo "packaging-tools prompt (or install appimagetool yourself and put it on PATH)." >&2
    exit 1
fi

LINUXDEPLOY="$(resolve_linuxdeploy)"
if [ -z "$LINUXDEPLOY" ]; then
    echo "Error: 'linuxdeploy' not found. Run ./setup.sh and answer 'y' to the" >&2
    echo "packaging-tools prompt (or install linuxdeploy yourself and put it on PATH)." >&2
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $REPO_ROOT/.venv — run ./setup.sh first." >&2
    exit 1
fi

echo "Building the combined CLI+GUI launcher binary with PyInstaller..."
# One-dir (not one-file) build — see set-ttrpg-portrait-appimage.spec for
# why: linuxdeploy needs PyQt6's bundled Qt6 libraries/plugins to exist as
# real on-disk files so it can inspect and bundle their own dependencies.
(cd "$REPO_ROOT" && "$PYTHON" -m PyInstaller "$SCRIPT_DIR/set-ttrpg-portrait-appimage.spec" --noconfirm)

echo "Generating packaging icons from the master source icon..."
"$PYTHON" "$SCRIPT_DIR/icon/generate_icons.py"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib"
cp -r "$REPO_ROOT/dist/$LAUNCHER_NAME" "$APPDIR/usr/bin/$LAUNCHER_NAME"

cp "$SCRIPT_DIR/appimage/set-ttrpg-portrait.desktop" "$APPDIR/set-ttrpg-portrait.desktop"
cp "$SCRIPT_DIR/appimage/icon.png" "$APPDIR/set-ttrpg-portrait.png"

# PyInstaller's one-dir output only bundles PyQt6's own Qt6 shared
# libraries/plugins — it does NOT bundle the lower-level system libraries
# those in turn dynamically link against at runtime (X11/XCB extensions,
# D-Bus, fontconfig, freetype, glib, xkbcommon; verified with `ldd`
# against .venv's PyQt6/Qt6/plugins/platforms/libqxcb.so — see
# packaging/nfpm.yaml's overrides.deb/rpm.depends for the equivalent
# .deb/.rpm dependency list). An AppImage must bundle these itself since
# it can't rely on distro package managers — so run linuxdeploy over every
# Qt6 shared library/plugin PyInstaller bundled, letting it recursively
# discover and copy in whatever's still missing, patching RPATHs as it
# goes. linuxdeploy deliberately excludes libGL/libEGL/libGLX/Mesa (must
# match the host's own GPU driver) and libxcb.so.1/libX11.so.6/fontconfig/
# freetype (assumed universally present) from what it bundles — see
# https://github.com/probonopd/AppImages/blob/master/excludelist.
QT6_DIR="$APPDIR/usr/bin/$LAUNCHER_NAME/_internal/PyQt6/Qt6"
mapfile -t QT_LIBRARY_ARGS < <(
    # Excludes plugins/imageformats: this app never uses Qt's own image
    # decoders (portraits are always loaded via Pillow in image_prep.py;
    # the PDF preview builds QImages directly from PyMuPDF's raw pixel
    # buffers, never by decoding a file through a Qt plugin), and at least
    # one of them (libqtiff.so) depends on the long-removed libtiff.so.5
    # ABI that modern distros no longer ship (see the CI logs' "Library
    # not found: libtiff.so.5" warning during the .deb/.rpm PyInstaller
    # build) — bundling a plugin we never call would just add a dependency
    # linuxdeploy can't even satisfy, for no functional benefit.
    find "$QT6_DIR/lib" "$QT6_DIR/plugins" -path "$QT6_DIR/plugins/imageformats" -prune -o \
        -type f \( -name "*.so" -o -name "*.so.*" \) -printf "--library\n%p\n"
)

LD_LIBRARY_PATH="$QT6_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
    "$LINUXDEPLOY" --appdir "$APPDIR" "${QT_LIBRARY_ARGS[@]}"

cat > "$APPDIR/AppRun" <<EOF
#!/usr/bin/env bash
HERE="\$(dirname "\$(readlink -f "\${0}")")"
export LD_LIBRARY_PATH="\$HERE/usr/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
exec "\$HERE/usr/bin/$LAUNCHER_NAME/$LAUNCHER_NAME" "\$@"
EOF
chmod 755 "$APPDIR/AppRun"

mkdir -p "$OUT_DIR"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUT_DIR/set-ttrpg-portrait-${VERSION}-x86_64.AppImage"

echo "Built $OUT_DIR/set-ttrpg-portrait-${VERSION}-x86_64.AppImage"

