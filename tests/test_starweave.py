"""Rendering + CLI tests, including the original public-contract guarantees."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import xml.dom.minidom as minidom
from pathlib import Path

from starweave.cli import main
from starweave.layers import DEFAULT_LAYERS
from starweave.palette import PALETTES
from starweave.render import render_poster


def parse(svg: str) -> minidom.Document:
    return minidom.parseString(svg)


def run_cli(args: list[str]) -> int:
    """Run the CLI with stdout/stderr captured, returning the exit code."""

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return main(args)


class PublicContractTests(unittest.TestCase):
    """The behaviours other tools / earlier versions relied on."""

    def test_same_seed_renders_same_svg(self) -> None:
        first = render_poster("orbit coffee", width=640, height=360, stars=40, planets=2)
        second = render_poster("orbit coffee", width=640, height=360, stars=40, planets=2)
        self.assertEqual(first, second)

    def test_different_seed_changes_svg(self) -> None:
        first = render_poster("orbit coffee", width=640, height=360, stars=40, planets=2)
        second = render_poster("midnight compiler", width=640, height=360, stars=40, planets=2)
        self.assertNotEqual(first, second)

    def test_svg_contains_accessible_label_and_title(self) -> None:
        svg = render_poster("Sebby's launch", width=640, height=360, stars=40, planets=2)
        self.assertIn("<svg", svg)
        self.assertIn("Sebby&#x27;s launch star poster", svg)
        self.assertIn("seed: Sebby&#x27;s launch", svg)

    def test_rejects_invalid_dimensions(self) -> None:
        for kwargs in (dict(width=0), dict(height=0), dict(stars=0), dict(planets=0)):
            with self.assertRaises(ValueError):
                render_poster("bad", **kwargs)


class WellFormednessTests(unittest.TestCase):
    def test_every_palette_is_well_formed(self) -> None:
        for name in PALETTES:
            svg = render_poster("palette probe", palette=name, width=400, height=300, stars=60)
            parse(svg)  # raises on malformed XML

    def test_static_and_animated_and_auto_are_well_formed(self) -> None:
        for kwargs in (dict(), dict(animate=True), dict(palette="auto"), dict(variant=3)):
            svg = render_poster("xml probe", width=500, height=320, stars=80, **kwargs)
            parse(svg)

    def test_animated_emits_style_static_does_not(self) -> None:
        animated = render_poster("twinkle", width=500, height=320, animate=True)
        static = render_poster("twinkle", width=500, height=320, animate=False)
        self.assertIn("@keyframes", animated)
        self.assertIn("<style>", animated)
        self.assertNotIn("@keyframes", static)

    def test_reproduce_from_metadata_is_byte_identical(self) -> None:
        original = render_poster(
            "round trip", palette="auto", width=560, height=360,
            stars=120, planets=4, animate=True, variant=2,
        )
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / "orig.svg"
            dst = Path(directory) / "repro.svg"
            src.write_text(original, encoding="utf-8")
            self.assertEqual(run_cli(["--reproduce", str(src), "--out", str(dst)]), 0)
            self.assertEqual(dst.read_text(encoding="utf-8"), original)

    def test_metadata_roundtrips(self) -> None:
        svg = render_poster("metadata", palette="ember", width=500, height=320)
        doc = parse(svg)
        node = doc.getElementsByTagName("starweave")[0]
        params = json.loads(node.getAttribute("data-params"))
        self.assertEqual(params["world"]["seed"], "metadata")
        self.assertEqual(params["world"]["palette"], "ember")
        self.assertIn("generator", params)


class VariantAndLayerTests(unittest.TestCase):
    def test_variant_changes_output(self) -> None:
        base = render_poster("variant probe", variant=0)
        other = render_poster("variant probe", variant=1)
        self.assertNotEqual(base, other)

    def test_dropping_a_layer_changes_output(self) -> None:
        full = render_poster("layer probe", width=500, height=320)
        keep = tuple(layer for layer in DEFAULT_LAYERS if layer.name != "constellations")
        trimmed = render_poster("layer probe", width=500, height=320, layers=keep)
        self.assertNotEqual(full, trimmed)
        self.assertLess(len(trimmed), len(full))

    def test_attractor_layer_is_well_formed_and_deterministic(self) -> None:
        from starweave.options import RenderOptions
        from starweave.scene import render_scene
        from starweave.world import World

        world = World.from_seed("chaos theory", "synthwave")
        world.features["attractor"] = True
        svg = render_scene(world, RenderOptions(width=700, height=500))
        parse(svg)
        self.assertIn("<path", svg)
        again = World.from_seed("chaos theory", "synthwave")
        again.features["attractor"] = True
        self.assertEqual(svg, render_scene(again, RenderOptions(width=700, height=500)))

    def test_filament_layer_grows_and_is_well_formed(self) -> None:
        from starweave.options import RenderOptions
        from starweave.scene import render_scene
        from starweave.world import World

        world = World.from_seed("emergence", "aurora")
        world.features["filament"] = True  # force the emergent layer on
        svg = render_scene(world, RenderOptions(width=800, height=520))
        parse(svg)
        self.assertIn("<path", svg)
        again = World.from_seed("emergence", "aurora")
        again.features["filament"] = True
        self.assertEqual(svg, render_scene(again, RenderOptions(width=800, height=520)))

    def test_title_layer_can_be_hidden(self) -> None:
        with_title = render_poster("title probe")
        without = render_poster("title probe", show_title=False)
        self.assertIn("seed: title probe", with_title)
        self.assertNotIn("seed: title probe", without)


class CliTests(unittest.TestCase):
    def test_cli_writes_svg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "poster.svg"
            result = run_cli(["cli seed", "--out", str(output), "--width", "320",
                              "--height", "220", "--stars", "20", "--planets", "1"])
            self.assertEqual(result, 0)
            self.assertTrue(output.exists())
            self.assertIn("cli seed", output.read_text(encoding="utf-8"))

    def test_cli_gallery_writes_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "g.html"
            result = run_cli(["seed", "--gallery", "4", "--out", str(output)])
            self.assertEqual(result, 0)
            html = output.read_text(encoding="utf-8")
            self.assertEqual(html.count("<figure"), 4)
            self.assertIn("<!doctype html>", html)
            # Inline SVG must not carry an XML prolog.
            self.assertNotIn("<?xml", html)

    def test_cli_list_and_describe_succeed(self) -> None:
        self.assertEqual(run_cli(["--list-palettes"]), 0)
        self.assertEqual(run_cli(["--list-layers"]), 0)
        self.assertEqual(run_cli(["seed", "--describe"]), 0)

    def test_cli_unknown_layer_is_an_error(self) -> None:
        with self.assertRaises(SystemExit):
            run_cli(["seed", "--only", "background,not-a-layer"])

    def test_ascii_is_deterministic_and_rectangular(self) -> None:
        from starweave.ascii_art import ascii_poster
        from starweave.world import World

        world = World.from_seed("ascii sky", "aurora")
        art = ascii_poster(world, cols=60)
        self.assertEqual(art, ascii_poster(World.from_seed("ascii sky", "aurora"), cols=60))
        lines = art.split("\n")
        self.assertIn("STARWEAVE", lines[0])
        # Every grid row (between header and the seed footer) is exactly cols wide.
        grid = lines[1:-1]
        self.assertTrue(all(len(row) == 60 for row in grid))

    def test_cli_ascii_runs(self) -> None:
        self.assertEqual(run_cli(["seed", "--ascii", "--cols", "40"]), 0)

    def test_cli_explorer_writes_standalone_html(self) -> None:
        from starweave.webexport import explorer_html

        html = explorer_html()
        self.assertIn("<!doctype html>", html)
        self.assertIn("starweave", html)
        self.assertIn("<script>", html)
        self.assertIn("AudioContext", html)  # the in-browser sonification
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "explorer.html"
            self.assertEqual(run_cli(["seed", "--explorer", "--out", str(output)]), 0)
            self.assertTrue(output.exists())
            self.assertGreater(len(output.read_text(encoding="utf-8")), 5000)


if __name__ == "__main__":
    unittest.main()
