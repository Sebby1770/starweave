"""Lite SVG minifier — collapse inter-tag whitespace without touching text.

Careful with ``<text>`` / ``<tspan>`` content: only pure whitespace *between*
tags is removed (``>\\s+<`` → ``><``). Attribute values and character data
stay intact. The XML declaration line is preserved.
"""

from __future__ import annotations

import re

# Matches only whitespace that sits strictly between a closing ``>`` and the
# next opening ``<``. Character data that contains non-space characters is
# never matched, so title/caption strings keep their internal spaces.
_BETWEEN_TAGS = re.compile(r">\s+<")


def minify_svg(svg: str) -> str:
    """Collapse extra whitespace between SVG tags; keep text nodes intact."""

    if not svg:
        return svg
    # Preserve a trailing newline for POSIX friendliness.
    trailing_nl = svg.endswith("\n")
    # Collapse runs of blank lines / indentation between tags.
    out = _BETWEEN_TAGS.sub("><", svg.strip())
    # Collapse multiple spaces inside the document that are not inside quotes
    # is intentionally *not* done — too easy to mangle text/CSS.
    if trailing_nl or True:
        return out + "\n"
    return out  # pragma: no cover
