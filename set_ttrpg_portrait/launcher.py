"""Combined CLI+GUI entry point — used for the AppImage/Windows installer/
.dmg builds' single combined executable.

The `.deb`/`.rpm` packages ship the CLI (`set-ttrpg-portrait`) and GUI
(`set-ttrpg-portrait-gui`) as two separate commands. The frozen builds
instead bundle a single executable so double-clicking it "just works" like
a normal desktop app, while still behaving like the familiar CLI when given
arguments (e.g. from a terminal or script):

- No arguments, or `--gui` as the first argument -> launches the GUI.
- Any other arguments -> behaves exactly like the `set-ttrpg-portrait` CLI.

Deliberately kept separate from `cli.py`/`gui.py` so neither of those
modules (or their own frozen `.deb`/`.rpm` binaries) needs to know this
dispatch logic exists.
"""

from __future__ import annotations

import sys


def _attach_windows_console() -> None:
    """Make CLI output visible when the frozen Windows .exe is run as a CLI.

    `set-ttrpg-portrait-windows.spec` builds with PyInstaller's windowed
    (console=False) subsystem so double-clicking the .exe (GUI mode)
    doesn't flash a console window open first — unlike the AppImage/macOS
    builds, Windows is the only target where "console vs. windowed
    subsystem" is even a thing the OS enforces. But a windowed-subsystem
    .exe has no console of its own to print to, so when actually invoked
    as a CLI from an existing terminal, attach to *that* terminal's
    console instead (only if one isn't already attached, so this is a
    no-op for the AppImage/.dmg or a plain `python` run, which already
    have one) so stdout/stderr reach it like any normal CLI tool.
    """
    import ctypes

    kernel32 = ctypes.windll.kernel32
    if kernel32.GetConsoleWindow():
        return  # already attached (e.g. a plain `python` run) -- no-op.
    ATTACH_PARENT_PROCESS = -1
    if kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
        sys.stdout = open("CONOUT$", "w")  # noqa: SIM115 (kept open for the process lifetime)
        sys.stderr = open("CONOUT$", "w")  # noqa: SIM115
        sys.stdin = open("CONIN$")  # noqa: SIM115


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    if not args or args[0] == "--gui":
        from set_ttrpg_portrait.gui import main as gui_main

        gui_argv = args[1:] if args and args[0] == "--gui" else []
        return gui_main([sys.argv[0], *gui_argv])

    if sys.platform == "win32" and getattr(sys, "frozen", False):
        _attach_windows_console()

    from set_ttrpg_portrait.cli import main as cli_main

    return cli_main(args)


if __name__ == "__main__":
    sys.exit(main())
