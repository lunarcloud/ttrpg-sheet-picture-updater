#!/usr/bin/env bash
# Regenerates set-ttrpg-portrait.pyproject, the project file Qt Creator's
# Python plugin uses for its project tree/code completion/run configs.
#
# Qt Creator's .pyproject format is a simple JSON file with a "files" list —
# it does NOT reliably expand glob patterns (confirmed against real-world
# .pyproject files), so the list has to be literal paths. Run this script
# after adding, removing, or renaming any tracked .py/.ui file so Qt
# Creator's project view doesn't go stale.
#
# Usage: ./update-qtcreator-project.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OUT_FILE="set-ttrpg-portrait.pyproject"

# git ls-files (tracked + untracked-but-not-ignored) naturally skips
# .venv/, build/, dist/, packaging/tools/, etc. without needing a
# separate exclude list here.
mapfile -t FILES < <(git ls-files -co --exclude-standard -- '*.py' '*.ui' | sort)

python3 - "$OUT_FILE" "${FILES[@]}" <<'EOF'
import json
import sys

out_file = sys.argv[1]
files = sys.argv[2:]

with open(out_file, "w") as f:
    json.dump({"files": files}, f, indent=4)
    f.write("\n")

print(f"Wrote {out_file} with {len(files)} files.")
EOF
