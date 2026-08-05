#!/usr/bin/env python3
"""Launcher installed by the .deb/.rpm package at /usr/bin/set-ttrpg-portrait.

Unlike the AppImage (which bundles its own private copy of everything,
including Qt), the .deb/.rpm packages rely on the distro's own
python3-pyqt6/python3-pikepdf/python3-pil/python3-pymupdf packages for
their compiled dependencies (see packaging/nfpm.yaml's `depends`) — only
this project's own pure-Python code is shipped, staged by
packaging/lib/stage-files.sh into /usr/share/set-ttrpg-portrait/lib (kept
off the distro's versioned site-packages/dist-packages path so this one
package layout works unmodified across Python minor versions). This
script just points `sys.path` at that directory before importing.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path("/usr/share/set-ttrpg-portrait/lib")))

from set_ttrpg_portrait.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
