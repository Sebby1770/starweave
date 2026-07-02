from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from .gallery import cells_for, render_gallery
from .morph import morph_cells, render_morph
from .layers import DEFAULT_LAYERS, LAYERS_BY_NAME, Layer
from .options import (
    DEFAULT_HEIGHT,
    DEFAULT_PLANETS,
    DEFAULT_STARS,
    DEFAULT_WIDTH,
    RenderOptions,
)
from .palette import CHOICES, PALETTES
from .render import render_poster
from .webexport import explorer_html
from .world import World


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_palettes:
        for name in sorted(PALETTES):
            print(f"{name:<10} ({PALETTES[name].mood})")
        return 0

    if args.list_layers:
        for layer in DEFAULT_LAYERS:
            tag = f" [needs '{layer.requires}']" if layer.requires else ""
            print(f"{layer.name}{tag}")
        return 0

    seed = args.seed or "starweave"

    if args.describe:
        world = World.from_seed(seed, args.palette, args.variant)
        print(json.dumps(world.summary(), indent=2, sort_keys=True))
        return 0

    if args.myth:
        world = World.from_seed(seed, args.palette, args.variant)
        print(world.name)
        print(world.myth)
        return 0

    try:
        layers = _select_layers(args.only, args.without)
    except ValueError as exc:
        parser.error(str(exc))

    if args.reproduce:
        return _run_reproduce(args)

    if args.explorer:
        output = Path(args.out or "explorer.html")
        _write(output, explorer_html(), args.open)
        print(f"Wrote {output} — open it in a browser")
        return 0

    if args.ascii:
        from .ascii_art import ascii_poster

        world = World.from_seed(seed, args.palette, args.variant)
        art = ascii_poster(world, cols=args.cols)
        if args.out:
            Path(args.out).write_text(art + "\n", encoding="utf-8")
            print(f"Wrote {args.out}")
        else:
            print(art)
        return 0

    if args.sonify:
        from .sonify import sonify

        world = World.from_seed(seed, args.palette, args.variant)
        output = Path(args.out or "starweave.wav")
        if str(output.parent) not in ("", "."):
            output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(sonify(world, seconds=args.seconds))
        print(f"Wrote {output} ({args.seconds:g}s, mood={world.palette.mood})")
        return 0

    if args.morph is not None:
        return _run_morph(args, seed)

    if args.gallery is not None or args.gallery_palettes:
        return _run_gallery(args, seed)

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
            animate=args.animate,
            variant=args.variant,
            layers=layers,
        )
    except ValueError as exc:
        parser.error(str(exc))

    output = Path(args.out or "starweave.svg")
    _write(output, svg, args.open)
    print(f"Wrote {output}")
    return 0


def _run_gallery(args: argparse.Namespace, seed: str) -> int:
    mode = "palettes" if args.gallery_palettes else "variants"
    count = args.gallery if args.gallery is not None else 6
    # Gallery cells default to a compact size unless the user overrode it.
    width = args.width if args.width != DEFAULT_WIDTH else 480
    height = args.height if args.height != DEFAULT_HEIGHT else 300
    opts = RenderOptions(
        width=width,
        height=height,
        stars=args.stars if args.stars != DEFAULT_STARS else 120,
        planets=args.planets,
        title=args.title,
        show_title=not args.no_title,
        animate=args.animate,
    )
    try:
        cells = cells_for(seed, mode=mode, count=count, opts=opts, palette=args.palette)
    except ValueError as exc:
        print(f"starweave: {exc}", file=sys.stderr)
        return 2
    html = render_gallery(seed, cells)
    output = Path(args.out or "gallery.html")
    _write(output, html, args.open)
    print(f"Wrote {output} ({len(cells)} posters)")
    return 0


def _run_reproduce(args: argparse.Namespace) -> int:
    """Regenerate a poster byte-for-byte from the metadata embedded in an SVG."""

    import xml.dom.minidom as minidom

    try:
        doc = minidom.parse(args.reproduce)
    except Exception as exc:  # noqa: BLE001 - report any parse failure cleanly
        print(f"starweave: could not read {args.reproduce}: {exc}", file=sys.stderr)
        return 2
    nodes = doc.getElementsByTagName("starweave")
    if not nodes:
        print(f"starweave: no reproducibility metadata in {args.reproduce}", file=sys.stderr)
        return 2
    params = json.loads(nodes[0].getAttribute("data-params"))
    world = params["world"]
    width, height = params["size"]
    svg = render_poster(
        world["seed"],
        width=width,
        height=height,
        stars=params["stars"],
        planets=params["planets"],
        palette=world["palette"],
        variant=world["variant"],
        animate=params.get("animated", False),
    )
    output = Path(args.out or "reproduced.svg")
    _write(output, svg, args.open)
    print(f"Reproduced {world['seed']!r} -> {output}")
    return 0


