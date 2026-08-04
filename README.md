# TTRPG Character Sheet Form Portrait Setter

Embed a portrait image (JPG/PNG/etc.) into a fillable TTRPG character sheet
PDF's portrait/photo field — auto-detecting the right field, or letting you
pick one explicitly.

The portrait field is left as a live, replaceable `Button` field afterwards
(the same as clicking "Select Icon" in Acrobat), so the portrait can be
swapped again later in Acrobat or by re-running this tool — it's never
flattened/baked into the page permanently.

## Install

### Option 1: `.deb` / `.rpm` / AppImage (no Python needed)

Download the appropriate package from a [release](../../releases) and
install it:
```
sudo apt install ./set-ttrpg-portrait_<version>_amd64.deb   # Debian/Ubuntu
sudo rpm -i set-ttrpg-portrait-<version>-1.x86_64.rpm       # Fedora/RHEL
chmod +x set-ttrpg-portrait-<version>-x86_64.AppImage       # AppImage (any distro)
```
The `.deb`/`.rpm` install two separate commands — the CLI
(`set-ttrpg-portrait`) and the GUI (`set-ttrpg-portrait-gui`, also added to
your desktop's application menu). The AppImage bundles both in one
executable: double-click it (or run it with no arguments) for the GUI, or
pass it CLI arguments from a terminal:
```
./set-ttrpg-portrait-<version>-x86_64.AppImage --help
./set-ttrpg-portrait-<version>-x86_64.AppImage SHEET.pdf PORTRAIT.jpg -o OUTPUT.pdf
```

### Option 2: Run from source (Python 3)

```
git clone <this repo>
cd ttrpg-sheet-picture-updater
./setup.sh                 # creates .venv, pip installs this project (pyproject.toml)
source .venv/bin/activate
python set_ttrpg_portrait.py --help
```

Alternatively, skip activating the venv yourself and use `./run.sh`, which
runs `./setup.sh` automatically the first time, then always uses the
project's own `.venv` Python:
```
./run.sh                                        # no args -> launches the GUI
./run.sh SHEET.pdf PORTRAIT.jpg -o OUTPUT.pdf    # any args -> behaves like the CLI
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

```
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

```
python set_ttrpg_portrait.py my_character_sheet.pdf my_photo.jpg -o my_character.pdf
```

If the sheet has multiple image fields and auto-detection picks the wrong
one:
```
python set_ttrpg_portrait.py my_character_sheet.pdf --list-fields
python set_ttrpg_portrait.py my_character_sheet.pdf my_photo.jpg --field "Portrait" -o my_character.pdf
```

## For devs

1. `./setup.sh` — creates `.venv` and installs this project editable with
   its `dev` extra (`pip install -e ".[dev]"`, from `pyproject.toml`). It
   will also optionally offer to fetch `nfpm`/`appimagetool` (standalone
   binaries, cached in `packaging/tools/`, never installed system-wide) if
   you plan to build `.deb`/`.rpm`/AppImage packages — only needed for
   release builds, not everyday development.
2. `./format.sh` — formats Python with `isort` + `black`. Use `./format.sh
   --check` (what CI runs) to verify formatting without modifying files.
3. Run the test suite: `.venv/bin/python -m pytest tests/`.
4. Regenerate synthetic test fixtures after changing `tests/fixtures/`
   generation logic: `.venv/bin/python tests/fixtures/generate_fixtures.py`.
5. All automated tests use the synthetic, IP-free fixtures under
   `tests/fixtures/` — never commit or reference any real, copyrighted
   third-party character sheet PDFs anywhere in this repo or CI.
6. Using VS Code? `.vscode/` has ready-made tasks (Setup, Format, Test,
   Regenerate fixtures, Build packages), launch configs (Run CLI/GUI,
   debug tests), and settings pointing at `.venv` — open the Run/Debug and
   Tasks panels to use them; installing the recommended extensions
   (prompted automatically) enables format-on-save and the Testing panel.
7. Using Qt Creator? Just editing `set_ttrpg_portrait/gui/main_window.ui`
   visually needs no setup — open it directly in Qt Creator's Designer
   (File > Open File). To open the whole repo as a Python project (project
   tree, code completion, run configs), open `set-ttrpg-portrait.pyproject`
   instead. That file lists tracked `.py`/`.ui` files explicitly (Qt
   Creator's project format doesn't reliably expand globs), so re-run
   `./update-qtcreator-project.sh` after adding/removing/renaming any of
   those files to keep it in sync. Requires a reasonably recent Qt Creator
   (5+) with the Python plugin enabled — check `Help > About Plugins`.

See [`packaging/README.md`](packaging/README.md) for packaging-script details.
