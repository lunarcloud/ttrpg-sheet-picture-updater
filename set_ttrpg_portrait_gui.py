#!/usr/bin/env python3
"""Thin shim so `python set_ttrpg_portrait_gui.py` keeps working.

All real logic lives in `set_ttrpg_portrait/gui.py`.
"""

from __future__ import annotations

import sys

from set_ttrpg_portrait.gui import main

if __name__ == "__main__":
    sys.exit(main())
