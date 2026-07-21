"""Starweave — deterministic generative SVG space posters.

A seed phrase expands into a :class:`~starweave.world.World`, which a stack of
:mod:`~starweave.layers` paints onto an :class:`~starweave.svg.SvgDoc`.
"""

__version__ = "0.6.0"

from .options import RenderOptions, parse_wallpaper
from .render import render_poster
from .scene import build_document, content_hash, render_scene
from .themes import THEMES, apply_theme, get_theme
from .world import World, diff_worlds, format_diff

__all__ = [
    "render_poster",
    "render_scene",
    "build_document",
    "content_hash",
    "World",
    "RenderOptions",
    "parse_wallpaper",
    "diff_worlds",
    "format_diff",
    "THEMES",
    "get_theme",
    "apply_theme",
    "__version__",
]
