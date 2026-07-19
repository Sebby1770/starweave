"""Seed-family batch rendering — N related posters from one base phrase.

Each member uses the seed ``{base}#{index}`` so the family is fully
reproducible from the base string and count alone.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path

from .options import RenderOptions
from .render import render_poster
from .world import World


@dataclass
class BatchMember:
    seed: str
    index: int
    path: Path
    world_name: str


def family_seed(base: str, index: int) -> str:
    return f"{base}#{index}"


def render_batch(
    base: str,
    count: int,
    out_dir: Path,
    *,
    palette: str = "aurora",
    opts: RenderOptions | None = None,
    progress: bool = True,
    index_html: bool = True,
) -> list[BatchMember]:
    """Write ``count`` SVG variants of ``base`` into ``out_dir``.

    Seeds are ``base#0`` … ``base#{count-1}``. Optionally writes ``index.html``.
    """

    if count <= 0:
        raise ValueError("count must be greater than zero")
    out_dir.mkdir(parents=True, exist_ok=True)
    ro = opts or RenderOptions()
    members: list[BatchMember] = []

    for i in range(count):
        seed = family_seed(base, i)
        # Safe filename: keep alnum, dash, underscore; hash separates base/index.
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in seed)
        path = out_dir / f"{safe}.svg"
        svg = render_poster(
            seed,
            width=ro.width,
            height=ro.height,
            stars=ro.stars,
            planets=ro.planets,
            palette=palette,
            title=ro.title,
            show_title=ro.show_title,
            animate=ro.animate,
        )
        path.write_text(svg, encoding="utf-8")
        world = World.from_seed(seed, palette)
        members.append(BatchMember(seed=seed, index=i, path=path, world_name=world.name))
        if progress:
            _progress(i + 1, count)

    if index_html:
        (out_dir / "index.html").write_text(
            _batch_index_html(base, members), encoding="utf-8"
        )
    return members


def _progress(done: int, total: int) -> None:
    pct = int(100 * done / total)
    bar = "." * done
    sys.stderr.write(f"\r  batch [{bar:<{total}}] {done}/{total} ({pct}%)")
    if done >= total:
        sys.stderr.write("\n")
    sys.stderr.flush()


def _batch_index_html(base: str, members: list[BatchMember]) -> str:
    heading = escape(base)
    cards = []
    for m in members:
        rel = escape(m.path.name)
        cards.append(
            f'<figure class="cell">'
            f'<img src="{rel}" alt="{escape(m.seed)}" loading="lazy" />'
            f'<figcaption><b>{escape(m.seed)}</b>'
            f'<span>{escape(m.world_name)}</span></figcaption>'
            f"</figure>"
        )
    body = "\n".join(cards)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Starweave family · {heading}</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; background: #06070d; color: #e2e8f0;
         font-family: "Avenir Next", Inter, "Segoe UI", system-ui, sans-serif; }}
  header {{ padding: 28px 32px 8px; }}
  header h1 {{ margin: 0; font-size: 22px; letter-spacing: 1px; }}
  header p {{ margin: 4px 0 0; color: #94a3b8; font-size: 13px; }}
  .grid {{ display: grid; gap: 18px; padding: 20px 32px 48px;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }}
  .cell {{ margin: 0; background: #0b0d16; border: 1px solid #1e2330;
          border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,.35); }}
  .cell img {{ display: block; width: 100%; height: auto; background: #05060a; }}
  figcaption {{ display: flex; justify-content: space-between; align-items: baseline;
               padding: 10px 14px; font-size: 12px; gap: 8px; }}
  figcaption span {{ color: #8b95a7; font-style: italic; }}
</style>
</head>
<body>
<header>
  <h1>Starweave family · {heading}</h1>
  <p>{len(members)} seeds ({escape(base)}#0 … {escape(base)}#{len(members) - 1}).</p>
</header>
<main class="grid">
{body}
</main>
</body>
</html>
"""
