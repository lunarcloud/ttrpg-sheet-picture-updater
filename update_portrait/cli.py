"""Command-line interface for update_portrait.

Intentionally thin: parses arguments and delegates to `fields`,
`image_prep`, and `pdf_ops`. No `fitz`/`Pillow` business logic lives here so
those modules stay usable and testable independently of the CLI.
"""

from __future__ import annotations

import argparse
import sys

from update_portrait import __version__
from update_portrait.errors import UpdatePortraitError
from update_portrait.fields import find_button_fields, find_portrait_field
from update_portrait.image_prep import prepare_portrait_jpeg
from update_portrait.pdf_ops import open_sheet, save_sheet, set_field_icon


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser for the `update-portrait` CLI."""
    parser = argparse.ArgumentParser(
        prog="update_portrait.py",
        description=(
            "Embed a portrait image into a fillable PDF character sheet's "
            "portrait/photo field."
        ),
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
    """Entry point used by both `update_portrait.py` and `python -m update_portrait`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        pdf = open_sheet(args.sheet)
    except UpdatePortraitError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.list_fields:
        _print_field_list(pdf, args.page)
        return 0

    if not args.portrait or not args.output:
        parser.error(
            "portrait and -o/--output are required unless --list-fields is used"
        )

    try:
        candidate = find_portrait_field(pdf, args.field, args.page)
        rect = candidate.locations[0].rect
        portrait_bytes = prepare_portrait_jpeg(
            args.portrait,
            target_size=(rect[2] - rect[0], rect[3] - rect[1]),
            mode=args.fit,
        )
        set_field_icon(pdf, candidate, portrait_bytes)
        save_sheet(pdf, args.output)
    except UpdatePortraitError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}")
    return 0
