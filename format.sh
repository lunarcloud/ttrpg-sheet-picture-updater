#!/usr/bin/env bash
# Formats all Python source in this repo using isort + black.
# Usage: ./format.sh [--check]
#   --check   Don't modify files; exit non-zero if formatting is needed
#             (useful for CI).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $VENV_DIR — run ./setup.sh first." >&2
    exit 1
fi

# Directories/files to format. Excludes .venv, dist/build (packaging output),
# and tests/fixtures (generated PDFs, not Python needing formatting anyway).
TARGETS=(update_portrait.py update_portrait tests packaging)
EXISTING_TARGETS=()
for t in "${TARGETS[@]}"; do
    [ -e "$SCRIPT_DIR/$t" ] && EXISTING_TARGETS+=("$SCRIPT_DIR/$t")
done

if [ "${#EXISTING_TARGETS[@]}" -eq 0 ]; then
    echo "No Python targets found yet (${TARGETS[*]}) — nothing to format."
    exit 0
fi

MODE_ARGS=()
if [ "${1:-}" = "--check" ]; then
    MODE_ARGS=(--check --diff)
fi

echo "Running isort..."
"$PYTHON" -m isort "${MODE_ARGS[@]}" "${EXISTING_TARGETS[@]}"

echo "Running black..."
"$PYTHON" -m black "${MODE_ARGS[@]}" "${EXISTING_TARGETS[@]}"

echo "Formatting complete."
