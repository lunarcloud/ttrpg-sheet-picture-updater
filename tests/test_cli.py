"""End-to-end CLI tests, driving set_ttrpg_portrait.cli.main() against fixtures."""

from __future__ import annotations

from pathlib import Path

import pikepdf
import pytest

from set_ttrpg_portrait.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def _field_names(pdf_path: Path) -> set[str]:
    pdf = pikepdf.open(pdf_path)
    acroform = pdf.Root.get("/AcroForm")
    if acroform is None or "/Fields" not in acroform:
        return set()
    return {str(field.T) for field in acroform.Fields if "/T" in field}


def _has_icon(pdf_path: Path, field_name: str) -> bool:
    """True if `field_name`'s widget(s) still exist as a Button with an icon set."""
    pdf = pikepdf.open(pdf_path)
    acroform = pdf.Root.AcroForm
    for field in acroform.Fields:
        if "/T" not in field or str(field.T) != field_name:
            continue
        assert str(field.FT) == "/Btn"  # must remain a live pushbutton field
        annots = [field] if "/Rect" in field else list(field.get("/Kids", []))
        return all("/MK" in a and "/I" in a.MK and "/AP" in a for a in annots)
    return False


def test_cli_success_auto_detect(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    exit_code = main(
        [
            str(FIXTURES / "simple_sheet.pdf"),
            str(FIXTURES / "portrait.jpg"),
            "-o",
            str(output),
        ]
    )
    assert exit_code == 0
    assert output.exists()
    # The portrait field stays present as a live Button with an icon set,
    # so it remains replaceable later (matches Acrobat's own behavior).
    assert "Portrait" in _field_names(output)
    assert _has_icon(output, "Portrait")
    assert "Character Name" in _field_names(output)


def test_cli_success_field_override(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    exit_code = main(
        [
            str(FIXTURES / "multi_field_sheet.pdf"),
            str(FIXTURES / "portrait.jpg"),
            "-o",
            str(output),
            "--field",
            "Pic1",
        ]
    )
    assert exit_code == 0
    names = _field_names(output)
    assert "Pic1" in names
    assert _has_icon(output, "Pic1")
    assert {"Character Name", "Class", "Level"} <= names


def test_cli_png_input_normalizes(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    exit_code = main(
        [
            str(FIXTURES / "simple_sheet.pdf"),
            str(FIXTURES / "portrait.png"),
            "-o",
            str(output),
        ]
    )
    assert exit_code == 0
    assert output.exists()
    assert _has_icon(output, "Portrait")


def test_cli_transparent_png_input_flattens_to_white(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    exit_code = main(
        [
            str(FIXTURES / "simple_sheet.pdf"),
            str(FIXTURES / "portrait_transparent.png"),
            "-o",
            str(output),
        ]
    )
    assert exit_code == 0
    assert output.exists()
    assert _has_icon(output, "Portrait")


@pytest.mark.parametrize("fit_mode", ["cover", "contain"])
def test_cli_fit_modes(tmp_path: Path, fit_mode: str) -> None:
    output = tmp_path / "out.pdf"
    exit_code = main(
        [
            str(FIXTURES / "simple_sheet.pdf"),
            str(FIXTURES / "portrait.jpg"),
            "-o",
            str(output),
            "--fit",
            fit_mode,
        ]
    )
    assert exit_code == 0
    assert output.exists()


def test_cli_no_candidate_field_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "out.pdf"
    exit_code = main(
        [
            str(FIXTURES / "no_image_sheet.pdf"),
            str(FIXTURES / "portrait.jpg"),
            "-o",
            str(output),
        ]
    )
    assert exit_code == 1
    assert not output.exists()
    assert "Error" in capsys.readouterr().err


def test_cli_ambiguous_field_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "out.pdf"
    exit_code = main(
        [
            str(FIXTURES / "ambiguous_sheet.pdf"),
            str(FIXTURES / "portrait.jpg"),
            "-o",
            str(output),
        ]
    )
    assert exit_code == 1
    assert not output.exists()
    assert "Error" in capsys.readouterr().err


def test_cli_list_fields(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(FIXTURES / "simple_sheet.pdf"), "--list-fields"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Portrait" in out


def test_cli_list_fields_no_buttons(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(FIXTURES / "no_image_sheet.pdf"), "--list-fields"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "No pushbutton fields" in out


def test_cli_missing_sheet_file_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            str(tmp_path / "does-not-exist.pdf"),
            str(FIXTURES / "portrait.jpg"),
            "-o",
            str(tmp_path / "o.pdf"),
        ]
    )
    assert exit_code == 1
    assert "Error" in capsys.readouterr().err
