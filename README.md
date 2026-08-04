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
./set-ttrpg-portrait-<version>-x86_64.AppImage --help
```

### Option 2: Run from source (Python 3)

```
git clone <this repo>
cd ttrpg-sheet-picture-updater
./setup.sh                 # creates .venv, pip installs this project (pyproject.toml)
source .venv/bin/activate
python set_ttrpg_portrait.py --help
```

## Usage

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

See [`packaging/README.md`](packaging/README.md) for packaging-script details.
