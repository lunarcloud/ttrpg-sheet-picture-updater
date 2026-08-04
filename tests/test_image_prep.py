"""Unit tests for set_ttrpg_portrait.image_prep (Pillow-based fit/encode logic)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from set_ttrpg_portrait.image_prep import (
    fit_image,
    image_to_jpeg_bytes,
    load_portrait,
    prepare_portrait_jpeg,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_portrait_returns_rgb_image() -> None:
    image = load_portrait(str(FIXTURES / "portrait.jpg"))
    assert image.mode == "RGB"


def test_load_portrait_normalizes_png_to_rgb() -> None:
    image = load_portrait(str(FIXTURES / "portrait.png"))
    assert image.mode == "RGB"


def test_load_portrait_flattens_transparency_onto_white() -> None:
    image = load_portrait(str(FIXTURES / "portrait_transparent.png"))
    assert image.mode == "RGB"
    # Corner of the source fixture is fully transparent -> should become
    # opaque white, not a garbage/black color from a naive alpha drop.
    assert image.getpixel((0, 0)) == (255, 255, 255)


def test_load_portrait_blends_partial_transparency_toward_white() -> None:
    source = Image.open(str(FIXTURES / "portrait_transparent.png"))
    image = load_portrait(str(FIXTURES / "portrait_transparent.png"))
    # Pick a pixel from the fixture's semi-transparent "body" rectangle and
    # confirm it blended toward white rather than staying at its raw color.
    x, y = 150, 399
    raw_r, raw_g, raw_b, alpha = source.convert("RGBA").getpixel((x, y))
    assert 0 < alpha < 255
    blended = image.getpixel((x, y))
    expected = tuple(
        round(channel * alpha / 255 + 255 * (1 - alpha / 255))
        for channel in (raw_r, raw_g, raw_b)
    )
    assert blended == expected


@pytest.mark.parametrize("mode", ["cover", "contain"])
def test_fit_image_produces_exact_target_size(mode: str) -> None:
    source = Image.new("RGB", (500, 300), color="red")
    fitted = fit_image(source, (160, 220), mode=mode)
    assert fitted.size == (160, 220)


def test_fit_image_cover_crops_no_padding() -> None:
    # A wide source fit "cover" into a narrower/taller target should be
    # cropped, not letterboxed — check no white padding is introduced by
    # using a source with no white pixels.
    source = Image.new("RGB", (400, 100), color=(10, 20, 30))
    fitted = fit_image(source, (100, 100), mode="cover")
    assert fitted.getpixel((0, 0)) == (10, 20, 30)


def test_fit_image_contain_letterboxes_with_white() -> None:
    source = Image.new("RGB", (400, 100), color=(10, 20, 30))
    fitted = fit_image(source, (100, 100), mode="contain")
    # Corners should be white padding since the source is much wider than tall.
    assert fitted.getpixel((0, 0)) == (255, 255, 255)


def test_fit_image_rejects_unknown_mode() -> None:
    source = Image.new("RGB", (10, 10), color="blue")
    with pytest.raises(ValueError):
        fit_image(source, (10, 10), mode="stretch")


def test_fit_image_rejects_invalid_target_size() -> None:
    source = Image.new("RGB", (10, 10), color="blue")
    with pytest.raises(ValueError):
        fit_image(source, (0, 10))


def test_image_to_jpeg_bytes_round_trips() -> None:
    source = Image.new("RGB", (50, 50), color="green")
    data = image_to_jpeg_bytes(source)
    assert data[:2] == b"\xff\xd8"  # JPEG magic bytes
    reopened = Image.open(io.BytesIO(data))
    assert reopened.size == (50, 50)


def test_prepare_portrait_jpeg_end_to_end() -> None:
    data = prepare_portrait_jpeg(str(FIXTURES / "portrait.jpg"), (160.0, 220.0))
    reopened = Image.open(io.BytesIO(data))
    assert reopened.size == (160, 220)
