#!/usr/bin/env bash
# Builds every Linux distribution artifact (.deb, .rpm, AppImage) and
# collects them under dist/packages/. See "Distribution / Packaging" in
# plan.md. Each build-*.sh script freezes its own PyInstaller binary, so
# they can also be run individually.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/build-deb.sh"
"$SCRIPT_DIR/build-rpm.sh"
"$SCRIPT_DIR/build-appimage.sh"

echo "All packages built in $SCRIPT_DIR/../dist/packages"
