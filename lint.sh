#!/usr/bin/env bash
# Lints all Python source in this repo using ruff.
# Usage: ./lint.sh [--fix]
#   --fix   Automatically apply safe fixes instead of only reporting them.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $VENV_DIR — run ./setup.sh first." >&2
    exit 1
fi

# Directories/files to lint. Excludes .venv, dist/build (packaging output),
# and tests/fixtures (generated PDFs, not Python needing linting anyway).
TARGETS=(
    set_ttrpg_portrait.py
    set_ttrpg_portrait_gui.py
    set_ttrpg_portrait_launcher.py
    set_ttrpg_portrait
    tests
    packaging
)
EXISTING_TARGETS=()
for t in "${TARGETS[@]}"; do
    [ -e "$SCRIPT_DIR/$t" ] && EXISTING_TARGETS+=("$SCRIPT_DIR/$t")
done

if [ "${#EXISTING_TARGETS[@]}" -eq 0 ]; then
    echo "No Python targets found yet (${TARGETS[*]}) — nothing to lint."
    exit 0
fi

MODE_ARGS=()
if [ "${1:-}" = "--fix" ]; then
    MODE_ARGS=(--fix)
fi

echo "Running ruff check..."
"$PYTHON" -m ruff check "${MODE_ARGS[@]}" "${EXISTING_TARGETS[@]}"

echo "Linting complete."
