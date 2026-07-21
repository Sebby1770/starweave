from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from .batch import render_batch
from .gallery import cells_for, render_gallery
from .morph import morph_cells, render_morph, write_morph_frames
from .layers import DEFAULT_LAYERS, LAYERS_BY_NAME, Layer
from .options import (
    DEFAULT_HEIGHT,
    DEFAULT_PLANETS,
    DEFAULT_STARS,
    DEFAULT_WIDTH,
    WALLPAPER_PRESETS,
    RenderOptions,
    parse_wallpaper,
)
from .palette import CHOICES, PALETTES
from .palette_preview import palette_preview_svg
from .render import render_poster
from .themes import THEME_CHOICES, THEMES, get_theme
from .validate import validate_svg_file
from .webexport import explorer_html
from .world import World, diff_worlds, format_diff


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Subcommands live alongside the classic flat CLI.
    if argv and argv[0] == "batch":
        return _run_batch_cmd(argv[1:])
    if argv and argv[0] == "palette-preview":
        return _run_palette_preview_cmd(argv[1:])
    if argv and argv[0] == "diff":
        return _run_diff_cmd(argv[1:])
    if argv and argv[0] == "validate":
        return _run_validate_cmd(argv[1:])

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_palettes:
        for name in sorted(PALETTES):
            print(f"{name:<12} ({PALETTES[name].mood})")
        print(f"{'okabe-ito':<12} (alias of colorblind)")
        return 0

    if args.list_layers:
        for layer in DEFAULT_LAYERS:
            tag = f" [needs '{layer.requires}']" if layer.requires else ""
            print(f"{layer.name}{tag}")
        return 0

    if args.list_themes:
        for name in THEME_CHOICES:
            theme = THEMES[name]
            print(
                f"{name:<10} palette={theme.palette}  "
                f"turb×{theme.turbulence:.2f} bright×{theme.brightness:.2f} "
                f"dens×{theme.density:.2f}  — {theme.description}"
            )
        return 0

    # Resolve theme early — it locks palette + intensity bias.
    theme_name: str | None = getattr(args, "theme", None)
    if theme_name:
        try:
            theme = get_theme(theme_name)
        except ValueError as exc:
            parser.error(str(exc))
        args.palette = theme.palette

    # Multi-seed list rendering: write one poster per line into --out dir.
    if getattr(args, "seed_list", None):
        return _run_seed_list(args, parser)

    try:
        seed = _resolve_seed(args)
    except ValueError as exc:
        parser.error(str(exc))

    # Apply wallpaper size overrides before anything that uses width/height.
    if args.wallpaper:
        try:
            args.width, args.height = parse_wallpaper(args.wallpaper)
        except ValueError as exc:
            parser.error(str(exc))

    if args.describe:
        world = _world_for(seed, args)
        print(json.dumps(world.summary(), indent=2, sort_keys=True))
        return 0

    if args.dump_world:
        world = _world_for(seed, args)
        path = Path(args.dump_world)
        if str(path.parent) not in ("", "."):
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(world.summary(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if not args.quiet:
            print(f"Wrote {path}")
        # Dump-only unless the user also asked for a render path via --out
        # without another exclusive mode. If only --dump-world, stop here.
        if not args.out and not args.ascii and not args.sonify and not args.gallery \
                and args.gallery is None and not args.gallery_palettes \
                and args.morph is None and not args.explorer and not args.reproduce \
                and not getattr(args, "out_dir", None):
            return 0

    if args.myth:
        world = _world_for(seed, args)
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
        if not args.quiet:
            print(f"Wrote {output} — open it in a browser")
        return 0

    if args.ascii:
        from .ascii_art import ascii_poster

        world = _world_for(seed, args)
        cols = args.ascii_width if args.ascii_width is not None else args.cols
        art = ascii_poster(world, cols=cols)
        if args.out:
            Path(args.out).write_text(art + "\n", encoding="utf-8")
            if not args.quiet:
                print(f"Wrote {args.out}")
        else:
            print(art)
        return 0

    if args.sonify:
        from .sonify import sonify

        world = _world_for(seed, args)
        output = Path(args.out or "starweave.wav")
        if str(output.parent) not in ("", "."):
            output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(sonify(world, seconds=args.seconds))
        if not args.quiet:
            print(f"Wrote {output} ({args.seconds:g}s, mood={world.palette.mood})")
        return 0

    if args.morph is not None:
        return _run_morph(args, seed)

    if args.gallery is not None or args.gallery_palettes:
        return _run_gallery(args, seed)

    # If user only requested dump-world (and maybe --out for the dump itself was
    # not set but dump already written), avoid rendering unless they want SVG.
    if args.dump_world and args.out is None:
        return 0

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
            stamp=args.stamp,
            theme=theme_name,
            minify=bool(getattr(args, "minify", False)),
            layers=layers,
        )
    except ValueError as exc:
        parser.error(str(exc))

    output = Path(args.out or "starweave.svg")
    _write(output, svg, args.open)
    if not args.quiet:
        print(f"Wrote {output}")
    return 0


def _world_for(seed: str, args: argparse.Namespace) -> World:
    """Build a World, applying theme intensity bias when set."""

    from .themes import apply_theme

    palette = args.palette
    theme_name = getattr(args, "theme", None)
    if theme_name:
        theme = get_theme(theme_name)
        palette = theme.palette
        world = World.from_seed(seed, palette, getattr(args, "variant", 0))
        return apply_theme(world, theme)
    return World.from_seed(seed, palette, getattr(args, "variant", 0))


def _resolve_seed(args: argparse.Namespace) -> str:
    """Resolve seed from positional arg, --seed-file, or default."""

    file_seed: str | None = None
    if getattr(args, "seed_file", None):
        path = Path(args.seed_file)
        if not path.is_file():
            raise ValueError(f"seed file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"seed file is empty: {path}")
        # First non-empty line is the seed phrase.
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                file_seed = line
                break
        if not file_seed:
            raise ValueError(f"seed file has no usable line: {path}")

    if args.seed and file_seed:
        raise ValueError("pass either a seed phrase or --seed-file, not both")
    if file_seed:
        return file_seed
    return args.seed or "starweave"


def _read_seed_list(path: Path) -> list[str]:
    """Read one seed phrase per line; skip blanks and # comments."""

    if not path.is_file():
        raise ValueError(f"seed-list file not found: {path}")
    seeds: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        seeds.append(line)
    if not seeds:
        raise ValueError(f"seed-list file has no usable lines: {path}")
    return seeds


def _safe_filename(seed: str, index: int) -> str:
    base = "".join(c if c.isalnum() or c in "-_" else "_" for c in seed)
    base = base.strip("_") or f"seed_{index}"
    # Cap length so paths stay reasonable.
    if len(base) > 60:
        base = base[:60]
    return f"{index:03d}_{base}.svg"


def _run_seed_list(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        seeds = _read_seed_list(Path(args.seed_list))
    except ValueError as exc:
        parser.error(str(exc))

    if args.wallpaper:
        try:
            args.width, args.height = parse_wallpaper(args.wallpaper)
        except ValueError as exc:
            parser.error(str(exc))

    out_spec = args.out
    if not out_spec:
        parser.error("--seed-list requires --out DIR/")
    out_dir = Path(out_spec)
    # Treat as directory always for multi-seed output.
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        layers = _select_layers(args.only, args.without)
    except ValueError as exc:
        parser.error(str(exc))

    theme_name = getattr(args, "theme", None)
    written: list[Path] = []
    for i, seed in enumerate(seeds):
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
                stamp=args.stamp,
                theme=theme_name,
                minify=bool(getattr(args, "minify", False)),
                layers=layers,
            )
        except ValueError as exc:
            parser.error(str(exc))
        path = out_dir / _safe_filename(seed, i)
        path.write_text(svg, encoding="utf-8")
        written.append(path)
        if not args.quiet:
            sys.stderr.write(f"\r  seed-list {i + 1}/{len(seeds)}")
            sys.stderr.flush()
    if not args.quiet:
        sys.stderr.write("\n")
        print(f"Wrote {len(written)} posters to {out_dir}/")
    return 0


def _run_validate_cmd(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="starweave validate",
        description="Check that an SVG embeds Starweave reproducibility metadata.",
    )
    parser.add_argument("files", nargs="+", help="SVG file(s) to validate.")
    parser.add_argument("--quiet", action="store_true", help="Only set exit status.")
    args = parser.parse_args(argv)

    exit_code = 0
    for file in args.files:
        result = validate_svg_file(file)
        if not result.ok:
            exit_code = 1
        if not args.quiet:
            print(result.summary())
    return exit_code


def _run_batch_cmd(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="starweave batch",
        description="Render a seed family: base#0 … base#N-1 into a directory.",
    )
    parser.add_argument("base", help="Base seed phrase for the family.")
    parser.add_argument("--count", type=_positive_int, default=12, help="Number of family members (default 12).")
    parser.add_argument("--out", required=True, help="Output directory for the family.")
    parser.add_argument("--palette", choices=CHOICES, default="aurora")
    parser.add_argument("--theme", choices=THEME_CHOICES, help="Theme pack (overrides palette + intensity).")
    parser.add_argument("--width", type=_positive_int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=_positive_int, default=DEFAULT_HEIGHT)
    parser.add_argument("--wallpaper", metavar="SPEC", help="Size preset or WxH (overrides width/height).")
    parser.add_argument("--stars", type=_positive_int, default=DEFAULT_STARS)
    parser.add_argument("--planets", type=_positive_int, default=DEFAULT_PLANETS)
    parser.add_argument("--animate", action="store_true")
    parser.add_argument("--no-title", action="store_true")
    parser.add_argument("--title", help="Title override applied to every member.")
    parser.add_argument("--stamp", action="store_true", help="Draw corner hash stamp on each poster.")
    parser.add_argument("--minify", action="store_true", help="Collapse inter-tag whitespace in each SVG.")
    parser.add_argument("--no-index", action="store_true", help="Skip writing index.html.")
    parser.add_argument("--no-manifest", action="store_true", help="Skip writing manifest.json.")
    parser.add_argument("--quiet", action="store_true", help="Hide progress on stderr.")
    args = parser.parse_args(argv)

    width, height = args.width, args.height
    if args.wallpaper:
        try:
            width, height = parse_wallpaper(args.wallpaper)
        except ValueError as exc:
            parser.error(str(exc))

    palette = args.palette
    theme_name = args.theme
    if theme_name:
        palette = get_theme(theme_name).palette

    opts = RenderOptions(
        width=width,
        height=height,
        stars=args.stars,
        planets=args.planets,
        title=args.title,
        show_title=not args.no_title,
        animate=args.animate,
        stamp=args.stamp,
    )
    out_dir = Path(args.out)

    # Batch currently goes through render_poster per member; when theme/minify
    # are set, re-render with those knobs after the standard batch, or patch
    # render_batch usage. Simpler: custom loop when theme or minify is set.
    if theme_name or args.minify:
        out_dir.mkdir(parents=True, exist_ok=True)
        members = []
        from .batch import BatchMember, family_seed, _batch_index_html, _batch_manifest

        for i in range(args.count):
            seed = family_seed(args.base, i)
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in seed)
            path = out_dir / f"{safe}.svg"
            svg = render_poster(
                seed,
                width=opts.width,
                height=opts.height,
                stars=opts.stars,
                planets=opts.planets,
                palette=palette,
                title=opts.title,
                show_title=opts.show_title,
                animate=opts.animate,
                stamp=opts.stamp,
                theme=theme_name,
                minify=args.minify,
            )
            path.write_text(svg, encoding="utf-8")
            world = World.from_seed(seed, palette)
            members.append(
                BatchMember(
                    seed=seed,
                    index=i,
                    path=path,
                    world_name=world.name,
                    palette=world.palette.name,
                )
            )
            if not args.quiet:
                from .batch import _progress

                _progress(i + 1, args.count)
        if not args.no_index:
            (out_dir / "index.html").write_text(
                _batch_index_html(args.base, members), encoding="utf-8"
            )
        if not args.no_manifest:
            (out_dir / "manifest.json").write_text(
                _batch_manifest(args.base, members, palette=palette), encoding="utf-8"
            )
    else:
        members = render_batch(
            args.base,
            args.count,
            out_dir,
            palette=palette,
            opts=opts,
            progress=not args.quiet,
            index_html=not args.no_index,
            manifest=not args.no_manifest,
        )
    # Final summary always prints (quiet only hides the progress bar).
    print(f"Wrote {len(members)} posters to {out_dir}/")
    if not args.no_index:
        print(f"  index: {out_dir / 'index.html'}")
    if not args.no_manifest:
        print(f"  manifest: {out_dir / 'manifest.json'}")
    return 0


def _run_diff_cmd(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="starweave diff",
        description="Compare World knobs and features between two seed phrases.",
    )
    parser.add_argument("seed_a", help="First seed phrase.")
    parser.add_argument("seed_b", help="Second seed phrase.")
    parser.add_argument("--palette", choices=CHOICES, default="aurora")
    parser.add_argument("--variant-a", type=int, default=0, help="Variant for seed A.")
    parser.add_argument("--variant-b", type=int, default=0, help="Variant for seed B.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    a = World.from_seed(args.seed_a, args.palette, args.variant_a)
    b = World.from_seed(args.seed_b, args.palette, args.variant_b)
    result = diff_worlds(a, b)
    print(format_diff(result, as_json=args.json))
    return 0


def _run_palette_preview_cmd(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="starweave palette-preview",
        description="Write a small SVG swatch strip of every built-in palette.",
    )
    parser.add_argument("--out", default="palettes.svg", help="Output SVG path (default palettes.svg).")
    parser.add_argument("--open", action="store_true", help="Open the result after writing.")
    parser.add_argument("--quiet", action="store_true", help="Suppress status line.")
    args = parser.parse_args(argv)
    svg = palette_preview_svg()
    output = Path(args.out)
    _write(output, svg, args.open)
    if not args.quiet:
        print(f"Wrote {output} ({len(PALETTES)} palettes)")
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
        stamp=args.stamp,
    )
    try:
        cells = cells_for(
            seed,
            mode=mode,
            count=count,
            opts=opts,
            palette=args.palette,
            progress=not getattr(args, "quiet", False),
        )
    except ValueError as exc:
        print(f"starweave: {exc}", file=sys.stderr)
        return 2
    html = render_gallery(seed, cells)
    output = Path(args.out or "gallery.html")
    _write(output, html, args.open)
    if not args.quiet:
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
        minify=bool(getattr(args, "minify", False)),
    )
    output = Path(args.out or "reproduced.svg")
    _write(output, svg, args.open)
    if not args.quiet:
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
        stamp=args.stamp,
    )
    minify = bool(getattr(args, "minify", False))
    out_dir = getattr(args, "out_dir", None)

    # Individual frame SVGs when --out-dir is set.
    if out_dir:
        try:
            paths = write_morph_frames(
                seed,
                args.morph,
                frames=args.frames,
                palette=args.palette,
                opts=opts,
                out_dir=Path(out_dir),
                minify=minify,
            )
        except ValueError as exc:
            print(f"starweave: {exc}", file=sys.stderr)
            return 2
        if not args.quiet:
            print(f"Wrote {len(paths)} frames to {out_dir}/")
        # Also write HTML strip if --out was given alongside --out-dir.
        if not args.out:
            return 0

    try:
        cells = morph_cells(seed, args.morph, frames=args.frames, palette=args.palette, opts=opts)
    except ValueError as exc:
        print(f"starweave: {exc}", file=sys.stderr)
        return 2
    html = render_morph(seed, args.morph, cells)
    if minify:
        # HTML minify is not attempted; minify only applies to SVG frames above.
        pass
    output = Path(args.out or "morph.html")
    if out_dir and not args.out:
        return 0
    _write(output, html, args.open)
    if not args.quiet:
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
    presets = ", ".join(sorted(WALLPAPER_PRESETS))
    parser = argparse.ArgumentParser(
        prog="starweave",
        description="Generate deterministic SVG space posters from seed phrases.",
    )
    parser.add_argument("seed", nargs="?", help="Phrase used to generate the poster.")
    parser.add_argument("--seed-file", metavar="PATH", help="Read seed phrase from a file (first non-empty, non-# line).")
    parser.add_argument(
        "--seed-list",
        metavar="FILE",
        help="Read many seeds (one per line) and write each poster into --out DIR/.",
    )
    parser.add_argument("--out", help="Output path (.svg, or .html for galleries). Directory when used with --seed-list.")
    parser.add_argument(
        "--out-dir",
        metavar="DIR",
        help="With --morph: write individual frame_00.svg … SVGs into DIR.",
    )
    parser.add_argument("--width", type=_positive_int, default=DEFAULT_WIDTH, help="Poster width.")
    parser.add_argument("--height", type=_positive_int, default=DEFAULT_HEIGHT, help="Poster height.")
    parser.add_argument(
        "--wallpaper",
        metavar="SPEC",
        help=f"Wallpaper size: preset ({presets}) or WxH e.g. 1920x1080. Overrides --width/--height.",
    )
    parser.add_argument("--stars", type=_positive_int, default=DEFAULT_STARS, help="Number of stars.")
    parser.add_argument("--planets", type=_positive_int, default=DEFAULT_PLANETS, help="Number of planets.")
    parser.add_argument("--palette", choices=CHOICES, default="aurora", help="Color palette ('auto' picks from the seed; 'colorblind'/'okabe-ito' is colourblind-safe).")
    parser.add_argument(
        "--theme",
        choices=THEME_CHOICES,
        help="Theme pack: noir|biolume|ember|ice — fixed palette + intensity bias (overrides --palette).",
    )
    parser.add_argument("--variant", type=int, default=0, help="Alternate deterministic draw of the same seed.")
    parser.add_argument("--animate", action="store_true", help="Emit an animated SVG (twinkle/drift/orbit).")
    parser.add_argument("--stamp", action="store_true", help="Draw a corner micro-label with a short content hash.")
    parser.add_argument("--minify", action="store_true", help="Collapse inter-tag whitespace in SVG output.")
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
    parser.add_argument("--cols", type=_positive_int, default=100, help="Width in characters for --ascii (alias of --ascii-width).")
    parser.add_argument("--ascii-width", type=_positive_int, default=None, metavar="N", help="Width in characters for --ascii.")
    parser.add_argument("--describe", action="store_true", help="Print the seed's world as JSON and exit.")
    parser.add_argument("--dump-world", metavar="FILE", help="Write the seed's world as JSON to FILE (no render unless --out is also set).")
    parser.add_argument("--myth", action="store_true", help="Print the constellation's generated origin myth.")
    parser.add_argument("--reproduce", metavar="FILE", help="Regenerate a poster from the metadata embedded in an SVG.")
    parser.add_argument("--open", action="store_true", help="Open the result after writing it.")
    parser.add_argument("--quiet", action="store_true", help="Suppress status lines (progress still uses --quiet for galleries/batch).")
    parser.add_argument("--list-palettes", action="store_true", help="List palette names and exit.")
    parser.add_argument("--list-layers", action="store_true", help="List layer names and exit.")
    parser.add_argument("--list-themes", action="store_true", help="List theme packs and exit.")
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
