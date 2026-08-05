#!/usr/bin/env bash
# Computes this project's release version from a git ref name, without
# touching the filesystem — pure "ref name in, version string out" so it's
# trivially unit-testable (see tests/test_compute_version.py).
#
# Rules:
#   - "release/<version>" (e.g. "release/1.2.3", "release/2")  -> "<version>"
#   - anything else (branch names, other tags, empty/unset ref) -> "0.0.0"
#
# Usage: packaging/lib/compute-version.sh <ref-name>
#   Prints the resolved version to stdout. Callers that need to update
#   .VERSION-PLACEHOLDER should redirect this script's output themselves,
#   e.g.: packaging/lib/compute-version.sh "$GITHUB_REF_NAME" > .VERSION-PLACEHOLDER
set -euo pipefail

ref_name="${1:-}"

if [[ "$ref_name" =~ ^release/(.+)$ ]]; then
    echo "${BASH_REMATCH[1]}"
else
    echo "0.0.0"
fi
