#!/usr/bin/env bash
# Validates packaging scripts without needing a full platform-specific
# build (PyInstaller .spec files can't be fully "run" outside PyInstaller).
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

source "$SCRIPT_DIR/lib/fetch-tools.sh"
NFPM="$(resolve_nfpm)"
if [ -z "$NFPM" ]; then
    echo
    echo "nfpm not found — skipping MSI config validation." >&2
    echo "(Run ./setup.sh and answer 'y' to the packaging-tools prompt to enable it.)" >&2
    exit 0
fi

NFPM_ACTUAL_VERSION="$("$NFPM" --version 2>&1 | sed -nE 's/.*GitVersion:[[:space:]]*v?([0-9]+\.[0-9]+\.[0-9]+).*/\1/p' | head -n 1)"
if [ -z "$NFPM_ACTUAL_VERSION" ]; then
    echo "Error: could not determine nfpm version from '$NFPM --version'." >&2
    exit 1
fi
if ! nfpm_version_at_least "$NFPM_ACTUAL_VERSION" "$NFPM_VERSION"; then
    echo "Error: nfpm $NFPM_VERSION or newer is required for MSI validation; found $NFPM_ACTUAL_VERSION." >&2
    exit 1
fi

echo
echo "Building a throwaway MSI from the Windows package config..."
FAKE_STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$FAKE_STAGE_DIR"' EXIT
STAGE_CONTENTS="$FAKE_STAGE_DIR/stage"
mkdir "$STAGE_CONTENTS"
printf 'synthetic executable payload\n' > "$STAGE_CONTENTS/set-ttrpg-portrait-launcher.exe"
TEMP_CONFIG="$FAKE_STAGE_DIR/nfpm-windows.yaml"
sed "s|src: dist/set-ttrpg-portrait-launcher/|src: $STAGE_CONTENTS|" \
    "$SCRIPT_DIR/nfpm-windows.yaml" > "$TEMP_CONFIG"
VERSION="0.0.0"
export VERSION
(cd "$REPO_ROOT" && "$NFPM" package \
    --config "$TEMP_CONFIG" \
    --packager msi \
    --target "$FAKE_STAGE_DIR/validate.msi")
test -s "$FAKE_STAGE_DIR/validate.msi"

echo
echo "Packaging validation complete."
