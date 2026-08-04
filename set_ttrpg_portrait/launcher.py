"""Combined CLI+GUI entry point — used only for the AppImage build.

The `.deb`/`.rpm` packages ship the CLI (`set-ttrpg-portrait`) and GUI
(`set-ttrpg-portrait-gui`) as two separate commands. The AppImage instead
bundles a single executable so double-clicking it "just works" like a
normal desktop app, while still behaving like the familiar CLI when given
arguments (e.g. from a terminal or script):

- No arguments, or `--gui` as the first argument -> launches the GUI.
- Any other arguments -> behaves exactly like the `set-ttrpg-portrait` CLI.

Deliberately kept separate from `cli.py`/`gui.py` so neither of those
modules (or their own frozen `.deb`/`.rpm` binaries) needs to know this
dispatch logic exists.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    if not args or args[0] == "--gui":
        from set_ttrpg_portrait.gui import main as gui_main

        gui_argv = args[1:] if args and args[0] == "--gui" else []
        return gui_main([sys.argv[0], *gui_argv])

    from set_ttrpg_portrait.cli import main as cli_main

    return cli_main(args)


if __name__ == "__main__":
    sys.exit(main())
