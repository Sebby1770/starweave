"""Seed-space interpolation.

The single biggest idea this unlocks: a poster isn't a discrete output, it's a
*sample of a continuous space*. ``morph(A, B, n)`` walks the geodesic between two
seeds, emitting ``n`` frames where the palette and mood knobs interpolate while
the underlying structure (held from A) stays put — so you watch one sky shift
temperament from A to B. The frames are a contact-sheet strip you can scrub.

With ``write_morph_frames``, each frame is also written as an individual SVG
(``frame_00.svg`` …) for animation pipelines.
"""

from __future__ import annotations

from pathlib import Path

from .gallery import Cell, render_gallery
from .minify import minify_svg
from .options import RenderOptions
from .scene import render_scene
from .world import World


def _strip_xml_decl(svg: str) -> str:
    if svg.startswith("<?xml"):
        return svg.split("?>", 1)[1].lstrip("\n")
    return svg


def morph_worlds(
    seed_a: str,
    seed_b: str,
    *,
    frames: int,
    palette: str,
) -> list[tuple[float, World]]:
    """Return ``(t, world)`` pairs along the path from ``seed_a`` to ``seed_b``."""

    if frames < 2:
        frames = 2
    a = World.from_seed(seed_a, palette, 0)
    b = World.from_seed(seed_b, palette, 0)
    out: list[tuple[float, World]] = []
    for i in range(frames):
        t = i / (frames - 1)
        world = World.blended(a, b, t)
        # Distinct variant per frame -> distinct SVG id prefix, so the inlined
        # posters on one page never share gradient/filter ids.
        world.variant = i
        out.append((t, world))
    return out


def morph_cells(
    seed_a: str,
    seed_b: str,
    *,
    frames: int,
    palette: str,
    opts: RenderOptions,
) -> list[Cell]:
    """Render ``frames`` posters along the path from ``seed_a`` to ``seed_b``."""

    cells: list[Cell] = []
    for t, world in morph_worlds(seed_a, seed_b, frames=frames, palette=palette):
        svg = _strip_xml_decl(render_scene(world, opts))
        cells.append(Cell(svg=svg, title=f"t = {t:.2f}", subtitle=_corner(t, seed_a, seed_b)))
    return cells


def write_morph_frames(
    seed_a: str,
    seed_b: str,
    *,
    frames: int,
    palette: str,
    opts: RenderOptions,
    out_dir: Path,
    minify: bool = False,
) -> list[Path]:
    """Write ``frame_00.svg`` … ``frame_{N-1:02d}.svg`` into ``out_dir``.

    Returns the list of written paths in frame order.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    digits = max(2, len(str(max(frames - 1, 0))))
    for i, (_t, world) in enumerate(
        morph_worlds(seed_a, seed_b, frames=frames, palette=palette)
    ):
        svg = render_scene(world, opts)
        if minify:
            svg = minify_svg(svg)
        path = out_dir / f"frame_{i:0{digits}d}.svg"
        path.write_text(svg, encoding="utf-8")
        paths.append(path)
    return paths


def _corner(t: float, a: str, b: str) -> str:
    if t <= 0.0:
        return a
    if t >= 1.0:
        return b
    return f"{a} → {b}"


def render_morph(seed_a: str, seed_b: str, cells: list[Cell]) -> str:
    return render_gallery(f"{seed_a}  →  {seed_b}", cells)
