"""Validate that an SVG carries Starweave reproducibility metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


#: Fields expected on the top-level metadata payload.
_REQUIRED_TOP = ("generator", "size", "stars", "planets", "world")
#: Fields expected inside ``world``.
_REQUIRED_WORLD = ("seed", "palette", "variant")


@dataclass
class ValidationResult:
    path: str
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    params: dict[str, Any] | None = None

    def summary(self) -> str:
        status = "ok" if self.ok else "FAIL"
        lines = [f"{self.path}: {status}"]
        for err in self.errors:
            lines.append(f"  error: {err}")
        for warn in self.warnings:
            lines.append(f"  warning: {warn}")
        if self.ok and self.params is not None:
            world = self.params.get("world") or {}
            seed = world.get("seed", "?") if isinstance(world, dict) else "?"
            gen = self.params.get("generator", "?")
            lines.append(f"  generator: {gen}")
            lines.append(f"  seed: {seed!r}")
        return "\n".join(lines)


def validate_svg_text(text: str, *, path: str = "<svg>") -> ValidationResult:
    """Check that *text* embeds a ``<starweave>`` metadata node with required fields."""

    import xml.dom.minidom as minidom

    errors: list[str] = []
    warnings: list[str] = []
    params: dict[str, Any] | None = None

    try:
        doc = minidom.parseString(text)
    except Exception as exc:  # noqa: BLE001
        return ValidationResult(path=path, ok=False, errors=[f"not well-formed XML: {exc}"])

    nodes = doc.getElementsByTagName("starweave")
    if not nodes:
        return ValidationResult(
            path=path,
            ok=False,
            errors=["missing <starweave> metadata element (not a Starweave poster?)"],
        )

    raw = nodes[0].getAttribute("data-params")
    if not raw:
        return ValidationResult(
            path=path,
            ok=False,
            errors=["<starweave> element has empty data-params attribute"],
        )

    try:
        params = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ValidationResult(
            path=path,
            ok=False,
            errors=[f"data-params is not valid JSON: {exc}"],
        )

    if not isinstance(params, dict):
        return ValidationResult(
            path=path,
            ok=False,
            errors=["data-params must be a JSON object"],
        )

    for key in _REQUIRED_TOP:
        if key not in params:
            errors.append(f"missing top-level field {key!r}")

    world = params.get("world")
    if world is None:
        errors.append("missing top-level field 'world'")
    elif not isinstance(world, dict):
        errors.append("'world' must be an object")
    else:
        for key in _REQUIRED_WORLD:
            if key not in world:
                errors.append(f"missing world field {key!r}")

    size = params.get("size")
    if size is not None:
        if not (isinstance(size, list) and len(size) == 2):
            errors.append("'size' must be a [width, height] pair")
        elif not all(isinstance(n, (int, float)) and n > 0 for n in size):
            errors.append("'size' values must be positive numbers")

    # Optional but useful for reproducibility.
    if "stamp" not in params:
        warnings.append("no content-hash 'stamp' field (pre-0.5 poster?)")
    if "animated" not in params:
        warnings.append("no 'animated' field")

    return ValidationResult(
        path=path,
        ok=not errors,
        errors=errors,
        warnings=warnings,
        params=params,
    )


def validate_svg_file(path: str | Path) -> ValidationResult:
    """Read *path* and validate its Starweave metadata."""

    p = Path(path)
    if not p.is_file():
        return ValidationResult(path=str(p), ok=False, errors=[f"file not found: {p}"])
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        return ValidationResult(path=str(p), ok=False, errors=[f"could not read file: {exc}"])
    return validate_svg_text(text, path=str(p))
