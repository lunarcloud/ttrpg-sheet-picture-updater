#!/usr/bin/env bash
# Builds a .deb package from the PyInstaller-frozen binary using nfpm.
# See "Distribution / Packaging" in plan.md.
#
# Usage: ./packaging/build-deb.sh
# Requires: nfpm (https://nfpm.goreleaser.com/), a standalone binary — run
# ./setup.sh and answer "y" to the packaging-tools prompt to fetch it (or
# have `nfpm` on PATH yourself).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
STAGE_DIR="$REPO_ROOT/build/stage"
OUT_DIR="$REPO_ROOT/dist/packages"
VERSION="$(tr -d ' \t\n\r' < "$REPO_ROOT/VERSION")"

# shellcheck source=lib/fetch-tools.sh
source "$SCRIPT_DIR/lib/fetch-tools.sh"
# shellcheck source=lib/stage-files.sh
source "$SCRIPT_DIR/lib/stage-files.sh"

NFPM="$(resolve_nfpm)"
if [ -z "$NFPM" ]; then
    echo "Error: 'nfpm' not found. Run ./setup.sh and answer 'y' to the" >&2
    echo "packaging-tools prompt (or install nfpm yourself and put it on PATH)." >&2
    exit 1
fi

stage_files "$STAGE_DIR"
mkdir -p "$OUT_DIR"

export STAGE_DIR VERSION
"$NFPM" package \
    --config "$SCRIPT_DIR/nfpm.yaml" \
    --packager deb \
    --target "$OUT_DIR/update-portrait_${VERSION}_amd64.deb"

echo "Built $OUT_DIR/update-portrait_${VERSION}_amd64.deb"
