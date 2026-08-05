# TTRPG Character Sheet Form Portrait Setter

Embed a portrait image (JPG/PNG/etc.) into a fillable TTRPG character sheet
PDF's portrait/photo field — auto-detecting the right field, or letting you
pick one explicitly.

## To Run

### Option 1: Pre-Built Release

Download the appropriate package from a [release](../../releases) and
install it:

```sh
# Debian/Ubuntu (installs python3-pyqt6/python3-pikepdf/python3-pil/python3-pymupdf automatically)
sudo apt install ./set-ttrpg-portrait_<version>_amd64.deb

# Fedora/RHEL (installs python3-pyqt6/python3-pikepdf/python3-pillow/python3-PyMuPDF automatically)
sudo dnf install ./set-ttrpg-portrait-<version>-1.x86_64.rpm

# AppImage (any distro, no Python/system packages needed — fully self-contained)
chmod +x set-ttrpg-portrait-<version>-x86_64.AppImage
```

The `.deb`/`.rpm` are plain Python, relying on your distro's own Python +
PyQt6/pikepdf/Pillow/PyMuPDF packages (pulled in automatically by
`apt`/`dnf`) rather than bundling their own copies — see
`packaging/README.md` for why. They install two separate commands — the
CLI (`set-ttrpg-portrait`) and the GUI (`set-ttrpg-portrait-gui`, also
added to your desktop's application menu). The AppImage instead bundles
everything (interpreter, Qt, all dependencies) into one self-contained
executable that needs nothing pre-installed: double-click it (or run it
with no arguments) for the GUI, or pass it CLI arguments from a terminal:
```
./set-ttrpg-portrait-<version>-x86_64.AppImage --help
./set-ttrpg-portrait-<version>-x86_64.AppImage SHEET.pdf PORTRAIT.jpg -o OUTPUT.pdf
```

### Option 2: Source (Python 3)

You can read the script if you want to do your own thing, or just run it:

```sh
# no args -> launches the GUI
./run.sh

# any args -> behaves like the CLI
./run.sh SHEET.pdf PORTRAIT.jpg -o OUTPUT.pdf
```

## GUI

Launch it with `set-ttrpg-portrait-gui` (packaged install), `./run.sh`
(from source), or `python set_ttrpg_portrait_gui.py` (from an activated
`.venv`).

- Pick a **Sheet (PDF)** and a **Portrait (image)** via the Browse…
  buttons, or just drag and drop files onto their fields — you can also
  drop a file straight onto the preview area, which sorts it by type
  (a `.pdf` becomes the sheet, an image becomes the portrait).
  
- Once both are set, the portrait is embedded automatically and previewed
  inline — no separate "Process" button, and it re-runs automatically
  whenever either input changes.
  
- If the sheet has more than one image field, a picker lets you choose
  which one to use; **Change Field…** reopens that same picker afterwards
  to try a different candidate without reselecting either file.
  
- **Save As…** writes the previewed result to a permanent location (the
  preview itself is a throwaway temp copy, cleaned up on exit).

  
## CLI usage

```sh
source .venv/bin/activate
python set_ttrpg_portrait.py SHEET.pdf PORTRAIT.jpg -o OUTPUT.pdf
```

- `SHEET.pdf` — the fillable PDF character sheet.
- `PORTRAIT.jpg` — the portrait image (JPG/PNG/etc.; transparent PNGs are
  automatically flattened onto a white background).
- `-o OUTPUT.pdf` — where to write the result (required unless
  `--list-fields` is used).

  
### Flags

- `--field NAME` — use a specific pushbutton field by exact name, overriding
  auto-detection (useful if a sheet has more than one image field, e.g. a
  portrait plus a faction/class icon).
- `--page N` — limit field auto-detection to a single 0-based page index.
- `--fit {cover,contain}` — how the portrait is scaled into the field's
  rectangle (default `cover`, which crops to fill; `contain` letterboxes
  onto white instead of cropping).
- `--dpi DPI` — resolution (dots per inch) to embed the portrait at,
  oversampling the field's on-page size so the icon stays sharp when
  zoomed in or printed, not just on-screen at 72 DPI (default: `300`).
- `--list-fields` — print every candidate pushbutton field found on the
  sheet (name, page, size) and exit, without writing an output file. Useful
  for finding the right `--field` value.
- `--version` — print the tool's version and exit.


### Example

```sh
source .venv/bin/activate
python set_ttrpg_portrait.py my_character_sheet.pdf my_photo.jpg -o my_character.pdf
```

If the sheet has multiple image fields and auto-detection picks the wrong
one:

```sh
source .venv/bin/activate
python set_ttrpg_portrait.py my_character_sheet.pdf --list-fields
python set_ttrpg_portrait.py my_character_sheet.pdf my_photo.jpg --field "Portrait" -o my_character.pdf
```

## For devs

1. `./setup.sh` — creates `.venv` and installs this project editable with
   its `dev` extra (`pip install -e ".[dev]"`, from `pyproject.toml`). It
   will also optionally offer to fetch `nfpm`/`appimagetool`/`linuxdeploy`
   (standalone binaries, cached in `packaging/tools/`, never installed
   system-wide) if you plan to build `.deb`/`.rpm`/AppImage packages — only
   needed for release builds, not everyday development.
   
2. `./format.sh` — formats Python with `ruff format` (line length 120). Use
   `./format.sh --check` (what CI runs) to verify formatting without
   modifying files.

3. `./lint.sh` — lints Python with `ruff check`. Use `./lint.sh --fix` to
   auto-apply safe fixes.

4. `./package-updates.sh` — checks pinned dependency versions for updates:
   the pip packages in `pyproject.toml` (also covered automatically, on a
   monthly cadence, by Dependabot — see `.github/dependabot.yml`) plus the
   `nfpm`/`appimagetool`/`linuxdeploy` build tools in
   `packaging/lib/fetch-tools.sh`, which Dependabot can't see since they're
   plain bash variables, not a manifest file. Add `--update` to rewrite
   outdated pins in place.

5. Run the test suite: `.venv/bin/python -m pytest tests/`.

6. Regenerate synthetic test fixtures after changing `tests/fixtures/`
   generation logic: `.venv/bin/python tests/fixtures/generate_fixtures.py`.
   
7. All automated tests use the synthetic, IP-free fixtures under
   `tests/fixtures/` — never commit or reference any real, copyrighted
   third-party character sheet PDFs anywhere in this repo or CI.

   
### VS Code

We're set up with tasks (Setup, Format, Test, Regenerate fixtures, Build packages), 
launch configs (Run CLI/GUI, debug tests), 
and settings pointing at `.venv` — open the Run/Debug and Tasks panels to use them; 
installing the recommended extensions (prompted automatically) enables format-on-save and the Testing panel.

See [`packaging/README.md`](packaging/README.md) for packaging-script details.
