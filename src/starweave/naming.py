"""Deterministic flavour text.

Every seed gets a stable "catalogue name" (think star-chart label) and a short
caption. It's all assembled from word banks via a seeded RNG, so the same
phrase always names the same constellation — a small, repeatable myth.
"""

from __future__ import annotations

import random

_GREEK = (
    "Alpha", "Beta", "Gamma", "Delta", "Sigma", "Theta", "Omega", "Lyra",
    "Vega", "Nyx", "Astra", "Orpha", "Caelum", "Vesper",
)
_ADJECTIVES = (
    "Drifting", "Ember", "Hollow", "Silent", "Fractured", "Gilded", "Veiled",
    "Restless", "Frozen", "Luminous", "Wandering", "Sunken", "Distant",
    "Echoing", "Patient",
)
_NOUNS = (
    "Lattice", "Crown", "Spindle", "Harbor", "Verge", "Lantern", "Meridian",
    "Cradle", "Archive", "Furnace", "Atlas", "Reliquary", "Anchor", "Loom",
    "Threshold",
)
_VERBS = (
    "drifting", "unspooling", "burning low", "holding still", "turning slow",
    "breaking open", "settling", "wheeling", "listening",
)
_PLACES = (
    "the long dark", "an empty shore", "the last harbor", "a cold meridian",
    "the edge of count", "a quiet orbit", "the open verge", "nowhere in particular",
)


def constellation_name(rng: random.Random) -> str:
    """A short, star-chart-style designation, e.g. ``Sigma Lyrae`` style."""

    if rng.random() < 0.5:
        return f"{rng.choice(_GREEK)} {rng.choice(_NOUNS)}"
    return f"The {rng.choice(_ADJECTIVES)} {rng.choice(_NOUNS)}"


def caption(rng: random.Random) -> str:
    """A short poetic line, lower-cased like a footnote."""

    return f"{rng.choice(_ADJECTIVES).lower()} things, {rng.choice(_VERBS)} over {rng.choice(_PLACES)}"
