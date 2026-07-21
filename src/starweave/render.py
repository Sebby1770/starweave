"""Public rendering API.

``render_poster`` is the stable entry point: feed it a seed (and optional
overrides) and it returns a complete SVG string. Internally it expands the seed
into a :class:`~starweave.world.World` and paints the default layer stack, but
callers don't need to know that.
"""

from __future__ import annotations

from .layers import DEFAULT_LAYERS, Layer
from .minify import minify_svg
from .options import (
    DEFAULT_HEIGHT,
    DEFAULT_PLANETS,
    DEFAULT_STARS,
    DEFAULT_WIDTH,
    RenderOptions,
)
from .scene import render_scene
from .themes import Theme, apply_theme, get_theme
from .world import World

__all__ = [
    "render_poster",
    "DEFAULT_WIDTH",
    "DEFAULT_HEIGHT",
    "DEFAULT_STARS",
    "DEFAULT_PLANETS",
]


def _validate_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")


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
    animate: bool = False,
    variant: int = 0,
    stamp: bool = False,
    theme: str | Theme | None = None,
    minify: bool = False,
    layers: tuple[Layer, ...] = DEFAULT_LAYERS,
) -> str:
    """Return a deterministic SVG poster for ``seed``.

    ``palette`` may be ``"auto"`` to pick one from the seed. ``variant`` shifts
    the whole world to a different (still deterministic) draw of the same seed.
    ``animate=True`` emits a self-contained animated SVG (twinkle/drift/orbit).
    ``stamp=True`` draws a corner micro-label with a short content hash.
    ``theme`` selects a fixed palette + intensity bias (overrides ``palette``).
    ``minify=True`` collapses inter-tag whitespace in the SVG.
    """

    _validate_positive("width", width)
    _validate_positive("height", height)
    _validate_positive("stars", stars)
    _validate_positive("planets", planets)

    theme_obj: Theme | None = None
    if theme is not None:
        theme_obj = theme if isinstance(theme, Theme) else get_theme(theme)
        palette = theme_obj.palette

    world = World.from_seed(seed, palette, variant)
    if theme_obj is not None:
        apply_theme(world, theme_obj)
    opts = RenderOptions(
        width=width,
        height=height,
        stars=stars,
        planets=planets,
        title=title,
        show_title=show_title,
        animate=animate,
        stamp=stamp,
    )
    svg = render_scene(world, opts, layers)
    if minify:
        return minify_svg(svg)
    return svg
