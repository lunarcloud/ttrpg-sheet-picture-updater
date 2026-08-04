#!/usr/bin/env python3
"""Thin shim so `python set_ttrpg_portrait_launcher.py ...` keeps working.

All real logic lives in `set_ttrpg_portrait/launcher.py`. This is only used
to build the AppImage's single combined CLI+GUI binary — see
`packaging/set-ttrpg-portrait-appimage.spec`.
"""

from __future__ import annotations

import sys

from set_ttrpg_portrait.launcher import main

if __name__ == "__main__":
    sys.exit(main())
