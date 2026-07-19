"""Build a small SVG swatch strip of every built-in palette."""

from __future__ import annotations

from .palette import PALETTES
from .svg import esc, fmt


def palette_preview_svg(
    *,
    swatch_w: int = 120,
    swatch_h: int = 160,
    gap: int = 12,
    pad: int = 24,
) -> str:
    """Return an SVG document showing one vertical swatch column per palette."""

    names = sorted(PALETTES)
    n = len(names)
    width = pad * 2 + n * swatch_w + max(0, n - 1) * gap
    height = pad * 2 + swatch_h + 36
    defs: list[str] = []
    body: list[str] = []

    for i, name in enumerate(names):
        p = PALETTES[name]
        x = pad + i * (swatch_w + gap)
        y = pad
        gid = f"bg-{name}"
        defs.append(
            f'<linearGradient id="{gid}" x1="0%" y1="0%" x2="0%" y2="100%">'
            f'<stop offset="0%" stop-color="{p.background[0]}" />'
            f'<stop offset="100%" stop-color="{p.background[1]}" />'
            f"</linearGradient>"
        )
        body.append(
            f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(swatch_w)}" '
            f'height="{fmt(swatch_h)}" rx="10" fill="url(#{gid})" '
            f'stroke="#1e2330" stroke-width="1" />'
        )
        roles = (p.nebula, p.stars, p.planets, p.accent)
        stripe_h = 14
        stripe_y0 = y + swatch_h - len(roles) * (stripe_h + 4) - 10
        for ri, colors in enumerate(roles):
            sy = stripe_y0 + ri * (stripe_h + 4)
            cell_w = (swatch_w - 16) / max(1, len(colors))
            for ci, color in enumerate(colors):
                body.append(
                    f'<rect x="{fmt(x + 8 + ci * cell_w)}" y="{fmt(sy)}" '
                    f'width="{fmt(cell_w - 1)}" height="{fmt(stripe_h)}" '
                    f'rx="2" fill="{color}" />'
                )
        body.append(
            f'<text x="{fmt(x + swatch_w / 2)}" y="{fmt(y + swatch_h + 18)}" '
            f'fill="#e2e8f0" font-size="12" font-family="Avenir Next, Inter, sans-serif" '
            f'text-anchor="middle" font-weight="600">{esc(name)}</text>'
        )
        body.append(
            f'<text x="{fmt(x + swatch_w / 2)}" y="{fmt(y + swatch_h + 32)}" '
            f'fill="#8b95a7" font-size="10" font-family="Avenir Next, Inter, sans-serif" '
            f'text-anchor="middle">{esc(p.mood)}</text>'
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Starweave palette preview">\n'
        '<rect width="100%" height="100%" fill="#06070d" />\n'
        f"<defs>\n{chr(10).join(defs)}\n</defs>\n"
        f"{chr(10).join(body)}\n"
        "</svg>\n"
    )
