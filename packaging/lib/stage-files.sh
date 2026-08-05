#!/usr/bin/env bash
# Shared staging logic for the .deb and .rpm builds (nfpm-based).
#
# Not meant to be run directly — sourced by build-deb.sh/build-rpm.sh, which
# then point nfpm.yaml's `contents` at the resulting directory tree.
#
# Unlike the AppImage, the .deb/.rpm packages are NOT PyInstaller-frozen —
# they rely on the distro's own python3-pyqt6/python3-pikepdf/python3-pil/
# python3-pymupdf packages for their compiled dependencies (declared in
# packaging/nfpm.yaml's `depends`, and automatically pulling in whatever
# lower-level system libraries those need in turn — no manual X11/Wayland/
# GL/D-Bus/etc lib list to maintain). Only this project's own pure-Python
# code is staged here, via `pip install --no-deps --target=...` (so pip
# doesn't also try to fetch PyQt6/pikepdf/Pillow/PyMuPDF from PyPI) into a
# fixed, version-independent path (kept out of the distro's own versioned
# site-packages/dist-packages tree, since Debian/Fedora use different,
# Python-minor-version-specific paths for that — see packaging/README.md)
# that the wrapper scripts under packaging/native/ add to `sys.path` before
# importing.
#
# Produces a staging directory laid out as:
#   usr/bin/set-ttrpg-portrait                                  (CLI launcher)
#   usr/bin/set-ttrpg-portrait-gui                               (GUI launcher)
#   usr/share/set-ttrpg-portrait/lib/                    (this project's code)
#   usr/share/applications/set-ttrpg-portrait-gui.desktop
#   usr/share/icons/hicolor/<size>x<size>/apps/set-ttrpg-portrait.png
#   usr/share/doc/set-ttrpg-portrait/{README.md,LICENSE}
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PACKAGING_DIR="$REPO_ROOT/packaging"
PYTHON="$REPO_ROOT/.venv/bin/python"

stage_files() {
    local stage_dir="$1"

    if [ ! -x "$PYTHON" ]; then
        echo "No virtualenv found at $REPO_ROOT/.venv — run ./setup.sh first." >&2
        exit 1
    fi

    rm -rf "$stage_dir"
    mkdir -p "$stage_dir/usr/bin"
    mkdir -p "$stage_dir/usr/share/set-ttrpg-portrait/lib"
    mkdir -p "$stage_dir/usr/share/applications"
    mkdir -p "$stage_dir/usr/share/doc/set-ttrpg-portrait"

    echo "Installing this project's own code (no third-party deps) into the stage dir..."
    "$PYTHON" -m pip install --no-deps --no-compile \
        --target "$stage_dir/usr/share/set-ttrpg-portrait/lib" \
        "$REPO_ROOT"

    # Source files carry a .py extension so ruff/format.sh pick them up, but
    # the installed command names must not (they're run as `set-ttrpg-portrait`,
    # not `set-ttrpg-portrait.py`).
    cp "$PACKAGING_DIR/native/set-ttrpg-portrait.py" "$stage_dir/usr/bin/set-ttrpg-portrait"
    chmod 755 "$stage_dir/usr/bin/set-ttrpg-portrait"

    cp "$PACKAGING_DIR/native/set-ttrpg-portrait-gui.py" "$stage_dir/usr/bin/set-ttrpg-portrait-gui"
    chmod 755 "$stage_dir/usr/bin/set-ttrpg-portrait-gui"

    cp "$PACKAGING_DIR/set-ttrpg-portrait-gui.desktop" \
        "$stage_dir/usr/share/applications/set-ttrpg-portrait-gui.desktop"

    echo "Generating packaging icons from the master source icon..."
    "$PYTHON" "$PACKAGING_DIR/icon/generate_icons.py"

    for size_dir in "$PACKAGING_DIR"/icons/hicolor/*/apps; do
        size="$(basename "$(dirname "$size_dir")")"
        mkdir -p "$stage_dir/usr/share/icons/hicolor/$size/apps"
        cp "$size_dir/set-ttrpg-portrait.png" \
            "$stage_dir/usr/share/icons/hicolor/$size/apps/set-ttrpg-portrait.png"
    done

    cp "$REPO_ROOT/README.md" "$stage_dir/usr/share/doc/set-ttrpg-portrait/README.md"
    [ -f "$REPO_ROOT/LICENSE" ] && cp "$REPO_ROOT/LICENSE" "$stage_dir/usr/share/doc/set-ttrpg-portrait/LICENSE"
}
