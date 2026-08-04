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
**pushbutton form fields** whose "icon" is normally set via Acrobat's
"Select Icon" UI — there is no plain image/XObject field type in AcroForms.

**Confirmed by inspecting the user's own real, human-produced example
outputs in `examples/outputs/`**: those PDFs keep the portrait field as a
live `FieldType: Button` (per `pdftk`) after the image is set — i.e. the
field stays clickable/replaceable later in Acrobat, it is *not* flattened
into the page and discarded. The exact object structure Acrobat uses:
- `/MK/I` on the widget → a Form XObject ("FRM") that draws the raw image
  (`/Im0`, `/Filter /DCTDecode`, i.e. plain embedded JPEG bytes) at its
  native pixel size.
- `/AP/N` on the widget → a second Form XObject that clips to the widget's
  `/Rect` size and scales the icon (`FRM`) to fit via a `cm` matrix.
- Some fields are "merged" (the field dict *is* the one widget annotation,
  with its own `/Rect`); others use `/Kids` (a list of separate widget
  annotation dicts — e.g. the D&D sheet's `CHARACTER IMAGE` field has 3
  identical-`/Rect` kids). Both shapes must be supported.

This ruled out the initial plan (flatten the portrait into page content via
`PyMuPDF`/`fitz` and delete the widget) — that produced a *visually*
correct but *structurally* wrong result (no more `Button` field, unlike the
user's real examples) and hit a `fitz` gotcha along the way: a `Widget`
object holds only a weak reference to its parent `Page`; letting that
`Page` wrapper fall out of scope invalidates the widget with a
`ReferenceError`/`FzErrorArgument` deep inside `page.delete_widget()`.

**`PyMuPDF` has no ergonomic API for setting a button's icon appearance
stream**, and hand-building the required PDF object graph via `fitz`'s
low-level `xref_object`/`update_object` (raw PDF syntax as Python strings)
is fragile and error-prone. **`pikepdf`** (built on `qpdf`) exposes the
same low-level object graph through proper Pythonic `Dictionary`/
`Array`/`Stream` objects instead of hand-written PDF syntax strings, and a
prototype (see below) reproduced Acrobat's exact `/MK`/`/AP` structure
cleanly. `pikepdf` is therefore the actual PDF-editing library for this
tool; `pypdf` was considered too (no ergonomic button-icon API either).

Verified in a scratch venv: `pikepdf==10.11.0` and `pillow==12.3.0` install
and import cleanly, and a hand-built `/MK/I` + `/AP/N` icon (JPEG bytes as
a `DCTDecode` Image XObject wrapped in two Form XObjects) rendered
correctly with `pdftoppm` and still reported as `FieldType: Button` via
`pdftk` afterwards — matching the real reference outputs exactly.

`PyMuPDF` (`fitz==1.28.0`) remains useful as a **dev-only** dependency for
quickly authoring the synthetic test-fixture PDFs (`page.add_widget(...)`
is a convenient way to build a fillable PDF from scratch) — see
`requirements-dev.txt`. It is not used by the shipped tool at runtime.

## Tooling decisions
- **Language:** Python 3.
- **Env:** project-local `.venv` + `requirements.txt` (already created:
  `pikepdf`, `pillow`). Do **not** install into global site-packages.
  `setup.sh` creates `.venv` and installs `requirements.txt` into it. Tested
  to run cleanly from a clean checkout. **Linux/macOS only** — Windows users
  should use Adobe Acrobat's own tools to set portrait/image button icons
  instead of this script.
- **PDF library:** `pikepdf` — reads/writes the AcroForm field tree
  (including `/Kids`), and builds the `/MK/I` + `/AP/N` icon object graph
  described above, keeping every field (including the portrait field
  itself) live and fillable in the output. `PyMuPDF` is a dev-only
  dependency, used only to author test fixtures (see Testing plan).
- **Image library:** `Pillow` — EXIF-orientation fix, format normalization
  (any input → JPEG bytes embeddable as a `DCTDecode` Image XObject),
  aspect-fit/cover cropping, and **compositing transparent images onto an
  opaque white background** (JPEG/DCTDecode has no alpha channel, and a
  naive `.convert("RGB")` on an RGBA image does *not* properly blend
  toward white — it can leave garbage-colored pixels showing through fully
  or partially transparent regions). See Testing plan for the dedicated
  transparent-PNG fixture/test covering this.
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
  fields.py                     # AcroForm field discovery/heuristic-matching logic
  image_prep.py                 # Pillow-based EXIF/resize/fit/flatten-alpha logic
  pdf_ops.py                     # pikepdf calls: open, build icon XObjects, save
  errors.py                     # small custom exception types (NoFieldFound, AmbiguousField, ...)
update_portrait.py               # thin repo-root shim: `from update_portrait.cli import main; main()`
                                  # kept only so `python update_portrait.py ...` (per the
                                  # examples above) keeps working for casual use
```

### Guidelines to keep this maintainable long-term
- **Single responsibility per module**: `cli.py` never touches `pikepdf`/
  `Pillow` directly — it parses args and calls into
  `fields`/`image_prep`/`pdf_ops`. This keeps each file short and testable
  without a full CLI invocation.
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
1. **Load** the PDF with `pikepdf.open(sheet_path)`.
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
   - Open portrait JPG/PNG/etc., apply `ImageOps.exif_transpose`.
   - If the source has an alpha channel, **composite it onto an opaque
     white background** (`Image.alpha_composite`/`Image.paste(img, mask=...)`
     against a solid white canvas) — do *not* use a naive `.convert("RGB")`,
     which drops alpha without blending and can leave garbage-colored
     pixels showing through transparent/semi-transparent regions.
   - Compute the target aspect ratio from the widget's `rect` (not its
     literal point dimensions — see below).
   - Crop/pad per `--fit` mode (`cover` = crop to fill the rect's aspect,
     `contain` = letterbox within it) to match that aspect ratio, at a
     reasonably high resolution — real Acrobat-authored sheets embed the
     icon far larger (e.g. 816×816px) than the widget's point-sized
     display rect and let the PDF's appearance-stream `cm` matrix scale it
     down, rather than downsampling to the rect's literal point dimensions.
   - Encode to JPEG bytes (with a fixed quality constant) for embedding as
     a `DCTDecode` Image XObject.
4. **Build and set the icon** (`pdf_ops.set_field_icon`):
   - Build one Image XObject (raw JPEG bytes) + one Form XObject ("FRM",
     draws the image at native pixel size) — these become the field's
     `/MK/I` icon, shared across every widget annotation for the field.
   - For each widget annotation belonging to the field (one for a "merged"
     field, or one per `/Kids` entry), build a per-widget `/AP/N` Form
     XObject that clips to that widget's own `/Rect` and scales the icon
     to fit it, then set `/MK` and `/AP` on that annotation.
   - The field **stays a live, clickable Button field** afterwards — this
     matches Acrobat's own behavior and the user's real reference outputs
     in `examples/outputs/`, and means the portrait remains replaceable
     later (in Acrobat, or by re-running this tool) rather than being
     baked permanently into the page content.
5. **Preserve every other field:** only the target field's widget
   annotation(s) are touched; every other AcroForm field/value is left
   completely untouched by `pikepdf`.
6. **Save** via `pdf.save(output_path)`.
7. **Exit codes / errors:** clear, actionable stderr messages for: file not
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
- **`tests/fixtures/portrait_transparent.png`**: same idea, but with a real
  alpha channel (partially and/or fully transparent regions), to exercise
  transparency handling specifically. Since the embedded icon image is
  encoded as JPEG/DCTDecode (no alpha support), `image_prep.py` must
  properly **composite transparent input images onto an opaque white
  background** (not just drop the alpha channel, which can leave
  garbage-colored pixels showing through from naive `.convert("RGB")`).
  Add a unit test asserting a known transparent pixel becomes white
  (255, 255, 255) in the output, not black/garbage, and that a
  partially-transparent pixel blends correctly toward white.
- **`tests/test_update_portrait.py`** (pytest): drives `update_portrait.py`
  against the generated fixtures — covers auto-detect success, `--field`
  override, `--list-fields`, no-candidate error, ambiguous error, `--fit`
  modes, PNG-input normalization, transparent-PNG-input flattening to white,
  and confirms non-image fields survive untouched (re-open output with
  `pikepdf`/`pdftk` and diff field names/values).
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
     an icon) into `update-portrait-x86_64.AppImage`.
   - Script: `packaging/build-appimage.sh`.
6. **Icon: one source image, generate every size/format needed**:
   - Keep a **single master icon source**, `packaging/icon/icon-source.png`
     (large, e.g. 512×512, ideally the highest resolution the human artist
     provides) — this is the *only* file a human ever hand-edits/draws.
   - Since real app icon artwork is human-only (see
     `.github/copilot-instructions.md`), commit a simple **placeholder** for
     `icon-source.png` showing safe-zone guides (e.g. a bordered square, a
     centered circle marking the "rounded icon" crop-safe area, crosshairs,
     and a "REPLACE WITH ARTWORK" label) — generated by a small script
     (`packaging/icon/generate_placeholder_icon.py`, Pillow shapes only,
     same spirit as the test-fixture generator) so it's obvious which file
     to draw the real icon in and what area is safe from cropping/masking,
     without the AI creating or editing final artwork itself. Replace this
     placeholder with real artwork before a public release.
   - A conversion script, `packaging/icon/generate_icons.py`, derives every
     size/format the packagers need from that one source (via Pillow
     resize, no hand-maintained duplicates to drift out of sync):
     - `packaging/appimage/icon.png` (256×256, for the AppImage/`.desktop`).
     - `packaging/icons/hicolor/{16,32,48,64,128,256}x*/apps/update-portrait.png`
       (freedesktop hicolor icon theme sizes, installed by the `.deb`/`.rpm`
       so the icon shows up correctly in Linux app menus/file managers at
       every size they request).
   - `build-deb.sh`/`build-rpm.sh`/`build-appimage.sh` all run
     `generate_icons.py` (or depend on its already-generated output) rather
     than referencing hand-maintained per-size icon files directly.
7. **Orchestration**: `packaging/build-all.sh` runs PyInstaller once, then all
   three packagers, writing artifacts to `dist/packages/`.
8. **CI validation** (follow-up, not required for first pass): smoke-test
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
  icon/
    icon-source.png            # THE single source icon; placeholder w/ safe-zone
                                # guides until a human replaces it with real art
    generate_placeholder_icon.py  # (re)generates the placeholder guide image
    generate_icons.py          # derives every size/format below from icon-source.png
  icons/hicolor/16x16/apps/update-portrait.png   # generated, not committed
  icons/hicolor/32x32/apps/update-portrait.png   # generated, not committed
  icons/hicolor/48x48/apps/update-portrait.png   # generated, not committed
  icons/hicolor/64x64/apps/update-portrait.png   # generated, not committed
  icons/hicolor/128x128/apps/update-portrait.png # generated, not committed
  icons/hicolor/256x256/apps/update-portrait.png # generated, not committed
  appimage/
    update-portrait.desktop
    icon.png                  # generated, not committed (see generate_icons.py)
```

### Notes / risks
- `fpm` requires Ruby; document this build-time dependency in
  `packaging/README.md` (not needed by end users, only by whoever builds
  releases).
- Only `packaging/icon/icon-source.png` is committed; every derived
  size/format under `packaging/icons/` and `packaging/appimage/icon.png` is
  build output from `generate_icons.py` and should be `.gitignore`d, same as
  `dist/`, so there's never more than one file to keep in sync by hand.
- `pikepdf` ships platform-specific wheels with compiled extensions (it
  bundles `qpdf`) — PyInstaller must be run natively on each target OS/arch;
  CI matrix should build on `ubuntu-latest` for all three Linux artifacts.
- This project targets Linux only (`.deb`/`.rpm`/AppImage packaging, plus
  `setup.sh`/`format.sh`). Windows users should use Adobe Acrobat's own
  tooling to set a portrait/image button icon instead — no Windows build is
  planned.

## Out of scope / follow-ups
- No GUI; CLI only for now.
- Batch mode (many sheets/portraits at once) could be a future enhancement.

## Documentation

Once the implementation above is working end-to-end, update `README.md`
(final step, after everything else in this plan is done) to cover:
- **For users**: what the tool does, install options (`.venv`+`setup.sh`,
  or the `.deb`/`.rpm`/AppImage once packaging exists), CLI usage/examples
  (mirroring the "Example usage against sample data" section above),
  `--field`/`--fit`/`--list-fields` flags, and a note that the portrait
  field stays a live, replaceable Button field afterwards (not baked in
  permanently).
- **For human devs**: `.venv` setup, running `./format.sh`/`./format.sh
  --check`, running the test suite (`pytest`), regenerating fixtures
  (`tests/fixtures/generate_fixtures.py`), the `examples/` IP-sensitivity
  rule (never commit/run real sheets in CI), and a pointer to
  `.github/copilot-instructions.md` for the full contributor conventions
  (including the human-only project artwork rule and AI git-operation
  limits) so this isn't duplicated in two places.
