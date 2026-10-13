#!/usr/bin/env bash
# Builds a Windows .msix package, bundling a PyInstaller-frozen one-dir
# build of the combined CLI+GUI launcher (see set-ttrpg-portrait-msix.spec
# and set_ttrpg_portrait/launcher.py). See packaging/README.md's MSIX
# section for design rationale, including why this must run on a native
# Windows host (pikepdf ships platform-specific compiled wheels) even
# though nfpm's own MSIX packaging step is pure Go.
#
# Usage (from repo root, in Git Bash on Windows, with the project .venv
# set up — see packaging/README.md):
#   ./packaging/build-msix.sh
#
# Env vars:
#   MSIX_PUBLISHER      Signing identity (default: "CN=lunarcloud"). MUST
#                       exactly match the signing certificate's Subject.
#   MSIX_PFX_FILE       Path to a real code-signing .pfx. If unset, an
#                       ephemeral self-signed one is generated instead
#                       (end users must manually trust it — see below).
#   MSIX_PFX_PASSPHRASE Passphrase for MSIX_PFX_FILE (or for the generated
#                       self-signed cert, if MSIX_PFX_FILE is unset).
#
# Requires: nfpm (fetched the same way as build-deb.sh/build-rpm.sh — see
# ./setup.sh or packaging/lib/fetch-tools.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
STAGE_DIR="$REPO_ROOT/build/msix-stage"
OUT_DIR="$REPO_ROOT/dist/packages"
VERSION="$(tr -d ' \t\n\r' < "$REPO_ROOT/.VERSION-PLACEHOLDER")"
LAUNCHER_NAME="set-ttrpg-portrait-launcher"
PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"

# shellcheck source=lib/fetch-tools.sh
source "$SCRIPT_DIR/lib/fetch-tools.sh"
# shellcheck source=lib/generate-msix-cert.sh
source "$SCRIPT_DIR/lib/generate-msix-cert.sh"

case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*) ;;
    *)
        echo "Error: build-msix.sh must run on a native Windows host (Git Bash)." >&2
        echo "pikepdf ships platform-specific compiled wheels, so the frozen .exe" >&2
        echo "can't be cross-built from Linux/macOS — see packaging/README.md." >&2
        exit 1
        ;;
esac

NFPM="$(resolve_nfpm)"
if [ -z "$NFPM" ]; then
    echo "Error: 'nfpm' not found. Run ./setup.sh and answer 'y' to the" >&2
    echo "packaging-tools prompt (or install nfpm yourself and put it on PATH)." >&2
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "No virtualenv found at $REPO_ROOT/.venv — run ./setup.sh first." >&2
    exit 1
fi

echo "Building the combined CLI+GUI launcher .exe with PyInstaller..."
(cd "$REPO_ROOT" && "$PYTHON" -m PyInstaller "$SCRIPT_DIR/set-ttrpg-portrait-msix.spec" --noconfirm)

echo "Generating packaging icons (including MSIX logos/.ico) from the master source icon..."
"$PYTHON" "$SCRIPT_DIR/icon/generate_icons.py"

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR/app"
cp -r "$REPO_ROOT/dist/$LAUNCHER_NAME/." "$STAGE_DIR/app/"

MSIX_PUBLISHER="${MSIX_PUBLISHER:-CN=lunarcloud}"
export MSIX_PUBLISHER

MSIX_PFX_PASSPHRASE="${MSIX_PFX_PASSPHRASE:-}"
if [ -z "${MSIX_PFX_FILE:-}" ]; then
    echo
    echo "::warning::No MSIX_PFX_FILE provided — generating an ephemeral" \
        "self-signed certificate instead. End users must manually trust" \
        "this certificate (e.g. via 'certutil -addstore TrustedPeople" \
        "<cert>' or PowerShell's Import-Certificate) before Windows will" \
        "allow installing this MSIX. See packaging/README.md's MSIX section."
    echo

    if [ -z "$MSIX_PFX_PASSPHRASE" ]; then
        # A passphrase is still required by Export-PfxCertificate even
        # though it's never meant to protect anything long-lived — the
        # cert/key are ephemeral and discarded after this build.
        MSIX_PFX_PASSPHRASE="$(date +%s%N)"
    fi

    MSIX_PFX_FILE="$STAGE_DIR/self-signed.pfx"
    generate_self_signed_msix_cert "$MSIX_PUBLISHER" "$MSIX_PFX_FILE" "$MSIX_PFX_PASSPHRASE"

    # Also export the public certificate alongside the package so it can
    # be uploaded/documented for end users to trust before installing.
    export_msix_public_cert "$MSIX_PFX_FILE" "$MSIX_PFX_PASSPHRASE" "$OUT_DIR/set-ttrpg-portrait-${VERSION}-self-signed.cer"
fi

export VERSION
export MSIX_PFX_FILE
export NFPM_MSIX_PASSPHRASE="$MSIX_PFX_PASSPHRASE"

mkdir -p "$OUT_DIR"
(cd "$REPO_ROOT" && "$NFPM" package \
    --config "$SCRIPT_DIR/nfpm.yaml" \
    --packager msix \
    --target "$OUT_DIR/set-ttrpg-portrait-${VERSION}-x64.msix")

echo "Built $OUT_DIR/set-ttrpg-portrait-${VERSION}-x64.msix"
