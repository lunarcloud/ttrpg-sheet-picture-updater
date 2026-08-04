"""Unit tests for set_ttrpg_portrait.launcher (AppImage's combined CLI+GUI dispatch)."""

from __future__ import annotations

from unittest.mock import patch

from set_ttrpg_portrait.launcher import main


def test_no_args_launches_gui() -> None:
    with patch("set_ttrpg_portrait.gui.main", return_value=0) as gui_main:
        exit_code = main([])
    assert exit_code == 0
    gui_main.assert_called_once()


def test_dash_dash_gui_launches_gui() -> None:
    with patch("set_ttrpg_portrait.gui.main", return_value=0) as gui_main:
        exit_code = main(["--gui"])
    assert exit_code == 0
    gui_main.assert_called_once()


def test_other_args_use_cli() -> None:
    with patch("set_ttrpg_portrait.cli.main", return_value=0) as cli_main:
        exit_code = main(["sheet.pdf", "portrait.jpg", "-o", "out.pdf"])
    assert exit_code == 0
    cli_main.assert_called_once_with(["sheet.pdf", "portrait.jpg", "-o", "out.pdf"])


def test_help_flag_uses_cli_not_gui() -> None:
    with patch("set_ttrpg_portrait.cli.main", return_value=0) as cli_main:
        exit_code = main(["--help"])
    assert exit_code == 0
    cli_main.assert_called_once_with(["--help"])
