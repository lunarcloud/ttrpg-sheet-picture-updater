"""Regression coverage for the macOS bundle's foreground-app configuration."""

from __future__ import annotations

import ast
from pathlib import Path


def test_console_launcher_is_packaged_as_a_foreground_app() -> None:
    """Override PyInstaller's console-mode background flag without losing CLI output."""
    spec = Path(__file__).resolve().parent.parent / "packaging" / "set-ttrpg-portrait-macos.spec"
    tree = ast.parse(spec.read_text())
    calls = {
        node.func.id: {keyword.arg: keyword.value for keyword in node.keywords}
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert ast.literal_eval(calls["EXE"]["console"]) is True
    plist = calls["BUNDLE"]["info_plist"]
    assert isinstance(plist, ast.Dict)
    values = {
        ast.literal_eval(key): value for key, value in zip(plist.keys, plist.values, strict=True) if key is not None
    }
    assert ast.literal_eval(values["LSBackgroundOnly"]) is False
    assert ast.literal_eval(values["LSUIElement"]) is False
    assert ast.literal_eval(values["CFBundleName"]) == "Set TTRPG Portrait"
    assert ast.literal_eval(values["CFBundleDisplayName"]) == "Set TTRPG Portrait"
