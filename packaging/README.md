# Packaging: `.deb`, `.rpm`, AppImage, MSIX

Three different strategies, chosen per-format:

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
- **Windows `.msix`** (via `build-msix.sh`/`set-ttrpg-portrait-msix.spec`)
  mirrors the AppImage's approach — a PyInstaller-frozen one-dir build of
  the same combined CLI+GUI launcher, just targeting Windows. nfpm builds
  both deb/rpm and `.msix` from the same `packaging/nfpm.yaml` (its
  `overrides.msix.contents` replaces the shared Linux `contents:` list
  with the MSIX-specific staged files — see that file's comments). Note
  that nfpm supports `.msix` (Microsoft's modern app package format), not
  the older `.msi` installer format.
  - **Must be built on a native Windows host** (`.github/workflows/
    release.yml`'s `windows-latest` runner) — `pikepdf`'s platform-specific
    compiled wheel means the frozen `.exe` can't be cross-built from
    Linux/macOS, same constraint as the AppImage. nfpm's own MSIX packaging
    logic is pure Go, though, so `packaging/nfpm.yaml`'s `overrides.msix`
    section can be tested/validated using the Linux `nfpm` binary against a
    placeholder `.exe` without needing a Windows host at all.
  - **Signing**: Windows generally refuses to install an MSIX unless it's
    signed, even with a self-signed certificate. This project has no paid
    code-signing certificate, so `build-msix.sh` generates an ephemeral
    self-signed one at build time (via PowerShell's
    `New-SelfSignedCertificate`, see `packaging/lib/generate-msix-cert.sh`)
    whenever `MSIX_PFX_FILE` isn't supplied, and also exports its public
    half as a `.cer` alongside the `.msix`. **End users must manually
    import/trust that `.cer`** (e.g. `certutil -addstore TrustedPeople
    <cert.cer>`, or PowerShell's `Import-Certificate -CertStoreLocation
    Cert:\LocalMachine\TrustedPeople`) before Windows will allow installing
    the package — there's no way around this without a real, paid
    code-signing certificate. If/when one is available, set `MSIX_PFX_FILE`
    (and `MSIX_PFX_PASSPHRASE`) to use it instead, and that manual-trust
    step becomes unnecessary.
  - The MSIX's `publisher` field (`packaging/nfpm.yaml`'s `msix.publisher`,
    default `CN=lunarcloud` via `MSIX_PUBLISHER`) must exactly match
    whichever certificate's Subject signs it.

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
mid-build. `fetch_nfpm` detects Git Bash on Windows (via `uname -s`) and
fetches nfpm's separate Windows release asset automatically.

## Usage

From the repo root, with `.venv` set up (`./setup.sh`):

```
./packaging/build-deb.sh        # -> dist/packages/set-ttrpg-portrait_<version>_amd64.deb
./packaging/build-rpm.sh        # -> dist/packages/set-ttrpg-portrait-<version>-1.x86_64.rpm
./packaging/build-appimage.sh   # -> dist/packages/set-ttrpg-portrait-<version>-x86_64.AppImage
./packaging/build-all.sh        # builds all three Linux artifacts above
./packaging/build-msix.sh       # -> dist/packages/set-ttrpg-portrait-<version>-x64.msix (Windows only)
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
git tag that triggered the release. Two tag formats are recognized (either
works, the `release/`/`v` prefix is stripped either way): `release/<version>`
(e.g. `release/1.2.3` → `1.2.3`) or `v<version>` (e.g. `v1.2.3` → `1.2.3`).
Anything else (including a bare `1.2.3` with no prefix at all) → `0.0.0`,
with a workflow warning. See `tests/test_compute_version.py` for that
script's test coverage.

## Icon

Only `icon/icon-source.png` is a committed file — a hand-drawn (or, until
real artwork is provided, a generated placeholder showing safe-zone guides)
master icon. Every other icon file (`icons/hicolor/**/apps/set-ttrpg-portrait.png`,
`appimage/icon.png`, `msix/icon.ico`, `msix/Assets/*.png`) is generated by
`icon/generate_icons.py` and gitignored — this is the single source of
truth; nothing derived from it is ever hand-maintained or committed.

## Build natively per architecture

`pikepdf` ships platform-specific compiled wheels, so the AppImage's and
MSIX's PyInstaller builds must each run natively on their target OS/arch
(Linux x86_64 and Windows x64 respectively — see `.github/workflows/
release.yml`'s separate `ubuntu-latest`/`windows-latest` jobs). The
`.deb`/`.rpm` themselves are pure Python (no compiled wheel of our own to
bundle), so this constraint doesn't apply to them directly — but they
still declare `arch: amd64` in `packaging/nfpm.yaml` to match the other
artifacts, since the system packages they depend on are
architecture-specific anyway.

