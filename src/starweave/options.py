"""Render options shared between the scene and its layers."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 900
DEFAULT_STARS = 300
DEFAULT_PLANETS = 4


@dataclass(frozen=True)
class RenderOptions:
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    stars: int = DEFAULT_STARS
    planets: int = DEFAULT_PLANETS
    title: str | None = None
    show_title: bool = True
    animate: bool = False
