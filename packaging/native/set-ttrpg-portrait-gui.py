#!/usr/bin/env python3
"""Launcher installed by the .deb/.rpm package at /usr/bin/set-ttrpg-portrait-gui.

See the sibling `set-ttrpg-portrait` launcher's docstring for why this
points `sys.path` at /usr/share/set-ttrpg-portrait/lib instead of relying
on PyInstaller-style bundling.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path("/usr/share/set-ttrpg-portrait/lib")))

from set_ttrpg_portrait.gui import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
