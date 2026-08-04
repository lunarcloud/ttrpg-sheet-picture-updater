"""Allows `python -m update_portrait ...` invocation."""

from __future__ import annotations

import sys

from update_portrait.cli import main

if __name__ == "__main__":
    sys.exit(main())
