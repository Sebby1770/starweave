"""The deterministic *world* a seed expands into.

This is the conceptual core of Starweave. A seed phrase doesn't draw a poster
directly — it expands into a :class:`World`: a small bundle of facts (mood,
intensity knobs, which celestial features exist, a catalogue name) plus a
factory of independent random streams.

Two properties matter:

* **Reproducible** — same ``(seed, palette, variant)`` always yields the same
  world, hence the same poster.
* **Composable** — each layer pulls its own named stream (``world.stream("stars")``),
  so adding, removing, or reordering layers never disturbs another layer's
  randomness. The galaxy looks identical whether or not comets are drawn.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from . import naming
from .palette import Palette, blend_palette, get_palette, resolve_palette_name


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

# How each palette mood biases the generator. Values multiply the base roll.
_MOOD_BIAS = {
    "serene": dict(turbulence=0.6, brightness=1.0, density=0.9),
    "turbulent": dict(turbulence=1.5, brightness=1.1, density=1.2),
    "glacial": dict(turbulence=0.5, brightness=0.85, density=0.8),
    "radiant": dict(turbulence=1.1, brightness=1.3, density=1.05),
    "balanced": dict(turbulence=1.0, brightness=1.0, density=1.0),
}

# Optional celestial features and the odds each one shows up in a world.
# Order is fixed so new entries appended at the end never reshuffle older rolls
# (composability of the features stream across releases).
_FEATURE_ODDS = {
    "galaxy": 0.42,
    "comets": 0.55,
    "moon": 0.5,
    "aurora": 0.38,
    "horizon": 0.3,
    "rings": 0.7,
    "grid": 0.25,
    "filament": 0.4,
    "attractor": 0.35,
    "blackhole": 0.22,
    "supernova": 0.28,
    "nebula_clusters": 0.32,
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


_VOWELS = frozenset("aeiou")


def semantics(text: str) -> dict[str, float]:
    """Read meaning out of the *shape* of the phrase — no ML, just letters.

    Vowel-rich phrases read as soft and bright; consonant-heavy ones as
    turbulent; longer words pack the sky denser. These signals (all 0..1) are
    blended into the world's knobs so the words genuinely steer the art rather
    than just hashing into noise.
    """

    lowered = text.lower()
    letters = [c for c in lowered if c.isalpha()]
    n = len(letters) or 1
    vowel_ratio = sum(1 for c in letters if c in _VOWELS) / n
    words = [w for w in lowered.split() if w]
    avg_word = (sum(len(w) for w in words) / len(words)) if words else float(len(letters))
    return {
        "vowel_ratio": vowel_ratio,
        "avg_word": avg_word,
        "brightness": _clamp(0.35 + vowel_ratio),
        "turbulence": _clamp(0.25 + (1.0 - vowel_ratio) * 0.85),
        "density": _clamp(0.35 + min(avg_word, 9.0) / 12.0),
    }


@dataclass
class World:
    seed: str
    palette: Palette
    variant: int = 0
    _root: bytes = field(default=b"", repr=False)

    # Derived knobs (0..1).
    turbulence: float = 0.0
    brightness: float = 0.0
    density: float = 0.0

    features: dict[str, bool] = field(default_factory=dict)
    name: str = ""
    caption: str = ""
    myth: str = ""
    reading: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_seed(cls, seed: str, palette_name: str = "aurora", variant: int = 0) -> "World":
        resolved = resolve_palette_name(palette_name, seed)
        palette = get_palette(resolved, seed)
        root = hashlib.sha256(
            f"starweave|v2|{seed}|{resolved}|{variant}".encode()
        ).digest()
        world = cls(seed=seed, palette=palette, variant=variant, _root=root)
        world._derive()
        return world

    def stream(self, name: str) -> random.Random:
        """An independent, reproducible RNG for a named concern."""

        digest = hashlib.sha256(self._root + b"|" + name.encode()).digest()
        return random.Random(int.from_bytes(digest[:16], "big"))

    def _derive(self) -> None:
        bias = _MOOD_BIAS.get(self.palette.mood, _MOOD_BIAS["balanced"])
        sem = semantics(self.seed)
        roll = self.stream("knobs")

        # Each knob is part seeded-chance (with the palette's mood bias) and part
        # meaning read from the phrase, so the words you choose actually show up.
        def mix(roll_value: float, key: str) -> float:
            base = _clamp(roll_value * bias[key])
            return _clamp(0.45 * base + 0.55 * sem[key])

        self.turbulence = mix(roll.uniform(0.25, 0.85), "turbulence")
        self.brightness = mix(roll.uniform(0.55, 0.95), "brightness")
        self.density = mix(roll.uniform(0.5, 0.95), "density")
        self.reading = {
            "vowel_ratio": round(sem["vowel_ratio"], 3),
            "avg_word": round(sem["avg_word"], 2),
        }

        feature_roll = self.stream("features")
        self.features = {
            name: feature_roll.random() < odds for name, odds in _FEATURE_ODDS.items()
        }

        name_rng = self.stream("name")
        self.name = naming.constellation_name(name_rng)
        self.caption = naming.caption(name_rng)
        self.myth = naming.myth(self.stream("myth"), self.name)

    @classmethod
    def blended(cls, a: "World", b: "World", t: float) -> "World":
        """A world partway between two seeds — a point on the geodesic A→B.

        Structure (RNG streams, feature set, and ``density`` which sets element
        *counts*) is held from ``a`` so nothing pops in or out along the path;
        only the continuous mood knobs and the palette interpolate. The result:
        the same sky, smoothly shifting its colour and temperament from A to B.
        """

        return cls(
            seed=a.seed,
            palette=blend_palette(a.palette, b.palette, t),
            variant=a.variant,
            _root=a._root,
            turbulence=_lerp(a.turbulence, b.turbulence, t),
            brightness=_lerp(a.brightness, b.brightness, t),
            density=a.density,  # held: keeps element counts stable across frames
            features=dict(a.features),
            name=f"{a.name} → {b.name}",
            caption=a.caption,
        )

    def has(self, feature: str) -> bool:
        return self.features.get(feature, False)

    def summary(self) -> dict[str, object]:
        """A compact, JSON-friendly description (used in poster metadata)."""

        return {
            "seed": self.seed,
            "palette": self.palette.name,
            "variant": self.variant,
            "mood": self.palette.mood,
            "name": self.name,
            "myth": self.myth,
            "turbulence": round(self.turbulence, 3),
            "brightness": round(self.brightness, 3),
            "density": round(self.density, 3),
            "reading": self.reading,
            "features": [k for k, v in self.features.items() if v],
        }
