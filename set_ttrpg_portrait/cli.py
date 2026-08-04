"""Command-line interface for set_ttrpg_portrait.

Intentionally thin: parses arguments and delegates to `fields`,
`image_prep`, and `pdf_ops`. No `fitz`/`Pillow` business logic lives here so
those modules stay usable and testable independently of the CLI.
"""

from __future__ import annotations

import argparse
import sys

from set_ttrpg_portrait import __version__
from set_ttrpg_portrait.core import apply_portrait
from set_ttrpg_portrait.errors import SetTtrpgPortraitError
from set_ttrpg_portrait.fields import find_button_fields
from set_ttrpg_portrait.image_prep import DEFAULT_ICON_DPI
from set_ttrpg_portrait.pdf_ops import open_sheet


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser for the `set-ttrpg-portrait` CLI."""
    parser = argparse.ArgumentParser(
        prog="set_ttrpg_portrait.py",
        description=("Embed a portrait image into a fillable PDF character sheet's portrait/photo field."),
    )
    parser.add_argument("sheet", help="Path to the fillable PDF sheet.")
    parser.add_argument(
        "portrait",
        nargs="?",
        help="Path to the portrait image (JPG/PNG/etc).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output PDF path (required unless --list-fields is used).",
    )
    parser.add_argument(
        "--field",
        help="Exact name of the pushbutton field to use, overriding auto-detect.",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=None,
        help="Limit the field search to a single 0-based page index.",
    )
    parser.add_argument(
        "--fit",
        choices=("cover", "contain"),
        default="cover",
        help="How to fit the portrait into the field's rectangle (default: cover).",
    )
    parser.add_argument(
        "--dpi",
        type=float,
        default=DEFAULT_ICON_DPI,
        help=(
            "Resolution (dots per inch) to embed the portrait at, oversampling "
            "the field's on-page size in points so the icon stays sharp when "
            f"zoomed or printed, not just on-screen at 72 DPI (default: {DEFAULT_ICON_DPI:g})."
        ),
    )
    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="Print all pushbutton fields found on the sheet, then exit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _print_field_list(pdf, page_index: int | None) -> None:
    candidates = find_button_fields(pdf, page_index)
    if not candidates:
        print("No pushbutton fields found on this sheet.")
        return
    print("Pushbutton fields found:")
    for c in candidates:
        for loc in c.locations:
            print(f"  - {c.name!r} (page {loc.page_index}, rect {loc.rect})")


def main(argv: list[str] | None = None) -> int:
    """Entry point used by both `set_ttrpg_portrait.py` and `python -m set_ttrpg_portrait`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.dpi <= 0:
        parser.error("--dpi must be greater than 0")

    if args.list_fields:
        try:
            # Closed via the `with` block: this is the only place the CLI
            # opens the sheet itself — the embed path below instead lets
            # `apply_portrait()` open (and close) its own copy, so the
            # file is never parsed/held open twice.
            with open_sheet(args.sheet) as pdf:
                _print_field_list(pdf, args.page)
        except SetTtrpgPortraitError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    if not args.portrait or not args.output:
        parser.error("portrait and -o/--output are required unless --list-fields is used")

    try:
        apply_portrait(
            args.sheet,
            args.portrait,
            args.output,
            field=args.field,
            page=args.page,
            fit=args.fit,
            dpi=args.dpi,
        )
    except SetTtrpgPortraitError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}")
    return 0
