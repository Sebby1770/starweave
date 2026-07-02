"""Seed-space interpolation.

The single biggest idea this unlocks: a poster isn't a discrete output, it's a
*sample of a continuous space*. ``morph(A, B, n)`` walks the geodesic between two
seeds, emitting ``n`` frames where the palette and mood knobs interpolate while
the underlying structure (held from A) stays put — so you watch one sky shift
temperament from A to B. The frames are a contact-sheet strip you can scrub.
"""

from __future__ import annotations

from .gallery import Cell, render_gallery
from .options import RenderOptions
from .scene import render_scene
from .world import World


def _strip_xml_decl(svg: str) -> str:
    if svg.startswith("<?xml"):
        return svg.split("?>", 1)[1].lstrip("\n")
    return svg


def morph_cells(
    seed_a: str,
    seed_b: str,
    *,
    frames: int,
    palette: str,
    opts: RenderOptions,
) -> list[Cell]:
    """Render ``frames`` posters along the path from ``seed_a`` to ``seed_b``."""

    if frames < 2:
        frames = 2
    a = World.from_seed(seed_a, palette, 0)
    b = World.from_seed(seed_b, palette, 0)
    cells: list[Cell] = []
    for i in range(frames):
        t = i / (frames - 1)
        world = World.blended(a, b, t)
        # Distinct variant per frame -> distinct SVG id prefix, so the inlined
        # posters on one page never share gradient/filter ids.
        world.variant = i
        svg = _strip_xml_decl(render_scene(world, opts))
        cells.append(Cell(svg=svg, title=f"t = {t:.2f}", subtitle=_corner(t, seed_a, seed_b)))
    return cells


def _corner(t: float, a: str, b: str) -> str:
    if t <= 0.0:
        return a
    if t >= 1.0:
        return b
    return f"{a} → {b}"


def render_morph(seed_a: str, seed_b: str, cells: list[Cell]) -> str:
    return render_gallery(f"{seed_a}  →  {seed_b}", cells)
