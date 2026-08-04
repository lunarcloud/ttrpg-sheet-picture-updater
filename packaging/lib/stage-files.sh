#!/usr/bin/env bash
# Shared staging logic for the .deb and .rpm builds (nfpm-based).
#
# Not meant to be run directly — sourced by build-deb.sh/build-rpm.sh, which
# then point nfpm's ${STAGE_DIR}-templated `contents` at the resulting
# directory tree.
#
# Produces a staging directory laid out as:
#   usr/bin/set-ttrpg-portrait                                  (CLI binary)
#   usr/bin/set-ttrpg-portrait-gui                               (GUI binary)
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

    echo "Building the CLI binary with PyInstaller..."
    (cd "$REPO_ROOT" && "$PYTHON" -m PyInstaller "$PACKAGING_DIR/set-ttrpg-portrait.spec" --noconfirm)

    echo "Building the GUI binary with PyInstaller..."
    (cd "$REPO_ROOT" && "$PYTHON" -m PyInstaller "$PACKAGING_DIR/set-ttrpg-portrait-gui.spec" --noconfirm)

    echo "Generating packaging icons from the master source icon..."
    "$PYTHON" "$PACKAGING_DIR/icon/generate_icons.py"

    rm -rf "$stage_dir"
    mkdir -p "$stage_dir/usr/bin"
    mkdir -p "$stage_dir/usr/share/applications"
    mkdir -p "$stage_dir/usr/share/doc/set-ttrpg-portrait"

    cp "$REPO_ROOT/dist/set-ttrpg-portrait" "$stage_dir/usr/bin/set-ttrpg-portrait"
    chmod 755 "$stage_dir/usr/bin/set-ttrpg-portrait"

    cp "$REPO_ROOT/dist/set-ttrpg-portrait-gui" "$stage_dir/usr/bin/set-ttrpg-portrait-gui"
    chmod 755 "$stage_dir/usr/bin/set-ttrpg-portrait-gui"

    cp "$PACKAGING_DIR/set-ttrpg-portrait-gui.desktop" \
        "$stage_dir/usr/share/applications/set-ttrpg-portrait-gui.desktop"

    for size_dir in "$PACKAGING_DIR"/icons/hicolor/*/apps; do
        size="$(basename "$(dirname "$size_dir")")"
        mkdir -p "$stage_dir/usr/share/icons/hicolor/$size/apps"
        cp "$size_dir/set-ttrpg-portrait.png" \
            "$stage_dir/usr/share/icons/hicolor/$size/apps/set-ttrpg-portrait.png"
    done

    cp "$REPO_ROOT/README.md" "$stage_dir/usr/share/doc/set-ttrpg-portrait/README.md"
    [ -f "$REPO_ROOT/LICENSE" ] && cp "$REPO_ROOT/LICENSE" "$stage_dir/usr/share/doc/set-ttrpg-portrait/LICENSE"
}

