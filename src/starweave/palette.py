from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    background: tuple[str, str]
    nebula: tuple[str, ...]
    stars: tuple[str, ...]
    planets: tuple[str, ...]
    accent: tuple[str, ...]


PALETTES: dict[str, Palette] = {
    "aurora": Palette(
        name="aurora",
        background=("#09111f", "#101a38"),
        nebula=("#2dd4bf", "#7c3aed", "#f0abfc", "#38bdf8"),
        stars=("#f8fafc", "#bfdbfe", "#ccfbf1", "#fef3c7"),
        planets=("#14b8a6", "#818cf8", "#f472b6", "#fde68a"),
        accent=("#22d3ee", "#a78bfa", "#fb7185"),
    ),
    "ember": Palette(
        name="ember",
        background=("#120b16", "#24101d"),
        nebula=("#f97316", "#ef4444", "#f59e0b", "#ec4899"),
        stars=("#fff7ed", "#fed7aa", "#fecaca", "#fef9c3"),
        planets=("#fb923c", "#f43f5e", "#facc15", "#c084fc"),
        accent=("#f97316", "#fb7185", "#fbbf24"),
    ),
    "midnight": Palette(
        name="midnight",
        background=("#050816", "#101827"),
        nebula=("#2563eb", "#4f46e5", "#0ea5e9", "#64748b"),
        stars=("#eff6ff", "#dbeafe", "#c7d2fe", "#e0f2fe"),
        planets=("#38bdf8", "#6366f1", "#94a3b8", "#a5b4fc"),
        accent=("#60a5fa", "#818cf8", "#67e8f9"),
    ),
    "solar": Palette(
        name="solar",
        background=("#08100d", "#162116"),
        nebula=("#fbbf24", "#22c55e", "#84cc16", "#f97316"),
        stars=("#fff7ed", "#ecfccb", "#fde68a", "#dcfce7"),
        planets=("#eab308", "#22c55e", "#fb923c", "#bef264"),
        accent=("#facc15", "#4ade80", "#fb923c"),
    ),
}


def get_palette(name: str) -> Palette:
    try:
        return PALETTES[name]
    except KeyError as exc:
        available = ", ".join(sorted(PALETTES))
        raise ValueError(f"Unknown palette {name!r}. Choose from: {available}") from exc

