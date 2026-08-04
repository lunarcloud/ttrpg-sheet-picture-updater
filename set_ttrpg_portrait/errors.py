"""Custom exception types for set_ttrpg_portrait.

Keeping these separate from the logic layer lets ``cli.py`` catch a small,
well-known set of errors in one place and turn them into clear stderr
messages/exit codes, instead of scattering ``sys.exit()`` calls or string
matching throughout the field-detection and PDF-editing code.
"""

from __future__ import annotations


class SetTtrpgPortraitError(Exception):
    """Base class for all expected/handled errors raised by this tool."""


class NoCandidateFieldError(SetTtrpgPortraitError):
    """Raised when no portrait/image button field could be found on the sheet."""


class AmbiguousFieldError(SetTtrpgPortraitError):
    """Raised when more than one field matches the portrait-field heuristic."""


class FieldNotFoundError(SetTtrpgPortraitError):
    """Raised when an explicitly-requested ``--field`` name doesn't exist."""


class InvalidPdfError(SetTtrpgPortraitError):
    """Raised when the sheet PDF can't be opened (missing, corrupt, encrypted)."""
