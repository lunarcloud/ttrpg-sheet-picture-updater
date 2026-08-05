"""Tests for packaging/lib/compute-version.sh.

This is a bash script (not a Python module) so it's exercised here as a
subprocess, asserting on its stdout for a range of git ref names. It backs
.github/workflows/release.yml's version-resolution step, which overwrites
the committed .VERSION-PLACEHOLDER file (see pyproject.toml) from the
release tag before anything else builds — see packaging/README.md.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "packaging" / "lib" / "compute-version.sh"


def _compute_version(ref_name: str) -> str:
    """Run compute-version.sh with the given ref name and return its stdout, stripped."""
    result = subprocess.run(
        [str(SCRIPT), ref_name],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.mark.parametrize(
    ("ref_name", "expected_version"),
    [
        ("release/1.2.3", "1.2.3"),
        ("release/2", "2"),
        ("release/1.2.3-rc1", "1.2.3-rc1"),
        ("v1.2.3", "1.2.3"),
        ("v2", "2"),
        ("v1.2.3-rc1", "1.2.3-rc1"),
        ("main", "0.0.0"),
        ("some-branch", "0.0.0"),
        ("vNext", "0.0.0"),
        ("version1.2.3", "0.0.0"),
        ("1.2.3", "0.0.0"),
        ("release/", "0.0.0"),
        ("v", "0.0.0"),
        ("", "0.0.0"),
    ],
)
def test_compute_version(ref_name: str, expected_version: str) -> None:
    assert _compute_version(ref_name) == expected_version


def test_compute_version_missing_arg_defaults_to_0_0_0() -> None:
    # No ref-name argument at all (simulates $GITHUB_REF_NAME being unset).
    result = subprocess.run(
        [str(SCRIPT)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "0.0.0"
