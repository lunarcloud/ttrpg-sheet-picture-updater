# Plan: TTRPG Sheet Portrait Updater

## Goal
A Python script that takes a JPG **portrait** and a fillable **PDF sheet**, finds
the portrait/image placeholder on the sheet, and produces a new PDF with the
portrait embedded in place — without disturbing any other (still-fillable)
form fields.

## Research findings (from `examples/`)

Inspected the four sample sheets with `pdftk ... dump_data_fields`:

| Sheet | Image field name | Field type |
|---|---|---|
| `DnD_5E_CharacterSheet - Form Fillable.pdf` | `CHARACTER IMAGE` (also `Faction Symbol Image`) | Button (pushbutton, `FieldFlags: 65536`) |
| `ENG Brancalonia Editable Character Sheet 2.2.pdf` | `Image` | Button |
| `STA 2e Character sheet Federation digital form v1.1.pdf` | `Photo_af_image` | Button |
| `ION_HEART_Character_Sheet_Digital.pdf` | *(none found)* | n/a — no image field, out of scope for auto-detect |

Key insight: portrait placeholders in these Acrobat-authored sheets are
**pushbutton form fields** whose "icon" is normally set via Acrobc's
"Select Icon" UI — there is no plain image/XObject field type in AcroForms.
`pypdf` has no ergonomic API for setting a button icon appearance stream.
`PyMuPDF` (`fitz`) can read widget rects/names easily, and — pragmatically —
we can simply draw the portrait image directly onto the page at the widget's
rectangle and then remove/flatten that one widget, so the image is baked in
permanently while every other form field remains fillable. This avoids
hand-building PDF appearance streams and is robust across the varied sheets.

Verified in a scratch venv: `pymupdf==1.28.0`, `pypdf==6.14.2`, `pillow==12.3.0`
all install and import cleanly.

## Tooling decisions
- **Language:** Python 3.
- **Env:** project-local `.venv` + `requirements.txt` (already created:
  `pymupdf`, `pillow`). Do **not** install into global site-packages.
  `setup.sh` creates `.venv` and installs `requirements.txt` into it. Tested
  to run cleanly from a clean checkout. **Linux/macOS only** — Windows users
  should use Adobe Acrobat's own tools to set portrait/image button icons
  instead of this script.
- **PDF library:** `PyMuPDF` (`fitz`) — widget introspection + image
  insertion + page rendering, all in one dependency.
- **Image library:** `Pillow` — EXIF-orientation fix, format normalization
  (any input → JPEG/PNG bytes fitz can embed), aspect-fit/cover cropping.
- **CLI:** stdlib `argparse`, no extra framework needed.
- **Formatting:** `black` + `isort`, pinned in `requirements-dev.txt`
  (`black==26.5.1`, `isort==8.0.1`). Run via `./format.sh` to auto-fix;
  `./format.sh --check` runs in check-only mode (non-zero exit on
  unformatted code) for use in CI. Skips cleanly (exit 0) if there's no
  Python code yet to format. Formats `update_portrait.py`,
  `update_portrait/`, `tests/`, and `packaging/`.

## Code organization & maintainability

Rather than one large flat script, the tool is a small, well-factored
package so each concern is easy to find, read, and change in isolation:

```
update_portrait/                # importable package, not a junk-drawer script
  __init__.py                   # re-exports the public API + __version__
  __main__.py                   # `python -m update_portrait ...`
  cli.py                        # argparse setup + main(); thin, no business logic
  fields.py                     # widget discovery/heuristic-matching logic
  image_prep.py                 # Pillow-based EXIF/resize/fit logic
  pdf_ops.py                     # fitz calls: open, insert_image, delete_widget, save
  errors.py                     # small custom exception types (NoFieldFound, AmbiguousField, ...)
update_portrait.py               # thin repo-root shim: `from update_portrait.cli import main; main()`
                                  # kept only so `python update_portrait.py ...` (per the
                                  # examples above) keeps working for casual use
```

