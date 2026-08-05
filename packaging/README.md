# Packaging: `.deb`, `.rpm`, AppImage

Two different strategies, chosen per-format:

- **`.deb`/`.rpm`** ship this project's own plain Python source (no
  PyInstaller), plus two thin launcher scripts
  (`packaging/native/set-ttrpg-portrait{,-gui}`). They rely on the
  distro's own `python3-pyqt6`/`python3-pikepdf`/`python3-pil`/
  `python3-pymupdf` (Debian/Ubuntu) or `python3-pyqt6`/`python3-pikepdf`/
  `python3-pillow`/`python3-PyMuPDF` (Fedora) packages for their compiled
  dependencies — declared in `packaging/nfpm.yaml`'s `depends`. This means
  apt/dnf resolve the *entire* transitive dependency chain automatically
  (down to X11/Wayland/GL/D-Bus/fontconfig/etc), rather than this repo
  hand-maintaining that list, and end users get security updates to those
  libraries through their normal distro update mechanism. The trade-off:
  `python3` and those four packages must already be installed (or
  installable) on the target system — reasonable for the desktop
  Linux distros this targets, but unlike the AppImage below, not fully
  self-contained.
  - One wrinkle: loading `main_window.ui` at runtime normally needs
    `PyQt6.uic`, but Debian/Ubuntu split that submodule out of
    `python3-pyqt6` into the separate (if confusingly-named)
    `pyqt6-dev-tools` package. Rather than adding that as a runtime
    dependency, `stage-files.sh` precompiles `main_window.ui` into a plain
    `main_window_ui.py` at package-build time via `pyuic6` (which ships as
    part of the `PyQt6` *pip* package itself — no extra build tool needed),
    so the installed `.deb`/`.rpm` never needs `PyQt6.uic` at all. See
    `set_ttrpg_portrait/gui/main_window.py`'s module docstring and
    `tests/test_gui_precompiled_ui.py`.
- **AppImage** is fully self-contained: a PyInstaller-frozen one-dir build
  (see `set-ttrpg-portrait-appimage.spec`) plus `linuxdeploy` to bundle the
  handful of system libraries PyInstaller alone misses (Qt's own
  plugins dynamically link against X11/XCB extensions, D-Bus,
  fontconfig/freetype, glib, xkbcommon — see `build-appimage.sh`'s
  comments for the full rationale and the AppImage project's own
  "excludelist" of libraries deliberately left to the host, like
  GL/EGL/Mesa and base X11). No distro package manager or system Python
  needed at all — this is the right choice for one-off/portable use, or
  distros the `.deb`/`.rpm` don't cover.

## Build-time tools (not needed by end users)

- **PyInstaller** — already an optional `dev` dependency in
  `pyproject.toml`, installed by `./setup.sh`. Only used for the AppImage.
- **[`nfpm`](https://nfpm.goreleaser.com/)** — required by
  `build-deb.sh`/`build-rpm.sh`. A single static Go binary, no
  interpreter/package-manager dependency. Builds both `.deb` and `.rpm`
  fully natively — no `rpmbuild`, Ruby, or other external tools needed.
- **`appimagetool`** — required by `build-appimage.sh`. Also a standalone
  binary; builds the final `.AppImage` from the `linuxdeploy`-populated
  `AppDir`.
- **`linuxdeploy`** — also required by `build-appimage.sh`. Statically
  discovers and bundles the AppImage's missing system-library
  dependencies (see above).

All three tools are fetched on demand to `packaging/tools/` (gitignored,
never committed, never installed system-wide) — run `./setup.sh` from the
repo root and answer "y" to the "Set up packaging tools too?" prompt, or run
`packaging/lib/fetch-tools.sh`'s `fetch_nfpm`/`fetch_appimagetool`/
`fetch_linuxdeploy` functions directly. The `build-*.sh` scripts will tell
you to do this if a tool is missing, rather than downloading it themselves
mid-build.

## Usage

From the repo root, with `.venv` set up (`./setup.sh`):

```
./packaging/build-deb.sh        # -> dist/packages/set-ttrpg-portrait_<version>_amd64.deb
./packaging/build-rpm.sh        # -> dist/packages/set-ttrpg-portrait-<version>-1.x86_64.rpm
./packaging/build-appimage.sh   # -> dist/packages/set-ttrpg-portrait-<version>-x86_64.AppImage
./packaging/build-all.sh        # builds all three
```

To install the resulting `.deb`/`.rpm` you'll need the system packages
listed above installed first (`sudo apt install python3-pyqt6
python3-pikepdf python3-pil python3-pymupdf` on Debian/Ubuntu, or `sudo dnf
install python3-pyqt6 python3-pikepdf python3-pillow python3-PyMuPDF` on
Fedora) — `apt`/`dnf` will otherwise pull them in automatically as part of
installing the `.deb`/`.rpm` itself, same as any other native package.
`.github/workflows/release.yml`'s `test-deb-install`/`test-rpm-install`
jobs install and smoke-test the built packages in real `debian:stable`/
`fedora:latest` containers on every release, to catch a wrong/missing
system package name before it ships.

Version numbers come from `.VERSION-PLACEHOLDER` at the repo root —
`pyproject.toml` reads it dynamically (`version = { file = ".VERSION-PLACEHOLDER" }`),
and `set_ttrpg_portrait.__version__` resolves it via `importlib.metadata` at
runtime. **Never hand-edit that file** — it's committed as `0.0.0` (what
local dev installs and non-release CI runs always see) and is only ever
overwritten, in `.github/workflows/release.yml`'s first step, by
`packaging/lib/compute-version.sh`, which derives the real version from the
`release/<version>` git tag that triggered the release (e.g. tag
`release/1.2.3` → version `1.2.3`; anything else → `0.0.0`, with a
workflow warning). See `tests/test_compute_version.py` for that script's
test coverage.

## Icon

Only `icon/icon-source.png` is a committed file — a hand-drawn (or, until
real artwork is provided, a generated placeholder showing safe-zone guides)
master icon. Every other icon file (`icons/hicolor/**/apps/set-ttrpg-portrait.png`,
`appimage/icon.png`) is generated by `icon/generate_icons.py` and gitignored.

## Build natively per architecture

`pikepdf` ships platform-specific compiled wheels, so the AppImage's
PyInstaller build must run natively on each target OS/arch you want a
package for — these scripts assume a Linux x86_64 build host. The `.deb`/
`.rpm` themselves are pure Python (no compiled wheel of our own to bundle),
so this constraint doesn't apply to them directly — but they still declare
`arch: amd64` in `packaging/nfpm.yaml` to match the other two artifacts,
since the system packages they depend on are architecture-specific anyway.

