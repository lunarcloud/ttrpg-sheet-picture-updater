"""Allows `python -m set_ttrpg_portrait ...` invocation."""

from __future__ import annotations

import sys

from set_ttrpg_portrait.cli import main

if __name__ == "__main__":
    sys.exit(main())