### Guidelines to keep this maintainable long-term
- **Single responsibility per module**: `cli.py` never touches `fitz`/`Pillow`
  directly — it parses args and calls into `fields`/`image_prep`/`pdf_ops`.
  This keeps each file short and testable without a full CLI invocation.
- **Type hints everywhere** (function signatures, return types) — makes
  intent obvious at a glance and lets editors/IDEs help future contributors.
- **Docstrings**: one-line module docstring at the top of every file, plus a
  short docstring on every public function explaining *why*, not just *what*
  (the *what* should be clear from the code itself).
- **Small, pure functions where possible**: e.g. the field-matching heuristic
  and the image-fit math should be pure functions (inputs → outputs, no I/O)
  so they're trivial to unit test without building real PDFs/images for
  every case.
- **Custom exceptions over bare strings**: `errors.py` defines
  `NoCandidateFieldError`, `AmbiguousFieldError`, etc.; `cli.py` catches
  these once and turns them into clear stderr messages + exit codes, instead
  of scattering `sys.exit()`/string-matching through the logic layer.
- **Named constants, not magic values**: the field-name heuristic regex/list,
  default fit mode, JPEG quality, etc. live as module-level constants with
  descriptive names near the top of `fields.py`/`image_prep.py`.
- **Consistent style enforced automatically**: `black` (formatting) + `isort`
  (import order) via `./format.sh`, so reviewers/contributors never bikeshed
  style — see Tooling decisions above.
- **Tests mirror the module layout** (`tests/test_fields.py`,
  `tests/test_image_prep.py`, `tests/test_cli.py`) so it's obvious where to
  add a test for a given change, in addition to the fixture-driven
  end-to-end test described below.
- Keep the whole package small — this is a focused single-purpose tool, not
  a framework; resist adding abstraction/config layers beyond what's
  described here unless a real need appears.

## Script design

Entry points: `update_portrait/cli.py:main()`, invoked via
`.venv/bin/python update_portrait.py ...` or
`.venv/bin/python -m update_portrait ...`.

### CLI
```
update_portrait.py SHEET.pdf PORTRAIT.jpg -o OUTPUT.pdf
                    [--field NAME]        # explicit field name override
                    [--page N]            # limit search to one page (0-based)
                    [--fit {cover,contain}]  # default: cover
                    [--list-fields]       # print candidate fields and exit
```

### Steps
1. **Load** the PDF with `fitz.open(sheet_path)`.
2. **Locate the portrait field:**
   - If `--field` given, find the widget with that exact `field_name` (search
     all pages).
   - Else, enumerate all `Button`-type widgets across all pages and score by
     name heuristics (case-insensitive match against
     `portrait|character image|photo|headshot|^image$|player image`).
   - If exactly one candidate: use it.
   - If zero or multiple candidates and no `--field`: print the full list of
     button field names (name, page, rect) and exit non-zero with guidance to
     rerun with `--field`.
3. **Prepare the image** with Pillow:
   - Open portrait JPG, apply `ImageOps.exif_transpose`.
   - Compute target rect size/aspect from the widget's `rect`.
   - Resize/crop per `--fit` mode (`cover` = crop to fill rect, `contain` =
     letterbox within rect) so proportions look correct on the sheet.
   - Save to an in-memory buffer as JPEG for embedding.
4. **Embed the image:**
   - `page.insert_image(widget.rect, stream=buffer, keep_proportion=False)`
     (aspect already handled in step 3) on the widget's page.
5. **Neutralize the placeholder widget** so it doesn't float a clickable/empty
   button on top of the new image: delete the annotation
   (`page.delete_widget(widget)` / `page.delete_annot`) after inserting the
   image, or clear its border/background — deletion is preferred so no ghost
   button remains.
6. **Preserve every other field:** do not touch any other widget; PyMuPDF's
   incremental save keeps the rest of the AcroForm intact and fillable.
7. **Save** via `doc.save(output_path, garbage=4, deflate=True)`.
8. **Exit codes / errors:** clear, actionable stderr messages for: file not
   found, encrypted PDF, no candidate field found, ambiguous field found.

