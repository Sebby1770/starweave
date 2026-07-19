"""Render options shared between the scene and its layers."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 900
DEFAULT_STARS = 300
DEFAULT_PLANETS = 4

#: Named desktop wallpaper size presets (WxH).
WALLPAPER_PRESETS: dict[str, tuple[int, int]] = {
    "desktop": (1920, 1080),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
}


def parse_wallpaper(spec: str) -> tuple[int, int]:
    """Parse a wallpaper size: preset name (``desktop``, ``1080p``, …) or ``WxH``."""

    key = spec.strip().lower()
    if key in WALLPAPER_PRESETS:
        return WALLPAPER_PRESETS[key]
    if "x" in key:
        left, _, right = key.partition("x")
        try:
            width = int(left)
            height = int(right)
        except ValueError as exc:
            raise ValueError(
                f"invalid wallpaper size {spec!r}; use WxH or one of: "
                + ", ".join(sorted(WALLPAPER_PRESETS))
            ) from exc
        if width <= 0 or height <= 0:
            raise ValueError("wallpaper width and height must be greater than zero")
        return width, height
    raise ValueError(
        f"unknown wallpaper preset {spec!r}; use WxH or one of: "
        + ", ".join(sorted(WALLPAPER_PRESETS))
    )


@dataclass(frozen=True)
class RenderOptions:
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    stars: int = DEFAULT_STARS
    planets: int = DEFAULT_PLANETS
    title: str | None = None
    show_title: bool = True
    animate: bool = False
    #: When true, draw a corner micro-label with a short content hash.
    stamp: bool = False
