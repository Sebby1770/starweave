"""Public rendering API.

``render_poster`` is the stable entry point: feed it a seed (and optional
overrides) and it returns a complete SVG string. Internally it expands the seed
into a :class:`~starweave.world.World` and paints the default layer stack, but
callers don't need to know that.
"""

from __future__ import annotations

from .layers import DEFAULT_LAYERS, Layer
from .options import (
    DEFAULT_HEIGHT,
    DEFAULT_PLANETS,
    DEFAULT_STARS,
    DEFAULT_WIDTH,
    RenderOptions,
)
from .scene import render_scene
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
    layers: tuple[Layer, ...] = DEFAULT_LAYERS,
) -> str:
    """Return a deterministic SVG poster for ``seed``.

    ``palette`` may be ``"auto"`` to pick one from the seed. ``variant`` shifts
    the whole world to a different (still deterministic) draw of the same seed.
    ``animate=True`` emits a self-contained animated SVG (twinkle/drift/orbit).
    """

    _validate_positive("width", width)
    _validate_positive("height", height)
    _validate_positive("stars", stars)
    _validate_positive("planets", planets)

    world = World.from_seed(seed, palette, variant)
    opts = RenderOptions(
        width=width,
        height=height,
        stars=stars,
        planets=planets,
        title=title,
        show_title=show_title,
        animate=animate,
    )
    return render_scene(world, opts, layers)
