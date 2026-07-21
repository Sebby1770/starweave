"""Color palettes for Starweave posters.

A :class:`Palette` is a small, frozen bundle of colors. Layers pull from it by
role (``background``, ``nebula``, ``stars`` ...) so a single palette swap
restyles the whole poster without touching any geometry.

``"auto"`` is special: it deterministically chooses a real palette from the
seed, so ``--palette auto`` gives every phrase a stable signature color.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    background: tuple[str, str]
    nebula: tuple[str, ...]
    stars: tuple[str, ...]
    planets: tuple[str, ...]
    accent: tuple[str, ...]
    #: Mood biases the generator (density, turbulence). See ``world.py``.
    mood: str = "balanced"


PALETTES: dict[str, Palette] = {
    "aurora": Palette(
        name="aurora",
        background=("#09111f", "#101a38"),
        nebula=("#2dd4bf", "#7c3aed", "#f0abfc", "#38bdf8"),
        stars=("#f8fafc", "#bfdbfe", "#ccfbf1", "#fef3c7"),
        planets=("#14b8a6", "#818cf8", "#f472b6", "#fde68a"),
        accent=("#22d3ee", "#a78bfa", "#fb7185"),
        mood="serene",
    ),
    "ember": Palette(
        name="ember",
        background=("#120b16", "#24101d"),
        nebula=("#f97316", "#ef4444", "#f59e0b", "#ec4899"),
        stars=("#fff7ed", "#fed7aa", "#fecaca", "#fef9c3"),
        planets=("#fb923c", "#f43f5e", "#facc15", "#c084fc"),
        accent=("#f97316", "#fb7185", "#fbbf24"),
        mood="turbulent",
    ),
    "midnight": Palette(
        name="midnight",
        background=("#050816", "#101827"),
        nebula=("#2563eb", "#4f46e5", "#0ea5e9", "#64748b"),
        stars=("#eff6ff", "#dbeafe", "#c7d2fe", "#e0f2fe"),
        planets=("#38bdf8", "#6366f1", "#94a3b8", "#a5b4fc"),
        accent=("#60a5fa", "#818cf8", "#67e8f9"),
        mood="glacial",
    ),
    "solar": Palette(
        name="solar",
        background=("#08100d", "#162116"),
        nebula=("#fbbf24", "#22c55e", "#84cc16", "#f97316"),
        stars=("#fff7ed", "#ecfccb", "#fde68a", "#dcfce7"),
        planets=("#eab308", "#22c55e", "#fb923c", "#bef264"),
        accent=("#facc15", "#4ade80", "#fb923c"),
        mood="radiant",
    ),
    "rose": Palette(
        name="rose",
        background=("#1a0712", "#2c0d22"),
        nebula=("#fb7185", "#e879f9", "#f0abfc", "#fda4af"),
        stars=("#fff1f2", "#ffe4e6", "#fae8ff", "#fce7f3"),
        planets=("#f43f5e", "#d946ef", "#fb7185", "#f9a8d4"),
        accent=("#fb7185", "#e879f9", "#fda4af"),
        mood="serene",
    ),
    "noir": Palette(
        name="noir",
        background=("#0a0a0b", "#16181d"),
        nebula=("#334155", "#475569", "#1e293b", "#64748b"),
        stars=("#f8fafc", "#e2e8f0", "#cbd5e1", "#94a3b8"),
        planets=("#e2e8f0", "#94a3b8", "#cbd5e1", "#64748b"),
        accent=("#e2e8f0", "#94a3b8", "#f8fafc"),
        mood="glacial",
    ),
    "synthwave": Palette(
        name="synthwave",
        background=("#170b2e", "#2a0b3d"),
        nebula=("#f000b8", "#7c3aed", "#22d3ee", "#fb7185"),
        stars=("#fdf4ff", "#c4b5fd", "#a5f3fc", "#fbcfe8"),
        planets=("#f000b8", "#22d3ee", "#a855f7", "#fde047"),
        accent=("#f000b8", "#22d3ee", "#fde047"),
        mood="turbulent",
    ),
    "glacier": Palette(
        name="glacier",
        background=("#04141c", "#082630"),
        nebula=("#22d3ee", "#38bdf8", "#5eead4", "#a5f3fc"),
        stars=("#ecfeff", "#cffafe", "#e0f2fe", "#f0fdfa"),
        planets=("#06b6d4", "#0ea5e9", "#2dd4bf", "#7dd3fc"),
        accent=("#22d3ee", "#5eead4", "#7dd3fc"),
        mood="glacial",
    ),
    "verdant": Palette(
        name="verdant",
        background=("#04140d", "#0a2417"),
        nebula=("#22c55e", "#10b981", "#84cc16", "#34d399"),
        stars=("#f0fdf4", "#dcfce7", "#ecfccb", "#d1fae5"),
        planets=("#16a34a", "#10b981", "#65a30d", "#4ade80"),
        accent=("#4ade80", "#a3e635", "#34d399"),
        mood="serene",
    ),
    "gilded": Palette(
        name="gilded",
        background=("#16120a", "#241a0c"),
        nebula=("#f59e0b", "#d97706", "#fbbf24", "#b45309"),
        stars=("#fffbeb", "#fef3c7", "#fde68a", "#fef9c3"),
        planets=("#eab308", "#f59e0b", "#d97706", "#fcd34d"),
        accent=("#fbbf24", "#fcd34d", "#f59e0b"),
        mood="radiant",
    ),
    # Okabe–Ito inspired colourblind-safe set (orange / sky / bluish-green /
    # yellow / blue / vermillion / reddish-purple) on a deep navy ground.
    "colorblind": Palette(
        name="colorblind",
        background=("#0b1020", "#1a1f36"),
        nebula=("#E69F00", "#56B4E9", "#009E73", "#CC79A7"),
        stars=("#F0E442", "#FFFFFF", "#56B4E9", "#E69F00"),
        planets=("#0072B2", "#D55E00", "#009E73", "#CC79A7"),
        accent=("#E69F00", "#56B4E9", "#D55E00"),
        mood="balanced",
    ),
}

#: Alias accepted on the CLI; resolves to the ``colorblind`` palette entry.
_PALETTE_ALIASES: dict[str, str] = {
    "okabe-ito": "colorblind",
    "okabe_ito": "colorblind",
}

#: Palette names a user can pick on the CLI, plus the special ``auto`` token.
CHOICES: tuple[str, ...] = (
    tuple(sorted(PALETTES)) + ("auto", "okabe-ito")
)


def resolve_palette_name(name: str, seed: str) -> str:
    """Resolve a requested palette name, expanding ``auto`` / aliases from the seed."""

    if name in _PALETTE_ALIASES:
        return _PALETTE_ALIASES[name]
    if name != "auto":
        return name
    digest = hashlib.sha256(f"starweave-palette|{seed}".encode()).digest()
    # Auto only picks among "real" named palettes (not aliases).
    names = sorted(PALETTES)
    return names[digest[0] % len(names)]


def get_palette(name: str, seed: str = "") -> Palette:
    """Look up a palette by name. ``auto`` / aliases are resolved first."""

    resolved = resolve_palette_name(name, seed)
    try:
        return PALETTES[resolved]
    except KeyError as exc:
        available = ", ".join(sorted(PALETTES))
        raise ValueError(
            f"Unknown palette {name!r}. Choose from: {available}, auto, okabe-ito"
        ) from exc


def _lerp_hex(c1: str, c2: str, t: float) -> str:
    a, b = c1.lstrip("#"), c2.lstrip("#")
    channels = (
        round(int(a[i : i + 2], 16) + (int(b[i : i + 2], 16) - int(a[i : i + 2], 16)) * t)
        for i in (0, 2, 4)
    )
    return "#" + "".join(f"{max(0, min(255, c)):02x}" for c in channels)


def _lerp_tuple(t1: tuple[str, ...], t2: tuple[str, ...], t: float) -> tuple[str, ...]:
    return tuple(_lerp_hex(t1[i], t2[i], t) for i in range(min(len(t1), len(t2))))


def blend_palette(a: Palette, b: Palette, t: float) -> Palette:
    """Interpolate two palettes channel-by-channel. ``t`` in [0, 1]."""

    return Palette(
        name=f"{a.name}~{b.name}",
        background=tuple(_lerp_tuple(a.background, b.background, t)),  # type: ignore[arg-type]
        nebula=_lerp_tuple(a.nebula, b.nebula, t),
        stars=_lerp_tuple(a.stars, b.stars, t),
        planets=_lerp_tuple(a.planets, b.planets, t),
        accent=_lerp_tuple(a.accent, b.accent, t),
        mood=a.mood if t < 0.5 else b.mood,
    )
