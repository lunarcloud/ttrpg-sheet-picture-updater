"""Unit tests for set_ttrpg_portrait.fields (pure heuristic + discovery logic)."""

from __future__ import annotations

from pathlib import Path

import pikepdf
import pytest

from set_ttrpg_portrait.errors import (
    AmbiguousFieldError,
    FieldNotFoundError,
    NoCandidateFieldError,
)
from set_ttrpg_portrait.fields import (
    FieldCandidate,
    FieldLocation,
    find_button_fields,
    find_portrait_field,
    is_portrait_field_name,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "name",
    [
        "Portrait",
        "portrait",
        "CHARACTER IMAGE",
        "Photo_af_image",
        "Image",
        "Player Image",
        "headshot",
    ],
)
def test_is_portrait_field_name_matches(name: str) -> None:
    assert is_portrait_field_name(name) is True


@pytest.mark.parametrize("name", ["Character Name", "Class", "Level", "Pic1", ""])
def test_is_portrait_field_name_rejects(name: str) -> None:
    assert is_portrait_field_name(name) is False


def test_find_button_fields_simple_sheet() -> None:
    pdf = pikepdf.open(FIXTURES / "simple_sheet.pdf")
    candidates = find_button_fields(pdf)
    assert candidates == [
        FieldCandidate(
            "Portrait",
            (FieldLocation(page_index=0, rect=(20.0, 280.0, 180.0, 440.0)),),
        )
    ]


def test_find_button_fields_no_image_sheet() -> None:
    pdf = pikepdf.open(FIXTURES / "no_image_sheet.pdf")
    assert find_button_fields(pdf) == []


def test_find_portrait_field_auto_detect() -> None:
    pdf = pikepdf.open(FIXTURES / "simple_sheet.pdf")
    candidate = find_portrait_field(pdf)
    assert candidate.name == "Portrait"


def test_find_portrait_field_less_obvious_name() -> None:
    pdf = pikepdf.open(FIXTURES / "multi_field_sheet.pdf")
    candidate = find_portrait_field(pdf, field_name="Pic1")
    assert candidate.name == "Pic1"


def test_find_portrait_field_no_candidate_raises() -> None:
    pdf = pikepdf.open(FIXTURES / "no_image_sheet.pdf")
    with pytest.raises(NoCandidateFieldError):
        find_portrait_field(pdf)


def test_find_portrait_field_ambiguous_raises() -> None:
    pdf = pikepdf.open(FIXTURES / "ambiguous_sheet.pdf")
    with pytest.raises(AmbiguousFieldError):
        find_portrait_field(pdf)


def test_find_portrait_field_ambiguous_resolved_with_field_name() -> None:
    pdf = pikepdf.open(FIXTURES / "ambiguous_sheet.pdf")
    candidate = find_portrait_field(pdf, field_name="Player Image")
    assert candidate.name == "Player Image"


def test_find_portrait_field_unknown_field_name_raises() -> None:
    pdf = pikepdf.open(FIXTURES / "simple_sheet.pdf")
    with pytest.raises(FieldNotFoundError):
        find_portrait_field(pdf, field_name="Does Not Exist")
