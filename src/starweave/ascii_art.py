"""Render a seed's world as terminal star-art.

The same World that paints an SVG poster can also be sampled onto a character
grid: nebulae become a faint wash, stars become bright glyphs, planets become
``O``. A different medium, same deterministic universe.
"""

from __future__ import annotations

import math

from .world import World

#: Intensity ramp from empty space to a bright star (ASCII-only for any terminal).
#: Slightly denser than the classic 10-step ramp so mid-tones read better.
_RAMP = " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def ascii_poster(world: World, cols: int = 100, rows: int | None = None) -> str:
    cols = max(8, cols)
    if rows is None:
        rows = max(6, cols // 3)
    field = [[0.0] * cols for _ in range(rows)]

    # Nebula wash: a few soft radial blobs.
    neb = world.stream("ascii-nebula")
    for _ in range(round(3 + 4 * world.density)):
        bx = neb.uniform(0, cols)
        by = neb.uniform(0, rows)
        radius = neb.uniform(cols * 0.12, cols * 0.3)
        peak = neb.uniform(0.12, 0.28) * (0.6 + 0.6 * world.turbulence)
        x0, x1 = max(0, int(bx - radius)), min(cols, int(bx + radius) + 1)
        y0, y1 = max(0, int(by - radius)), min(rows, int(by + radius) + 1)
        for y in range(y0, y1):
            for x in range(x0, x1):
                # rows are ~2x taller than wide in a terminal; scale y distance.
                dist = math.hypot(x - bx, (y - by) * 2.0)
                if dist < radius:
                    field[y][x] += peak * (1 - dist / radius)

    # Stars: bright points.
    stars = world.stream("ascii-stars")
    for _ in range(round(cols * rows * (0.03 + 0.05 * world.density))):
        x = stars.randrange(cols)
        y = stars.randrange(rows)
        field[y][x] = max(field[y][x], 0.5 + 0.5 * stars.random() * world.brightness)

    # Planets: a handful of solid 'O's that override the ramp.
    overrides: dict[tuple[int, int], str] = {}
    planets = world.stream("ascii-planets")
    for _ in range(planets.randint(2, 4)):
        x = planets.randrange(cols)
        y = planets.randrange(rows)
        overrides[(y, x)] = "O"
    if world.has("moon"):
        mx, my = planets.randrange(cols), planets.randrange(max(1, rows // 3))
        overrides[(my, mx)] = "@"
    if world.has("blackhole"):
        bx, by = planets.randrange(cols), planets.randrange(rows)
        overrides[(by, bx)] = "o"

    lines = []
    for y in range(rows):
        chars = []
        for x in range(cols):
            if (y, x) in overrides:
                chars.append(overrides[(y, x)])
                continue
            level = field[y][x]
            idx = min(len(_RAMP) - 1, int(level * (len(_RAMP) - 1) + 0.5))
            chars.append(_RAMP[idx])
        lines.append("".join(chars))

    header = f"STARWEAVE · {world.name.upper()}"
    return header + "\n" + "\n".join(lines) + "\n" + world.seed
