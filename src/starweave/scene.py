"""Compose a :class:`~starweave.world.World` and a stack of layers into SVG."""

from __future__ import annotations

import hashlib

from . import __version__
from .layers import DEFAULT_LAYERS, Layer
from .options import RenderOptions
from .svg import SvgDoc
from .world import World


def _uid(world: World, opts: RenderOptions) -> str:
    material = f"{world.seed}|{opts.width}|{opts.height}|{world.palette.name}|{world.variant}"
    return hashlib.sha1(material.encode()).hexdigest()[:10]


def content_hash(world: World, opts: RenderOptions) -> str:
    """Short content hash of seed + render params (for metadata + stamp)."""

    material = (
        f"starweave|{world.seed}|{world.palette.name}|{world.variant}|"
        f"{opts.width}x{opts.height}|s{opts.stars}|p{opts.planets}|"
        f"a{int(opts.animate)}|t{int(opts.show_title)}"
    )
    return hashlib.sha256(material.encode()).hexdigest()[:10]


def build_document(
    world: World,
    opts: RenderOptions,
    layers: tuple[Layer, ...] = DEFAULT_LAYERS,
) -> SvgDoc:
    label = f"{world.seed} star poster"
    doc = SvgDoc(opts.width, opts.height, label, _uid(world, opts))
    stamp = content_hash(world, opts)
    doc.shared["stamp"] = stamp
    for layer in layers:
        if layer.applies(world):
            layer.build(world, doc, opts)
    doc.metadata = {
        "generator": f"starweave {__version__}",
        "size": [opts.width, opts.height],
        "stars": opts.stars,
        "planets": opts.planets,
        "animated": doc.animated,
        "stamp": stamp,
        "world": world.summary(),
    }
    return doc


def render_scene(
    world: World,
    opts: RenderOptions,
    layers: tuple[Layer, ...] = DEFAULT_LAYERS,
) -> str:
    return build_document(world, opts, layers).render()
