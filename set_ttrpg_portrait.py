#!/usr/bin/env python3
"""Thin shim so `python set_ttrpg_portrait.py ...` keeps working.

All real logic lives in the `set_ttrpg_portrait` package (see `cli.py`,
`fields.py`, `image_prep.py`, `pdf_ops.py`, `errors.py`).
"""

from __future__ import annotations

import sys

from set_ttrpg_portrait.cli import main

if __name__ == "__main__":
    sys.exit(main())
