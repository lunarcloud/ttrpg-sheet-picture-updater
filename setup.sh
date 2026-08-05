#!/usr/bin/env bash
# Sets up a local Python virtual environment and installs dependencies.
# Usage: ./setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing project (editable) with dev dependencies from pyproject.toml ..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e "${SCRIPT_DIR}[dev]"

echo
echo "Setup complete. Activate the environment with:"
echo "  source .venv/bin/activate"

# Packaging tools (nfpm, appimagetool, linuxdeploy) are only needed if
# you're building .deb/.rpm/AppImage releases (packaging/build-*.sh), not
# for everyday development. They're standalone binaries downloaded to
# packaging/tools/ (gitignored) — never installed system-wide, never
# committed to the repo.
echo
if [ -t 0 ]; then
    read -r -p "Set up packaging tools too (nfpm, appimagetool, linuxdeploy — for building .deb/.rpm/AppImage releases)? [y/N] " REPLY
else
    REPLY="n"  # non-interactive (e.g. CI): skip by default
fi
if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    # shellcheck source=packaging/lib/fetch-tools.sh
    source "$SCRIPT_DIR/packaging/lib/fetch-tools.sh"
    fetch_nfpm
    fetch_appimagetool
    fetch_linuxdeploy
else
    echo "Skipping packaging tools. Run ./setup.sh again anytime to add them."
fi

