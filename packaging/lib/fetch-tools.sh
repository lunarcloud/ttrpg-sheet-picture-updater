#!/usr/bin/env bash
# Downloads the standalone build-time binaries used by packaging/build-*.sh
# (nfpm for .deb/.rpm, appimagetool for the AppImage, NSIS for the Windows
# installer) into packaging/tools/ (gitignored) — never checked into the
# repo, and never installed globally/system-wide. None of these are a
# dependency of the shipped app itself.
#
# Sourced by ./setup.sh (as an optional interactive step) and by the
# packaging/build-*.sh scripts (which just check for these tools and tell
# you to (re-)run ./setup.sh if they're missing, rather than downloading
# them themselves mid-build).
set -euo pipefail

NFPM_VERSION="2.47.0"
NFPM_URL="https://github.com/goreleaser/nfpm/releases/download/v${NFPM_VERSION}/nfpm_${NFPM_VERSION}_Linux_x86_64.tar.gz"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
# linuxdeploy bundles the AppImage's shared-library dependencies (see
# build-appimage.sh) — also pinned to its "continuous" release, like
# appimagetool, since neither publishes versioned releases.
LINUXDEPLOY_URL="https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
# NSIS's "portable" zip (as opposed to its installer .exe) just needs
# extracting — no install step, same as the other tools here. Used by
# build-nsis.sh. release.yml's build-windows-installer CI job installs
# NSIS via Chocolatey instead (see packaging/README.md's Windows
# section), so this is only needed for local Windows dev builds without
# choco.
NSIS_VERSION="3.11"
NSIS_URL="https://sourceforge.net/projects/nsis/files/NSIS%203/${NSIS_VERSION}/nsis-${NSIS_VERSION}.zip/download"

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
    if [ -x "$PACKAGING_TOOLS_DIR/nfpm" ]; then
        echo "nfpm already present at $PACKAGING_TOOLS_DIR/nfpm"
        return 0
    fi
    echo "Downloading nfpm v$NFPM_VERSION to $PACKAGING_TOOLS_DIR/nfpm ..."
    mkdir -p "$PACKAGING_TOOLS_DIR"
    curl -fsSL -o "$PACKAGING_TOOLS_DIR/nfpm.tar.gz" "$NFPM_URL"
    tar -xzf "$PACKAGING_TOOLS_DIR/nfpm.tar.gz" -C "$PACKAGING_TOOLS_DIR" nfpm
    rm -f "$PACKAGING_TOOLS_DIR/nfpm.tar.gz"
    chmod +x "$PACKAGING_TOOLS_DIR/nfpm"
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

fetch_makensis() {
    if ! _is_windows; then
        echo "Skipping NSIS fetch — makensis is only needed for Windows builds." >&2
        return 0
    fi
    if [ -x "$PACKAGING_TOOLS_DIR/nsis/makensis.exe" ]; then
        echo "makensis already present at $PACKAGING_TOOLS_DIR/nsis/makensis.exe"
        return 0
    fi
    echo "Downloading NSIS v$NSIS_VERSION to $PACKAGING_TOOLS_DIR/nsis ..."
    mkdir -p "$PACKAGING_TOOLS_DIR"
    curl -fsSL -o "$PACKAGING_TOOLS_DIR/nsis.zip" "$NSIS_URL"
    # Use PowerShell's Expand-Archive rather than `unzip` — guaranteed
    # present on windows-latest runners, unlike `unzip` in Git Bash.
    powershell.exe -NoProfile -Command \
        "Expand-Archive -Path '$(cygpath -w "$PACKAGING_TOOLS_DIR/nsis.zip")' -DestinationPath '$(cygpath -w "$PACKAGING_TOOLS_DIR")' -Force"
    rm -f "$PACKAGING_TOOLS_DIR/nsis.zip"
    mv "$PACKAGING_TOOLS_DIR/nsis-${NSIS_VERSION}" "$PACKAGING_TOOLS_DIR/nsis"
}

# `nfpm`/`appimagetool`/`linuxdeploy`/`makensis` resolve to a repo-local
# packaging/tools/ copy if one exists, else to a PATH-installed copy (or,
# for makensis, the default NSIS install location), else empty (caller
# should error).
resolve_nfpm() {
    if [ -x "$PACKAGING_TOOLS_DIR/nfpm" ]; then
        echo "$PACKAGING_TOOLS_DIR/nfpm"
    else
        command -v nfpm || true
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

resolve_makensis() {
    if [ -x "$PACKAGING_TOOLS_DIR/nsis/makensis.exe" ]; then
        echo "$PACKAGING_TOOLS_DIR/nsis/makensis.exe"
        return 0
    fi
    if command -v makensis.exe >/dev/null 2>&1; then
        command -v makensis.exe
        return 0
    fi
    if command -v makensis >/dev/null 2>&1; then
        command -v makensis
        return 0
    fi
    # Chocolatey's `nsis` package (installed by release.yml's
    # build-windows-installer job) installs to this default location,
    # which isn't necessarily already on PATH.
    local default_path="/c/Program Files (x86)/NSIS/makensis.exe"
    if [ -x "$default_path" ]; then
        echo "$default_path"
        return 0
    fi
    true
}