def _run_morph(args: argparse.Namespace, seed: str) -> int:
    width = args.width if args.width != DEFAULT_WIDTH else 480
    height = args.height if args.height != DEFAULT_HEIGHT else 300
    opts = RenderOptions(
        width=width,
        height=height,
        stars=args.stars if args.stars != DEFAULT_STARS else 120,
        planets=args.planets,
        title=args.title,
        show_title=not args.no_title,
        animate=args.animate,
    )
    try:
        cells = morph_cells(seed, args.morph, frames=args.frames, palette=args.palette, opts=opts)
    except ValueError as exc:
        print(f"starweave: {exc}", file=sys.stderr)
        return 2
    html = render_morph(seed, args.morph, cells)
    output = Path(args.out or "morph.html")
    _write(output, html, args.open)
    print(f"Wrote {output} ({len(cells)} frames: {seed!r} -> {args.morph!r})")
    return 0


def _write(output: Path, text: str, open_after: bool) -> None:
    if str(output.parent) not in ("", "."):
        output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    if open_after:
        webbrowser.open(output.resolve().as_uri())


def _select_layers(only: str | None, without: str | None) -> tuple[Layer, ...]:
    def parse(spec: str | None) -> list[str]:
        if not spec:
            return []
        return [name.strip() for name in spec.split(",") if name.strip()]

    only_names = parse(only)
    without_names = parse(without)
    unknown = (set(only_names) | set(without_names)) - set(LAYERS_BY_NAME)
    if unknown:
        valid = ", ".join(LAYERS_BY_NAME)
        raise ValueError(f"unknown layer(s): {', '.join(sorted(unknown))}. Valid: {valid}")

    chosen = set(only_names) if only_names else set(LAYERS_BY_NAME)
    chosen -= set(without_names)
    return tuple(layer for layer in DEFAULT_LAYERS if layer.name in chosen)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="starweave",
        description="Generate deterministic SVG space posters from seed phrases.",
    )
    parser.add_argument("seed", nargs="?", help="Phrase used to generate the poster.")
    parser.add_argument("--out", help="Output path (.svg, or .html for galleries).")
    parser.add_argument("--width", type=_positive_int, default=DEFAULT_WIDTH, help="Poster width.")
    parser.add_argument("--height", type=_positive_int, default=DEFAULT_HEIGHT, help="Poster height.")
    parser.add_argument("--stars", type=_positive_int, default=DEFAULT_STARS, help="Number of stars.")
    parser.add_argument("--planets", type=_positive_int, default=DEFAULT_PLANETS, help="Number of planets.")
    parser.add_argument("--palette", choices=CHOICES, default="aurora", help="Color palette ('auto' picks from the seed).")
    parser.add_argument("--variant", type=int, default=0, help="Alternate deterministic draw of the same seed.")
    parser.add_argument("--animate", action="store_true", help="Emit an animated SVG (twinkle/drift/orbit).")
    parser.add_argument("--only", help="Comma-separated layers to keep (e.g. background,stars,title).")
    parser.add_argument("--without", help="Comma-separated layers to drop.")
    parser.add_argument("--title", help="Title printed on the poster.")
    parser.add_argument("--no-title", action="store_true", help="Hide poster title text.")
    parser.add_argument("--gallery", type=int, nargs="?", const=6, metavar="N", help="Write an HTML contact sheet of N seed variants.")
    parser.add_argument("--gallery-palettes", action="store_true", help="Gallery: one poster per built-in palette.")
    parser.add_argument("--morph", metavar="SEED_B", help="Interpolate the seed-space from this seed to SEED_B (HTML strip).")
    parser.add_argument("--frames", type=_positive_int, default=7, help="Number of frames for --morph.")
    parser.add_argument("--explorer", action="store_true", help="Write a self-contained interactive web explorer (HTML).")
    parser.add_argument("--sonify", action="store_true", help="Render the seed as a deterministic WAV tune.")
    parser.add_argument("--seconds", type=float, default=12.0, help="Length of the --sonify tune.")
    parser.add_argument("--ascii", action="store_true", help="Render the seed as terminal star-art.")
    parser.add_argument("--cols", type=_positive_int, default=100, help="Width in characters for --ascii.")
    parser.add_argument("--describe", action="store_true", help="Print the seed's world as JSON and exit.")
    parser.add_argument("--myth", action="store_true", help="Print the constellation's generated origin myth.")
    parser.add_argument("--reproduce", metavar="FILE", help="Regenerate a poster from the metadata embedded in an SVG.")
    parser.add_argument("--open", action="store_true", help="Open the result after writing it.")
    parser.add_argument("--list-palettes", action="store_true", help="List palette names and exit.")
    parser.add_argument("--list-layers", action="store_true", help="List layer names and exit.")
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
