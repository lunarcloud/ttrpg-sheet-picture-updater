"""set_ttrpg_portrait: embed a portrait image into a fillable PDF character sheet."""

from __future__ import annotations

__version__ = "0.1.0"

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
