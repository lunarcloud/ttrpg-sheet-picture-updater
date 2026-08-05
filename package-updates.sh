#!/usr/bin/env bash
# Checks (and optionally updates) this repo's pinned dependency versions.
#
# Covers things Dependabot (.github/dependabot.yml) does NOT track, since
# they aren't in a manifest file it understands:
#   1. The exact pip package pins in pyproject.toml's [project.dependencies]
#      / [project.optional-dependencies] (Dependabot *does* also cover these
#      automatically on a monthly cadence — this script is for on-demand
#      checks between those cycles, or to force an update right now).
#   2. The manually-pinned `NFPM_VERSION` in packaging/lib/fetch-tools.sh
#      (a plain bash variable, not a manifest Dependabot can read).
#   3. `appimagetool`/`linuxdeploy` are intentionally pinned to GitHub's
#      "continuous" release tag (always the latest upstream build, so
#      there's no version number to bump) — but the *local, cached* copy in
#      packaging/tools/ is only downloaded once, so this checks its mtime
#      against the remote asset's last-updated time to catch local drift.
#
# Usage: ./package-updates.sh [--update]
#   (no args)  Report outdated pins, don't modify anything.
#   --update   Rewrite outdated pins in-place (pyproject.toml,
#              packaging/lib/fetch-tools.sh). Re-run ./setup.sh afterwards
#              to install the updated pip packages.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYPROJECT="$SCRIPT_DIR/pyproject.toml"
FETCH_TOOLS="$SCRIPT_DIR/packaging/lib/fetch-tools.sh"

for tool in curl jq; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "This script requires '$tool', which was not found on PATH." >&2
        exit 1
    fi
done

UPDATE=0
if [ "${1:-}" = "--update" ]; then
    UPDATE=1
fi

ANY_OUTDATED=0

latest_pypi_version() {
    # $1: PyPI package name
    curl -fsSL "https://pypi.org/pypi/$1/json" | jq -r '.info.version'
}

latest_github_release() {
    # $1: owner/repo. Strips a leading "v" from the tag, if present.
    curl -fsSL "https://api.github.com/repos/$1/releases/latest" \
        | jq -r '.tag_name' | sed 's/^v//'
}

echo "Checking pinned pip dependencies ($PYPROJECT)..."
# Matches lines like:  "pikepdf==10.11.0",
while read -r name current; do
    latest="$(latest_pypi_version "$name")" || {
        echo "  $name: could not reach PyPI, skipping"
        continue
    }
    if [ "$current" = "$latest" ]; then
        echo "  $name $current (up to date)"
    else
        echo "  $name $current -> $latest (update available)"
        ANY_OUTDATED=1
        if [ "$UPDATE" -eq 1 ]; then
            sed -i "s/\"$name==$current\"/\"$name==$latest\"/" "$PYPROJECT"
        fi
    fi
done < <(grep -oP '"\K[A-Za-z0-9_.-]+(?===[0-9][^"]*")' "$PYPROJECT" | while read -r n; do
    v=$(grep -oP "\"$n==\K[^\"]+" "$PYPROJECT" | head -1)
    echo "$n $v"
done)

echo
echo "Checking manually-pinned build tool versions..."

NFPM_CURRENT="$(grep -oP 'NFPM_VERSION="\K[^"]+' "$FETCH_TOOLS")"
NFPM_LATEST="$(latest_github_release goreleaser/nfpm)" || NFPM_LATEST=""
if [ -z "$NFPM_LATEST" ]; then
    echo "  nfpm: could not reach GitHub, skipping"
elif [ "$NFPM_CURRENT" = "$NFPM_LATEST" ]; then
    echo "  nfpm $NFPM_CURRENT (up to date)"
else
    echo "  nfpm $NFPM_CURRENT -> $NFPM_LATEST (update available)"
    ANY_OUTDATED=1
    if [ "$UPDATE" -eq 1 ]; then
        sed -i "s/NFPM_VERSION=\"$NFPM_CURRENT\"/NFPM_VERSION=\"$NFPM_LATEST\"/" "$FETCH_TOOLS"
    fi
fi

check_continuous_release_staleness() {
    local label="$1" repo="$2" asset_name="$3" local_path="$4"
    echo "  $label: pinned to GitHub's \"continuous\" release tag (always the"
    echo "  latest upstream build), but the local $local_path copy"
    echo "  is only downloaded once, then cached forever — so a stale local copy"
    echo "  can silently drift behind mainstream 'continuous' as new builds ship."
    local remote_updated
    remote_updated="$(
        curl -fsSL "https://api.github.com/repos/$repo/releases/tags/continuous" \
            | jq -r --arg name "$asset_name" '.assets[] | select(.name == $name) | .updated_at'
    )" || remote_updated=""
    if [ ! -e "$local_path" ]; then
        echo "  $label: not downloaded yet (run ./setup.sh), nothing to compare"
    elif [ -z "$remote_updated" ]; then
        echo "  $label: could not reach GitHub, skipping"
    else
        local local_epoch remote_epoch
        local_epoch="$(stat -c %Y "$local_path")"
        remote_epoch="$(date -d "$remote_updated" +%s)"
        if [ "$remote_epoch" -gt "$local_epoch" ]; then
            echo "  $label: local copy predates the latest continuous build (update available)"
            ANY_OUTDATED=1
            if [ "$UPDATE" -eq 1 ]; then
                rm -f "$local_path"
                echo "  Removed cached $label; run ./setup.sh to re-download the latest build."
            fi
        else
            echo "  $label: local copy is at least as new as the latest continuous build"
        fi
    fi
}

check_continuous_release_staleness \
    "appimagetool" "AppImage/appimagetool" "appimagetool-x86_64.AppImage" \
    "$SCRIPT_DIR/packaging/tools/appimagetool"

check_continuous_release_staleness \
    "linuxdeploy" "linuxdeploy/linuxdeploy" "linuxdeploy-x86_64.AppImage" \
    "$SCRIPT_DIR/packaging/tools/linuxdeploy"

echo
if [ "$UPDATE" -eq 1 ]; then
    echo "Updated pins written. Run ./setup.sh to install the updated pip packages"
    echo "(and delete packaging/tools/nfpm to force re-download of the new nfpm)."
elif [ "$ANY_OUTDATED" -eq 1 ]; then
    echo "Some pins are outdated. Re-run with --update to rewrite them in-place."
else
    echo "Everything is up to date."
fi
