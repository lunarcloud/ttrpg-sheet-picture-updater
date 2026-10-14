#!/usr/bin/env bash
# Type-checks the library using mypy.
# Usage: ./typecheck.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $VENV_DIR — run ./setup.sh first." >&2
    exit 1
fi

# Scoped to set_ttrpg_portrait/ only (the actual library), not tests/ or
# packaging/: PyInstaller .spec files rely on globals (Analysis, EXE,
# COLLECT, BUNDLE, SPECPATH, ...) injected at exec time by PyInstaller
# itself, which aren't real imports and would just be a wall of false
# "undefined name" errors; tests/ pulls in third-party stub gaps (e.g.
# PyMuPDF's C constants) that aren't worth chasing for test-only code.
TARGET="$SCRIPT_DIR/set_ttrpg_portrait"

if [ ! -e "$TARGET" ]; then
    echo "No set_ttrpg_portrait/ found yet — nothing to type-check."
    exit 0
fi

echo "Running mypy..."
"$PYTHON" -m mypy "$TARGET"

echo "Type-checking complete."
