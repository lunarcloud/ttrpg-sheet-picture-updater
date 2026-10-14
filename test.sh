#!/usr/bin/env bash
# Regenerates test fixtures and runs the pytest suite (with coverage).
# Usage: ./test.sh [pytest args...]
#   Any extra args are passed through to pytest, e.g. ./test.sh -k fields
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $VENV_DIR — run ./setup.sh first." >&2
    exit 1
fi

# Regenerated (not just reused as committed) so a stale generator/fixture
# mismatch fails loudly here instead of silently passing against an
# out-of-date fixture — see tests/fixtures/generate_fixtures.py.
echo "Regenerating test fixtures..."
"$PYTHON" "$SCRIPT_DIR/tests/fixtures/generate_fixtures.py"

echo "Running pytest..."
"$PYTHON" -m pytest "$SCRIPT_DIR/tests" -v "$@"

echo "Tests complete."
