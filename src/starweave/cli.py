from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from .palette import PALETTES
from .render import DEFAULT_HEIGHT, DEFAULT_PLANETS, DEFAULT_STARS, DEFAULT_WIDTH, render_poster


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_palettes:
        for name in sorted(PALETTES):
            print(name)
        return 0

    seed = args.seed or "starweave"
    try:
        svg = render_poster(
            seed,
            width=args.width,
            height=args.height,
            stars=args.stars,
            planets=args.planets,
            palette=args.palette,
            title=args.title,
            show_title=not args.no_title,
        )
    except ValueError as exc:
        parser.error(str(exc))

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")

    if args.open:
        webbrowser.open(output.resolve().as_uri())

    print(f"Wrote {output}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="starweave",
        description="Generate deterministic SVG space posters from seed phrases.",
    )
    parser.add_argument("seed", nargs="?", help="Phrase used to generate the poster.")
    parser.add_argument("--out", default="starweave.svg", help="SVG output path.")
    parser.add_argument("--width", type=_positive_int, default=DEFAULT_WIDTH, help="Poster width.")
    parser.add_argument("--height", type=_positive_int, default=DEFAULT_HEIGHT, help="Poster height.")
    parser.add_argument("--stars", type=_positive_int, default=DEFAULT_STARS, help="Number of stars.")
    parser.add_argument("--planets", type=_positive_int, default=DEFAULT_PLANETS, help="Number of planets.")
    parser.add_argument("--palette", choices=sorted(PALETTES), default="aurora", help="Color palette.")
    parser.add_argument("--title", help="Title printed on the poster.")
    parser.add_argument("--no-title", action="store_true", help="Hide poster title text.")
    parser.add_argument("--open", action="store_true", help="Open the SVG after writing it.")
    parser.add_argument("--list-palettes", action="store_true", help="List palette names and exit.")
    return parser


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
