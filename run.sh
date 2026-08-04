#!/usr/bin/env bash
# Runs the project's venv Python against the combined CLI+GUI launcher.
# Usage:
#   ./run.sh                  # no args -> launches the GUI
#   ./run.sh --gui            # explicitly launches the GUI
#   ./run.sh <cli args...>    # behaves like the `set-ttrpg-portrait` CLI
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "No virtual environment found at $VENV_DIR — running ./setup.sh first ..."
    "$SCRIPT_DIR/setup.sh"
fi

exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/set_ttrpg_portrait_launcher.py" "$@"
