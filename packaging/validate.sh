#!/usr/bin/env bash
# Validates packaging scripts without needing a full platform-specific
# build (PyInstaller .spec files can't be fully "run" outside PyInstaller,
# and build-nsis.sh itself requires a native Windows/Git-Bash host) —
# catches syntax errors (e.g. the "invalid VIProductVersion format" class
# of bug) on every PR instead of only at release time.
# Usage: ./packaging/validate.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$REPO_ROOT/.venv"
PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $VENV_DIR — run ./setup.sh first." >&2
    exit 1
fi

echo "Checking PyInstaller .spec files compile (syntax only — Analysis/EXE/"
echo "COLLECT/BUNDLE/SPECPATH are PyInstaller-injected globals, not real"
echo "imports, so this can't fully type-check them, only catch syntax errors)..."
for spec in "$SCRIPT_DIR"/*.spec; do
    [ -e "$spec" ] || continue
    echo "  $spec"
    "$PYTHON" -m py_compile "$spec"
done

MAKENSIS="$(command -v makensis || true)"
if [ -z "$MAKENSIS" ]; then
    echo
    echo "makensis not found on PATH — skipping installer.nsi compile check." >&2
    echo "(Run ./setup.sh and answer 'y' to the packaging-tools prompt, or see" >&2
    echo "https://nsis.sourceforge.io/, to get coverage for this locally — CI" >&2
    echo "always has it installed.)" >&2
    exit 0
fi

echo
echo "Compiling installer.nsi against a throwaway stage dir (dummy values,"
echo "discarded output — only proves the NSIS script itself is valid)..."

FAKE_STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$FAKE_STAGE_DIR"' EXIT
echo "placeholder" > "$FAKE_STAGE_DIR/set-ttrpg-portrait-launcher.exe"

echo "Generating packaging icons (needed for installer.nsi's Icon directive)..."
"$PYTHON" "$SCRIPT_DIR/icon/generate_icons.py"

"$MAKENSIS" \
    "-DVERSION=0.0.0-validate" \
    "-DVERSION_NUMERIC=0.0.0.0" \
    "-DSTAGE_DIR=$FAKE_STAGE_DIR" \
    "-DICON_FILE=$SCRIPT_DIR/windows/icon.ico" \
    "-DOUT_FILE=$FAKE_STAGE_DIR/validate-output.exe" \
    "$SCRIPT_DIR/windows/installer.nsi"

echo
echo "Packaging validation complete."
