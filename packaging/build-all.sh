#!/usr/bin/env bash
# Builds every Linux distribution artifact (.deb, .rpm, AppImage) and
# collects them under dist/packages/. See packaging/README.md for full
# design rationale. Each build-*.sh script freezes its own PyInstaller
# binary, so they can also be run individually.
#
# Does NOT include the Windows installer (build-nsis.sh) — that must run
# on a native Windows host (pikepdf's compiled-wheel constraint), so it's a
# separate CI job/script rather than part of this Linux-only aggregate.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/build-deb.sh"
"$SCRIPT_DIR/build-rpm.sh"
"$SCRIPT_DIR/build-appimage.sh"

echo "All packages built in $SCRIPT_DIR/../dist/packages"
