"""Theme packs — fixed palette + intensity bias for a signature look.

Themes are coarser than palettes: they lock a palette *and* nudge the world
knobs (turbulence / brightness / density) so a poster leans noir, bioluminescent,
ember-hot, or icy without the user fine-tuning each flag.

Mapping (``--theme NAME``):

===========  ============  ===========================================
Theme        Palette       Intensity bias (multipliers)
===========  ============  ===========================================
``noir``     ``noir``      turbulence×0.70, brightness×0.75, density×0.85
``biolume``  ``verdant``   turbulence×0.55, brightness×1.25, density×1.05
``ember``    ``ember``     turbulence×1.40, brightness×1.15, density×1.10
``ice``      ``glacier``   turbulence×0.45, brightness×0.90, density×0.75
===========  ============  ===========================================

``--theme`` overrides ``--palette`` when both are given.
"""

from __future__ import annotations

from dataclasses import dataclass

from .world import World, _clamp


@dataclass(frozen=True)
class Theme:
    name: str
    palette: str
    #: Multipliers applied to derived knobs after World.from_seed.
    turbulence: float = 1.0
    brightness: float = 1.0
    density: float = 1.0
    description: str = ""


THEMES: dict[str, Theme] = {
    "noir": Theme(
        name="noir",
        palette="noir",
        turbulence=0.70,
        brightness=0.75,
        density=0.85,
        description="monochrome slate, muted and sparse",
    ),
    "biolume": Theme(
        name="biolume",
        palette="verdant",
        turbulence=0.55,
        brightness=1.25,
        density=1.05,
        description="deep-sea glow, bright verdant bioluminescence",
    ),
    "ember": Theme(
        name="ember",
        palette="ember",
        turbulence=1.40,
        brightness=1.15,
        density=1.10,
        description="hot turbulent fire, dense and bright",
    ),
    "ice": Theme(
        name="ice",
        palette="glacier",
        turbulence=0.45,
        brightness=0.90,
        density=0.75,
        description="cold glacial calm, sparse and crystalline",
    ),
}

THEME_CHOICES: tuple[str, ...] = tuple(sorted(THEMES))


def get_theme(name: str) -> Theme:
    key = name.strip().lower()
    try:
        return THEMES[key]
    except KeyError as exc:
        available = ", ".join(THEME_CHOICES)
        raise ValueError(f"Unknown theme {name!r}. Choose from: {available}") from exc


def apply_theme(world: World, theme: Theme) -> World:
    """Mutate *world* knobs by the theme's intensity bias; return the same world."""

    world.turbulence = _clamp(world.turbulence * theme.turbulence)
    world.brightness = _clamp(world.brightness * theme.brightness)
    world.density = _clamp(world.density * theme.density)
    return world
