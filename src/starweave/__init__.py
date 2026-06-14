"""Starweave — deterministic generative SVG space posters.

A seed phrase expands into a :class:`~starweave.world.World`, which a stack of
:mod:`~starweave.layers` paints onto an :class:`~starweave.svg.SvgDoc`.
"""

__version__ = "0.2.0"

from .options import RenderOptions
from .render import render_poster
from .scene import build_document, render_scene
from .world import World

__all__ = [
    "render_poster",
    "render_scene",
    "build_document",
    "World",
    "RenderOptions",
    "__version__",
]
