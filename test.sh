#!/usr/bin/env bash
# Runs the pytest suite against the committed fixtures (with coverage).
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

echo "Running pytest..."
"$PYTHON" -m pytest "$SCRIPT_DIR/tests" -v "$@"

echo "Tests complete."
