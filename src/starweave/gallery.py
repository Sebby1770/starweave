"""Contact-sheet gallery — many posters inlined on one self-contained page.

Each poster is embedded as live inline SVG (not ``<img>``), so animations keep
running and the whole gallery is a single portable HTML file. Per-document id
prefixes (see :mod:`~starweave.svg`) keep gradients from leaking between cells.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from html import escape

from .options import RenderOptions
from .palette import PALETTES
from .scene import render_scene
from .world import World


@dataclass
class Cell:
    svg: str
    title: str
    subtitle: str


def _strip_xml_decl(svg: str) -> str:
    # Inline SVG inside HTML must not carry an <?xml ...?> prolog.
    if svg.startswith("<?xml"):
        return svg.split("?>", 1)[1].lstrip("\n")
    return svg


def _progress(done: int, total: int, label: str = "gallery") -> None:
    """Simple stderr progress (dots + percent) — no third-party deps."""

    if total <= 0:
        return
    pct = int(100 * done / total)
    sys.stderr.write(f"\r  {label} {'.' * done} {done}/{total} ({pct}%)")
    if done >= total:
        sys.stderr.write("\n")
    sys.stderr.flush()


def cells_for(
    seed: str,
    *,
    mode: str,
    count: int,
    opts: RenderOptions,
    palette: str = "auto",
    progress: bool = False,
) -> list[Cell]:
    """Build gallery cells.

    ``mode="variants"`` draws ``count`` deterministic variants of one seed.
    ``mode="palettes"`` draws the same seed once per built-in palette.
    """

    cells: list[Cell] = []
    if mode == "palettes":
        names = sorted(PALETTES)
        total = len(names)
        for i, name in enumerate(names):
            world = World.from_seed(seed, name)
            svg = _strip_xml_decl(render_scene(world, opts))
            cells.append(Cell(svg=svg, title=name, subtitle=world.name))
            if progress:
                _progress(i + 1, total)
    else:  # variants
        for variant in range(count):
            world = World.from_seed(seed, palette, variant)
            svg = _strip_xml_decl(render_scene(world, opts))
            cells.append(
                Cell(svg=svg, title=f"variant {variant}", subtitle=world.name)
            )
            if progress:
                _progress(variant + 1, count)
    return cells


def render_gallery(seed: str, cells: list[Cell]) -> str:
    heading = escape(seed)
    body = []
    for cell in cells:
        body.append(
            '<figure class="cell">'
            f'{cell.svg}'
            f'<figcaption><b>{escape(cell.title)}</b>'
            f'<span>{escape(cell.subtitle)}</span></figcaption>'
            '</figure>'
        )
    cards = "\n".join(body)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Starweave — {heading}</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; background: #06070d; color: #e2e8f0;
         font-family: "Avenir Next", Inter, "Segoe UI", system-ui, sans-serif; }}
  header {{ padding: 28px 32px 8px; }}
  header h1 {{ margin: 0; font-size: 22px; letter-spacing: 1px; }}
  header p {{ margin: 4px 0 0; color: #94a3b8; font-size: 13px; }}
  .grid {{ display: grid; gap: 18px; padding: 20px 32px 48px;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }}
  .cell {{ margin: 0; background: #0b0d16; border: 1px solid #1e2330;
          border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,.35); }}
  .cell svg {{ display: block; width: 100%; height: auto; }}
  figcaption {{ display: flex; justify-content: space-between; align-items: baseline;
               padding: 10px 14px; font-size: 12px; }}
  figcaption span {{ color: #8b95a7; font-style: italic; }}
</style>
</head>
<body>
<header>
  <h1>Starweave · {heading}</h1>
  <p>{len(cells)} deterministic posters from one seed — open in any browser.</p>
</header>
<main class="grid">
{cards}
</main>
</body>
</html>
"""
