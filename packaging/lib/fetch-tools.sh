#!/usr/bin/env bash
# Downloads the standalone build-time binaries used by packaging/build-*.sh
# (nfpm for .deb/.rpm/MSI, appimagetool for the AppImage) into
# packaging/tools/ (gitignored) — never checked into the
# repo, and never installed globally/system-wide. None of these are a
# dependency of the shipped app itself.
#
# Sourced by ./setup.sh (as an optional interactive step) and by the
# packaging/build-*.sh scripts (which just check for these tools and tell
# you to (re-)run ./setup.sh if they're missing, rather than downloading
# them themselves mid-build).
set -euo pipefail

NFPM_VERSION="2.49.0"
NFPM_URL="https://github.com/goreleaser/nfpm/releases/download/v${NFPM_VERSION}/nfpm_${NFPM_VERSION}_Linux_x86_64.tar.gz"
NFPM_WINDOWS_URL="https://github.com/goreleaser/nfpm/releases/download/v${NFPM_VERSION}/nfpm_${NFPM_VERSION}_Windows_x86_64.zip"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
# linuxdeploy bundles the AppImage's shared-library dependencies (see
# build-appimage.sh) — also pinned to its "continuous" release, like
# appimagetool, since neither publishes versioned releases.
LINUXDEPLOY_URL="https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
_fetch_tools_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGING_TOOLS_DIR="$(dirname "$_fetch_tools_script_dir")/tools"

# Git Bash on Windows reports a MINGW*/MSYS*/CYGWIN* `uname -s`, never
# "Linux"/"Darwin".
_is_windows() {
    case "$(uname -s)" in
        MINGW* | MSYS* | CYGWIN*) return 0 ;;
        *) return 1 ;;
    esac
}

fetch_nfpm() {
    local nfpm_binary="nfpm"
    local nfpm_url="$NFPM_URL"
    if _is_windows; then
        nfpm_binary="nfpm.exe"
        nfpm_url="$NFPM_WINDOWS_URL"
    fi
    if [ -x "$PACKAGING_TOOLS_DIR/$nfpm_binary" ]; then
        echo "nfpm already present at $PACKAGING_TOOLS_DIR/$nfpm_binary"
        return 0
    fi
    echo "Downloading nfpm v$NFPM_VERSION to $PACKAGING_TOOLS_DIR/$nfpm_binary ..."
    mkdir -p "$PACKAGING_TOOLS_DIR"
    if _is_windows; then
        curl -fsSL -o "$PACKAGING_TOOLS_DIR/nfpm.zip" "$nfpm_url"
        powershell.exe -NoProfile -Command \
            "Expand-Archive -Path '$(cygpath -w "$PACKAGING_TOOLS_DIR/nfpm.zip")' -DestinationPath '$(cygpath -w "$PACKAGING_TOOLS_DIR")' -Force"
        rm -f "$PACKAGING_TOOLS_DIR/nfpm.zip"
    else
        curl -fsSL -o "$PACKAGING_TOOLS_DIR/nfpm.tar.gz" "$nfpm_url"
        tar -xzf "$PACKAGING_TOOLS_DIR/nfpm.tar.gz" -C "$PACKAGING_TOOLS_DIR" nfpm
        rm -f "$PACKAGING_TOOLS_DIR/nfpm.tar.gz"
        chmod +x "$PACKAGING_TOOLS_DIR/nfpm"
    fi
}

fetch_appimagetool() {
    if [ -x "$PACKAGING_TOOLS_DIR/appimagetool" ]; then
        echo "appimagetool already present at $PACKAGING_TOOLS_DIR/appimagetool"
        return 0
    fi
    echo "Downloading appimagetool to $PACKAGING_TOOLS_DIR/appimagetool ..."
    mkdir -p "$PACKAGING_TOOLS_DIR"
    curl -fsSL -o "$PACKAGING_TOOLS_DIR/appimagetool" "$APPIMAGETOOL_URL"
    chmod +x "$PACKAGING_TOOLS_DIR/appimagetool"
}

fetch_linuxdeploy() {
    if [ -x "$PACKAGING_TOOLS_DIR/linuxdeploy" ]; then
        echo "linuxdeploy already present at $PACKAGING_TOOLS_DIR/linuxdeploy"
        return 0
    fi
    echo "Downloading linuxdeploy to $PACKAGING_TOOLS_DIR/linuxdeploy ..."
    mkdir -p "$PACKAGING_TOOLS_DIR"
    curl -fsSL -o "$PACKAGING_TOOLS_DIR/linuxdeploy" "$LINUXDEPLOY_URL"
    chmod +x "$PACKAGING_TOOLS_DIR/linuxdeploy"
}

# `nfpm`/`appimagetool`/`linuxdeploy` resolve to a repo-local
# packaging/tools/ copy if one exists, else to a PATH-installed copy, else
# empty (caller should error).
resolve_nfpm() {
    local nfpm_binary="nfpm"
    if _is_windows; then
        nfpm_binary="nfpm.exe"
    fi
    if [ -x "$PACKAGING_TOOLS_DIR/$nfpm_binary" ]; then
        echo "$PACKAGING_TOOLS_DIR/$nfpm_binary"
    elif [ -f "$PACKAGING_TOOLS_DIR/$nfpm_binary" ] && _is_windows; then
        echo "$PACKAGING_TOOLS_DIR/$nfpm_binary"
    elif command -v "$nfpm_binary" >/dev/null 2>&1; then
        command -v "$nfpm_binary"
    elif command -v nfpm >/dev/null 2>&1; then
        command -v nfpm
    else
        true
    fi
}

resolve_appimagetool() {
    if [ -x "$PACKAGING_TOOLS_DIR/appimagetool" ]; then
        echo "$PACKAGING_TOOLS_DIR/appimagetool"
    else
        command -v appimagetool || true
    fi
}

resolve_linuxdeploy() {
    if [ -x "$PACKAGING_TOOLS_DIR/linuxdeploy" ]; then
        echo "$PACKAGING_TOOLS_DIR/linuxdeploy"
    else
        command -v linuxdeploy || true
    fi
}
