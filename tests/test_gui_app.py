"""Tests for platform-specific GUI startup defaults."""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest

from set_ttrpg_portrait.gui import app


@pytest.mark.parametrize(
    ("platform", "theme", "expected"),
    [
        ("linux", None, "xdgdesktopportal"),
        ("linux", "gtk3", "gtk3"),
        ("darwin", None, None),
        ("darwin", "custom", "custom"),
        ("win32", None, None),
    ],
)
def test_startup_theme_defaults(
    monkeypatch: pytest.MonkeyPatch, platform: str, theme: str | None, expected: str | None
) -> None:
    """Only Linux defaults to the portal, before QApplication is created."""
    monkeypatch.setattr(app.sys, "platform", platform)
    if theme is None:
        monkeypatch.delenv("QT_QPA_PLATFORMTHEME", raising=False)
    else:
        monkeypatch.setenv("QT_QPA_PLATFORMTHEME", theme)

    application = Mock()
    application.exec.return_value = 17
    window = Mock()
    icon = Mock()

    def create_application(argv: list[str]) -> Mock:
        assert argv == ["test-app"]
        assert os.environ.get("QT_QPA_PLATFORMTHEME") == expected
        return application

    monkeypatch.setattr(app, "QApplication", create_application)
    monkeypatch.setattr(app, "MainWindow", lambda: window)
    monkeypatch.setattr(app, "app_icon", lambda: icon)

    assert app.main(["test-app"]) == 17
    application.setApplicationName.assert_called_once_with("Set TTRPG Portrait")
    window.show.assert_called_once_with()
