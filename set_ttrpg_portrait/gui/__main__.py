"""Allows `python -m set_ttrpg_portrait.gui` to launch the GUI directly."""

from __future__ import annotations

import sys

from set_ttrpg_portrait.gui import main

if __name__ == "__main__":
    sys.exit(main())
