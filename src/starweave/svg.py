"""A tiny SVG document builder.

Layers don't concatenate strings by hand any more — they push elements, defs,
and CSS into an :class:`SvgDoc`, which assembles a well-formed document at the
end. Every document carries a unique id prefix so dozens of posters can be
inlined on a single gallery page without their gradient/filter ids colliding.
"""

from __future__ import annotations

import json
from html import escape


def fmt(value: float) -> str:
    """Format a number compactly: integers stay integers, floats lose noise."""

    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def esc(text: str) -> str:
    return escape(text, quote=True)


class SvgDoc:
    def __init__(self, width: int, height: int, label: str, uid: str) -> None:
        self.width = width
        self.height = height
        self.label = label
        self.uid = uid
        self.defs: list[str] = []
        self.body: list[str] = []
        self._keyframes: dict[str, str] = {}
        self._rules: list[str] = []
        self.metadata: dict[str, object] = {}
        #: Scratch space for one layer to hand data to a later layer
        #: (e.g. the starfield shares its points with the constellation layer).
        self.shared: dict[str, object] = {}

    def ref(self, name: str) -> str:
        """A document-unique id for a def, e.g. ``ref("space")``."""

        return f"{self.uid}-{name}"

    def url(self, name: str) -> str:
        return f"url(#{self.ref(name)})"

    def add_def(self, markup: str) -> None:
        self.defs.append(markup)

    def add(self, markup: str) -> None:
        self.body.append(markup)

    def add_keyframes(self, name: str, body: str) -> None:
        """Register an ``@keyframes`` block once (deduplicated by name)."""

        self._keyframes.setdefault(name, body)

    def add_rule(self, rule: str) -> None:
        self._rules.append(rule)

    @property
    def animated(self) -> bool:
        return bool(self._keyframes or self._rules)

    def _style_block(self) -> str:
        if not self.animated:
            return ""
        parts: list[str] = []
        for name, body in self._keyframes.items():
            parts.append(f"@keyframes {self.ref(name)} {{{body}}}")
        parts.extend(self._rules)
        css = "\n".join(parts)
        # CDATA keeps the CSS opaque to the XML parser.
        return f"<style>/*<![CDATA[*/\n{css}\n/*]]>*/</style>"

    def _metadata_block(self) -> str:
        if not self.metadata:
            return ""
        payload = esc(json.dumps(self.metadata, ensure_ascii=False, sort_keys=True))
        return (
            '<metadata>'
            f'<starweave xmlns="https://github.com/Sebby1770/starweave" '
            f'data-params="{payload}" />'
            '</metadata>'
        )

    def render(self) -> str:
        defs = ""
        if self.defs:
            defs = "<defs>\n" + "\n".join(self.defs) + "\n</defs>"
        chunks = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}" '
                f'role="img" aria-label="{esc(self.label)}">'
            ),
            self._metadata_block(),
            self._style_block(),
            defs,
            *self.body,
            "</svg>",
            "",
        ]
        return "\n".join(chunk for chunk in chunks if chunk)
