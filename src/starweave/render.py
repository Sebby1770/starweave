from __future__ import annotations

import hashlib
import math
import random
from html import escape

from .palette import Palette, get_palette

DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 900
DEFAULT_STARS = 300
DEFAULT_PLANETS = 4


def render_poster(
    seed: str,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    stars: int = DEFAULT_STARS,
    planets: int = DEFAULT_PLANETS,
    palette: str = "aurora",
    title: str | None = None,
    show_title: bool = True,
) -> str:
    """Return a deterministic SVG poster for a seed phrase."""

    _validate_positive("width", width)
    _validate_positive("height", height)
    _validate_positive("stars", stars)
    _validate_positive("planets", planets)
    chosen_palette = get_palette(palette)
    rng = _rng(seed, width, height, stars, planets, palette)
    uid = hashlib.sha1(f"{seed}|{width}|{height}|{palette}".encode()).hexdigest()[:10]

    star_points = _star_points(rng, width, height, stars, chosen_palette)
    body = [
        _defs(uid, chosen_palette),
        f'<rect width="{width}" height="{height}" fill="url(#{uid}-space)" />',
        _render_nebulas(rng, width, height, chosen_palette, uid),
        _render_orbits(rng, width, height, chosen_palette, planets),
        _render_stars(star_points),
        _render_constellations(rng, star_points, chosen_palette),
        _render_planets(rng, width, height, planets, chosen_palette, uid),
    ]

    if show_title:
        body.append(_render_title(title or seed, seed, width, height, chosen_palette))

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(seed)} star poster">',
            *body,
            "</svg>",
            "",
        ]
    )


def _validate_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")


def _rng(*parts: object) -> random.Random:
    seed_material = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(seed_material.encode()).digest()
    return random.Random(int.from_bytes(digest[:16], "big"))


def _defs(uid: str, palette: Palette) -> str:
    start, end = palette.background
    return f"""<defs>
  <linearGradient id="{uid}-space" x1="0%" x2="100%" y1="0%" y2="100%">
    <stop offset="0%" stop-color="{start}" />
    <stop offset="100%" stop-color="{end}" />
  </linearGradient>
  <filter id="{uid}-soft" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="24" />
  </filter>
  <filter id="{uid}-glow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="5" result="blur" />
    <feMerge>
      <feMergeNode in="blur" />
      <feMergeNode in="SourceGraphic" />
    </feMerge>
  </filter>
</defs>"""


def _star_points(
    rng: random.Random,
    width: int,
    height: int,
    stars: int,
    palette: Palette,
) -> list[tuple[float, float, float, str, float]]:
    points = []
    for _ in range(stars):
        x = rng.uniform(0, width)
        y = rng.uniform(0, height)
        radius = rng.triangular(0.35, 2.4, 0.8)
        color = rng.choice(palette.stars)
        opacity = rng.uniform(0.38, 0.98)
        points.append((x, y, radius, color, opacity))
    return points


def _render_nebulas(
    rng: random.Random,
    width: int,
    height: int,
    palette: Palette,
    uid: str,
) -> str:
    shapes = []
    for _ in range(9):
        cx = rng.uniform(-0.05 * width, 1.05 * width)
        cy = rng.uniform(-0.05 * height, 1.05 * height)
        rx = rng.uniform(width * 0.08, width * 0.25)
        ry = rng.uniform(height * 0.06, height * 0.22)
        color = rng.choice(palette.nebula)
        opacity = rng.uniform(0.11, 0.32)
        rotation = rng.uniform(0, 180)
        shapes.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f'fill="{color}" opacity="{opacity:.2f}" filter="url(#{uid}-soft)" '
            f'transform="rotate({rotation:.1f} {cx:.1f} {cy:.1f})" />'
        )
    return '<g style="mix-blend-mode: screen">\n' + "\n".join(shapes) + "\n</g>"


def _render_orbits(
    rng: random.Random,
    width: int,
    height: int,
    palette: Palette,
    planets: int,
) -> str:
    cx = width * rng.uniform(0.35, 0.65)
    cy = height * rng.uniform(0.35, 0.65)
    orbit_count = max(3, planets + 1)
    lines = ['<g fill="none" opacity="0.24">']
    for index in range(orbit_count):
        rx = width * (0.18 + index * 0.07) * rng.uniform(0.88, 1.12)
        ry = height * (0.10 + index * 0.04) * rng.uniform(0.88, 1.12)
        rotation = rng.uniform(-22, 22)
        color = palette.accent[index % len(palette.accent)]
        dash = f"{rng.uniform(4, 10):.1f} {rng.uniform(8, 22):.1f}"
        lines.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f'stroke="{color}" stroke-width="1.2" stroke-dasharray="{dash}" '
            f'transform="rotate({rotation:.1f} {cx:.1f} {cy:.1f})" />'
        )
    lines.append("</g>")
    return "\n".join(lines)


