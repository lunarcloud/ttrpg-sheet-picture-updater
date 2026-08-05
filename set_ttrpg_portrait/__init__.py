"""set_ttrpg_portrait: embed a portrait image into a fillable PDF character sheet."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _installed_version

try:
    # Single source of truth: .VERSION-PLACEHOLDER, read by pyproject.toml's
    # `[tool.setuptools.dynamic]` at install time. For real releases, CI
    # overwrites that file from the "release/#" git tag before building
    # (see packaging/lib/compute-version.sh) — locally it's always "0.0.0".
    # Re-run `./setup.sh` (or `pip install -e .`) after it changes so this
    # picks it up.
    __version__ = _installed_version("set-ttrpg-portrait")
except PackageNotFoundError:
    # Only reachable if this package is imported without being installed
    # (e.g. running from a raw source checkout with no `pip install -e .`).
    __version__ = "0.0.0+unknown"

from set_ttrpg_portrait.errors import (
    AmbiguousFieldError,
    FieldNotFoundError,
    InvalidPdfError,
    NoCandidateFieldError,
    SetTtrpgPortraitError,
)

__all__ = [
    "__version__",
    "SetTtrpgPortraitError",
    "NoCandidateFieldError",
    "AmbiguousFieldError",
    "FieldNotFoundError",
    "InvalidPdfError",
]
