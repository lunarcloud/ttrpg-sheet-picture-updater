# Packaging: `.deb`, `.rpm`, AppImage, Windows installer, macOS `.dmg`

Four different strategies, chosen per-format:

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
- **Windows installer `.exe`** (via `build-nsis.sh`/
  `set-ttrpg-portrait-windows.spec`/`packaging/windows/installer.nsi`)
  mirrors the AppImage's approach — a PyInstaller-frozen one-dir build of
  the same combined CLI+GUI launcher, just targeting Windows, wrapped into
  a standard NSIS installer `.exe` via `makensis`.
  - **Must be built on a native Windows host** (`.github/workflows/
    release.yml`'s `windows-latest` runner) — `pikepdf`'s platform-specific
    compiled wheel means the frozen `.exe` can't be cross-built from
    Linux/macOS, same constraint as the AppImage. `makensis` itself is
    NOT preinstalled on `windows-latest` runners, but Chocolatey is —
    `release.yml`'s `build-windows-installer` job installs it via
    `choco install nsis`. For local builds, see `fetch_makensis` in
    `packaging/lib/fetch-tools.sh`, or install NSIS yourself from
    <https://nsis.sourceforge.io/>.
  - Installs per-user (to `%LOCALAPPDATA%\Programs\set-ttrpg-portrait`,
    registry entries under `HKCU`) — no admin/UAC elevation required.
  - **No signing**: this project previously shipped a `.msix`, but MSIX
    packages must be signed even with a self-signed certificate, and
    without a paid code-signing certificate, end users had to manually
    import/trust an ephemeral self-signed one before Windows would even
    install the package — a confusing, error-prone step. The NSIS `.exe`
    is unsigned instead: end users just see a dismissable Windows
    SmartScreen "Windows protected your PC" prompt the first time they run
    it (click "More info" then "Run anyway") — no certificate import step
    at all. If a paid code-signing certificate becomes available later,
    `build-nsis.sh` could be extended to sign the output with
    `signtool.exe`.
- **macOS `.dmg`** (via `build-macos.sh`/`set-ttrpg-portrait-macos.spec`),
  **Apple Silicon (arm64) only — no Intel build is produced.** Like the
  AppImage/Windows installer, it's a PyInstaller-frozen one-dir build of the same
  combined CLI+GUI launcher, wrapped in a PyInstaller `BUNDLE()` to produce
  a standard `set-ttrpg-portrait.app`, then packaged into a `.dmg` with
  `hdiutil` (built into every macOS host — no extra packaging tool needed,
  unlike nfpm for the other formats; macOS has no equivalent to nfpm). The
  `.dmg` contains the `.app` plus a symlink to `/Applications`, the
  standard "drag the icon over" installation pattern for Mac GUI apps.
  Advanced users wanting CLI access can invoke
  `/Applications/set-ttrpg-portrait.app/Contents/MacOS/set-ttrpg-portrait-launcher`
  directly, or symlink it onto their own `PATH`.
  - **Must be built on a native macOS arm64 host** (`.github/workflows/
    release.yml`'s `macos-latest` runner, which is Apple Silicon by
    default) — same `pikepdf` compiled-wheel constraint as the AppImage/
    Windows installer.
  - **Icon**: `packaging/icon/generate_icons.py` generates the required
    `AppIcon.iconset/` PNGs (cross-platform, Pillow-only), but converting
    that to the final `.icns` needs a dedicated tool — `build-macos.sh`
    uses `iconutil` (built into macOS, via `packaging/lib/make-icns.sh`).
    That script also supports `png2icns` (from the `icnsutils`/`libicns`
    package) as a fallback purely so this conversion step can be exercised
    on non-macOS dev machines; real builds always use `iconutil` since
    `build-macos.sh` only ever runs on macOS.
  - **Signing**: unsigned arm64 binaries are refused outright on Apple
    Silicon, so `build-macos.sh` always ad-hoc signs the `.app`
    (`codesign --sign -`) — but this project has no paid Apple Developer
    Program membership ($99/year) to get a real Developer ID certificate,
    so Gatekeeper still flags the app as being from an "unidentified
    developer" the first time a user opens it after downloading. **End
    users must right-click (or Control-click) the app in Finder and choose
    "Open"** (accepting the one-time warning dialog) instead of
    double-clicking it the first time — or remove the quarantine attribute
    themselves via `xattr -cr /Applications/set-ttrpg-portrait.app`. If a
    real Developer ID certificate becomes available later, set
    `MACOS_SIGN_IDENTITY` to its name instead of the ad-hoc default (`-`)
    to sign properly (notarization would still be a separate, unimplemented
    step).
  - **Caveat**: `cairosvg` (used to rasterize SVG portraits, see
    `set_ttrpg_portrait/image_prep.py`) depends on `libcairo` being
    loadable at runtime via `ctypes.util.find_library`. Unlike the
    `.deb`/`.rpm` (which declare it as a system package dependency), none
    of the frozen builds (AppImage/Windows installer/`.dmg`) bundle or
    declare it. Since
    cairocffi loads it with `ctypes` at *import* time rather than lazily,
    `image_prep.py` imports `cairosvg` only inside `_rasterize_svg()`
    (not at module scope) so a missing Cairo install only breaks loading
    that one SVG (raising `SvgSupportUnavailableError` with a clear
    message) instead of crashing the whole app on startup. A Mac without
    Cairo installed (e.g. via Homebrew's `cairo` package) simply can't load
    SVG portraits until it's installed; every other image format is
    unaffected.

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
- **`makensis` (NSIS)** — required by `build-nsis.sh`. NOT preinstalled on
  `windows-latest` CI runners; `release.yml`'s `build-windows-installer`
  job installs it via Chocolatey (`choco install nsis`, also preinstalled
  on those runners). For local Windows dev builds without choco, it's
  fetched the same way as the other tools below (NSIS's "portable" zip,
  no install step needed).

All four tools are fetched on demand to `packaging/tools/` (gitignored,
never committed, never installed system-wide) — run `./setup.sh` from the
repo root and answer "y" to the "Set up packaging tools too?" prompt, or run
`packaging/lib/fetch-tools.sh`'s `fetch_nfpm`/`fetch_appimagetool`/
`fetch_linuxdeploy`/`fetch_makensis` functions directly. The `build-*.sh`
scripts will tell you to do this if a tool is missing, rather than
downloading it themselves mid-build.

## Usage

From the repo root, with `.venv` set up (`./setup.sh`):

```
./packaging/build-deb.sh        # -> dist/packages/set-ttrpg-portrait_<version>_amd64.deb
./packaging/build-rpm.sh        # -> dist/packages/set-ttrpg-portrait-<version>-1.x86_64.rpm
./packaging/build-appimage.sh   # -> dist/packages/set-ttrpg-portrait-<version>-x86_64.AppImage
./packaging/build-all.sh        # builds all three Linux artifacts above
./packaging/build-nsis.sh       # -> dist/packages/set-ttrpg-portrait-<version>-x64-setup.exe (Windows only)
./packaging/build-macos.sh      # -> dist/packages/set-ttrpg-portrait-<version>-arm64.dmg (macOS arm64 only)
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
`appimage/icon.png`, `windows/icon.ico`,
`macos/AppIcon.iconset/*.png`, `macos/AppIcon.icns`) is generated by
`icon/generate_icons.py` (plus `build-macos.sh`'s `.icns` conversion step)
and gitignored — this is the single source of truth; nothing derived from
it is ever hand-maintained or committed.

## Build natively per architecture

`pikepdf` ships platform-specific compiled wheels, so the AppImage's,
Windows installer's, and macOS .dmg's PyInstaller builds must each run
natively on their target OS/arch (Linux x86_64, Windows x64, and macOS
arm64 respectively — see `.github/workflows/
release.yml`'s separate `ubuntu-latest`/`windows-latest`/`macos-latest`
jobs). The `.deb`/`.rpm` themselves are pure Python (no compiled wheel of
our own to bundle), so this constraint doesn't apply to them directly —
but they still declare `arch: amd64` in `packaging/nfpm.yaml` to match the
other artifacts, since the system packages they depend on are
architecture-specific anyway. macOS support is Apple Silicon (arm64) only
— no Intel build is produced.