### Example usage against sample data
```
.venv/bin/python update_portrait.py \
  "examples/DnD_5E_CharacterSheet - Form Fillable.pdf" \
  examples/inputs/some-portrait.jpg \
  -o examples/outputs/test-output.pdf
```

## Testing plan

### Manual/local smoke testing (against real-world samples)
- The sheets in `examples/` are third-party TTRPG publishers' PDFs (D&D 5E,
  Brancalonia, STA, ION HEART) — they're gitignored and **must never be
  committed or used in CI**, they're for local, manual sanity-checking only.
- Manual smoke test locally against all bundled sample PDFs using a sample
  JPG (add one to `examples/inputs/` if not present) — confirm the script
  picks the right field automatically for the 3 sheets that have one, and
  reports "no candidate" cleanly for `ION_HEART...`.
- Test `--field` override and `--list-fields` on an ambiguous/no-match case.
- Test with a non-JPEG portrait (e.g., PNG) to confirm Pillow normalization
  works even though the CLI is primarily documented for `.jpg`.

### Automated tests (CI-safe, our own IP-free fixtures)
Since the real sample sheets can't be committed or run in GitHub Actions
(third-party copyright), we need small, **originally-authored, synthetic**
fixtures checked into the repo so `pytest` and CI never depend on
`examples/`.

- **`tests/fixtures/generate_fixtures.py`**: a script (run once, output
  committed) that programmatically builds our own minimal fillable PDFs with
  `PyMuPDF`, mirroring the real-world shapes we need to handle:
  - `simple_sheet.pdf` — one text field (`Character Name`) + one pushbutton
    field named `Portrait` (mimics the `CHARACTER IMAGE`/`Image`/
    `Photo_af_image` pattern), single page.
  - `multi_field_sheet.pdf` — several text fields + a pushbutton field with a
    less obvious name (e.g. `Pic1`) to exercise the heuristic-matching /
    `--field` override path.
  - `no_image_sheet.pdf` — text fields only, no button field, to exercise the
    "no candidate found" error path (mirrors `ION_HEART...`).
  - `ambiguous_sheet.pdf` — two pushbutton fields whose names both match the
    heuristic, to exercise the "ambiguous, multiple candidates" error path.
  - All content is placeholder text/rectangles we author ourselves — no
    copied layouts, art, or text from the real publishers' sheets.
- **`tests/fixtures/portrait.jpg`** (and a `.png` variant): a small
  programmatically-generated image (e.g., Pillow-drawn gradient/shapes),
  not a real photo — fully original, safe to commit and redistribute.
- **`tests/test_update_portrait.py`** (pytest): drives `update_portrait.py`
  against the generated fixtures — covers auto-detect success, `--field`
  override, `--list-fields`, no-candidate error, ambiguous error, `--fit`
  modes, PNG-input normalization, and confirms non-image fields survive
  untouched (re-open output with `fitz`/`pdftk` and diff field names/values).
- Fixtures are static, checked into git (deterministic, no need to
  regenerate on every run); `generate_fixtures.py` is kept only so they can
  be regenerated/extended later.

### GitHub Actions CI
- New workflow: `.github/workflows/test.yml` — on push/PR:
  - Set up Python, `pip install -r requirements.txt -r requirements-dev.txt`
    (adds `pytest`, `black`, `isort`).
  - Run `./format.sh --check` to fail the build on unformatted code.
  - Run `pytest tests/`.
  - Runs on `ubuntu-latest`; no dependency on `examples/` or any
    third-party file at all, so the workflow is fully self-contained and
    safe to run on forks/public CI.

### Dependency updates
- `.github/dependabot.yml` (already added): monthly-cadence updates for the
  `pip` ecosystem (`requirements.txt`/`requirements-dev.txt`) and the
  `github-actions` ecosystem (workflow action versions), each capped at 5
  open PRs at a time. Monthly (not weekly/daily) keeps update-PR noise low
  for a small single-maintainer-style tool.

