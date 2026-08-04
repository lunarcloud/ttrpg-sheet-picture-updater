"""update_portrait: embed a portrait image into a fillable PDF character sheet."""

from __future__ import annotations

__version__ = "0.1.0"

from update_portrait.errors import (
    AmbiguousFieldError,
    FieldNotFoundError,
    InvalidPdfError,
    NoCandidateFieldError,
    UpdatePortraitError,
)

__all__ = [
    "__version__",
    "UpdatePortraitError",
    "NoCandidateFieldError",
    "AmbiguousFieldError",
    "FieldNotFoundError",
    "InvalidPdfError",
]