def _render_stars(points: list[tuple[float, float, float, str, float]]) -> str:
    circles = ['<g opacity="1">']
    for x, y, radius, color, opacity in points:
        circles.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.2f}" '
            f'fill="{color}" opacity="{opacity:.2f}" />'
        )
    circles.append("</g>")
    return "\n".join(circles)


def _render_constellations(
    rng: random.Random,
    points: list[tuple[float, float, float, str, float]],
    palette: Palette,
) -> str:
    bright = sorted(points, key=lambda point: point[2] * point[4], reverse=True)[:36]
    rng.shuffle(bright)
    groups = [bright[index : index + 6] for index in range(0, min(len(bright), 24), 6)]
    lines = ['<g fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.42">']
    for group_index, group in enumerate(groups):
        if len(group) < 3:
            continue
        color = palette.accent[group_index % len(palette.accent)]
        coords = [(x, y) for x, y, *_ in group]
        path = " ".join(
            f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}"
            for index, (x, y) in enumerate(coords)
        )
        lines.append(f'<path d="{path}" stroke="{color}" stroke-width="1.4" />')
    lines.append("</g>")
    return "\n".join(lines)


def _render_planets(
    rng: random.Random,
    width: int,
    height: int,
    planets: int,
    palette: Palette,
    uid: str,
) -> str:
    items = [f'<g filter="url(#{uid}-glow)">']
    for index in range(planets):
        angle = rng.uniform(0, math.tau)
        distance_x = width * rng.uniform(0.12, 0.42)
        distance_y = height * rng.uniform(0.08, 0.32)
        cx = width * 0.5 + math.cos(angle) * distance_x
        cy = height * 0.5 + math.sin(angle) * distance_y
        radius = rng.uniform(min(width, height) * 0.018, min(width, height) * 0.052)
        fill = rng.choice(palette.planets)
        shade = rng.choice(palette.background)
        accent = rng.choice(palette.accent)
        items.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="{fill}" opacity="0.96" />'
        )
        items.append(
            f'<circle cx="{cx - radius * 0.28:.1f}" cy="{cy - radius * 0.25:.1f}" '
            f'r="{radius * 0.38:.1f}" fill="#ffffff" opacity="0.18" />'
        )
        items.append(
            f'<path d="M {cx - radius:.1f} {cy + radius * 0.72:.1f} '
            f'C {cx - radius * 0.2:.1f} {cy + radius * 1.15:.1f}, '
            f'{cx + radius * 0.75:.1f} {cy + radius * 0.95:.1f}, '
            f'{cx + radius:.1f} {cy - radius * 0.1:.1f}" '
            f'fill="none" stroke="{shade}" stroke-width="{max(2, radius * 0.12):.1f}" opacity="0.24" />'
        )
        if index % 2 == 0:
            rotation = rng.uniform(-18, 18)
            items.append(
                f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{radius * 1.75:.1f}" ry="{radius * 0.38:.1f}" '
                f'fill="none" stroke="{accent}" stroke-width="{max(1.5, radius * 0.08):.1f}" '
                f'opacity="0.72" transform="rotate({rotation:.1f} {cx:.1f} {cy:.1f})" />'
            )
    items.append("</g>")
    return "\n".join(items)


def _render_title(
    title: str,
    seed: str,
    width: int,
    height: int,
    palette: Palette,
) -> str:
    safe_title = escape(title[:80])
    safe_seed = escape(seed[:96])
    x = max(40, width * 0.045)
    y = height - max(56, height * 0.09)
    accent = palette.accent[0]
    return f"""<g font-family="Avenir Next, Inter, Segoe UI, sans-serif">
  <text x="{x:.1f}" y="{y:.1f}" fill="#f8fafc" font-size="{max(32, width * 0.044):.1f}" font-weight="800">{safe_title}</text>
  <text x="{x:.1f}" y="{y + 34:.1f}" fill="{accent}" font-size="{max(14, width * 0.014):.1f}" opacity="0.86">seed: {safe_seed}</text>
</g>"""