## Distribution / Packaging (.deb, .rpm, AppImage)

Goal: let end users on Ubuntu/Debian and Fedora/RHEL install the tool as a
native package, and give everyone else a portable single-file AppImage — all
without needing to manually create a venv or have Python preinstalled.

### Approach
1. **Freeze to a standalone executable with PyInstaller** (new dev
   dependency, `pyinstaller`, added to a separate `requirements-dev.txt` —
   not needed by end users). PyInstaller bundles the interpreter plus
   `pymupdf`/`pillow` native extensions into one binary
   (`dist/update-portrait`), so downstream packages don't need a Python
   runtime or pip at all.
   - Build with a checked-in `.spec` file (`packaging/update-portrait.spec`)
     for reproducible, one-file builds: `pyinstaller packaging/update-portrait.spec`.
2. **Single source of truth for version**: a `VERSION` file at repo root,
   read by `update_portrait.py` (`--version` flag) and by every packaging
   script below, so `.deb`/`.rpm`/AppImage version numbers never drift from
   the script.
3. **`.deb` package** (Ubuntu/Debian):
   - Use [`fpm`](https://github.com/jordansissel/fpm) to build the `.deb`
     directly from the PyInstaller binary — avoids hand-maintaining
     `debian/` control files.
   - Script: `packaging/build-deb.sh` — installs the binary to
     `/usr/bin/update-portrait`, includes `LICENSE`/`README.md` as docs, sets
     package metadata (name, version from `VERSION`, maintainer, description,
     depends: none, since PyInstaller bundles everything).
4. **`.rpm` package** (Fedora/RHEL):
   - Same `fpm` invocation, targeting `-t rpm`, in
     `packaging/build-rpm.sh`, sharing the same staged file layout as the
     `.deb` script (factor common staging logic into
     `packaging/lib/stage-files.sh` to avoid duplication).
5. **AppImage**:
   - Use `appimagetool` (or `linuxdeploy` if we later add a `.desktop`
     GUI-style entry) to wrap the PyInstaller one-file binary plus an
     `AppRun` entrypoint and minimal `AppDir/` (`update-portrait.desktop`,
     a placeholder icon) into `update-portrait-x86_64.AppImage`.
   - Script: `packaging/build-appimage.sh`.
6. **Orchestration**: `packaging/build-all.sh` runs PyInstaller once, then all
   three packagers, writing artifacts to `dist/packages/`.
7. **CI validation** (follow-up, not required for first pass): smoke-test
   install of the `.deb` in an `ubuntu:latest` container and the `.rpm` in a
   `fedora:latest` container (`dpkg -i` / `rpm -Uvh` + run `update-portrait
   --help`), and that the AppImage is executable and runs on a generic Linux
   container.

### New repo layout additions
```
VERSION
requirements-dev.txt          # pyinstaller (build-time only)
packaging/
  update-portrait.spec        # PyInstaller spec
  build-deb.sh
  build-rpm.sh
  build-appimage.sh
  build-all.sh
  lib/stage-files.sh           # shared staging helper for fpm-based builds
  appimage/
    update-portrait.desktop
    icon.png
```

### Notes / risks
- `fpm` requires Ruby; document this build-time dependency in
  `packaging/README.md` (not needed by end users, only by whoever builds
  releases).
- PyMuPDF ships platform-specific wheels with compiled extensions —
  PyInstaller must be run natively on each target OS/arch; CI matrix should
  build on `ubuntu-latest` for all three Linux artifacts.
- This project targets Linux only (`.deb`/`.rpm`/AppImage packaging, plus
  `setup.sh`/`format.sh`). Windows users should use Adobe Acrobat's own
  tooling to set a portrait/image button icon instead — no Windows build is
  planned.

## Out of scope / follow-ups
- No GUI; CLI only for now.
- No support for re-inserting an image as an *interactive* button icon
  (would require hand-built `/AP` appearance streams) — baking the image into
  the page content is sufficient for the stated use case.
- Batch mode (many sheets/portraits at once) could be a future enhancement.
