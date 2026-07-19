"""Tests for the 0.4.0 features: blackhole, batch, dump-world, palettes, composability."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import xml.dom.minidom as minidom
from pathlib import Path

from starweave.cli import main
from starweave.layers import DEFAULT_LAYERS, Blackhole, Layer
from starweave.options import RenderOptions
from starweave.palette import PALETTES
from starweave.palette_preview import palette_preview_svg
from starweave.render import render_poster
from starweave.scene import render_scene
from starweave.world import World


def parse(svg: str) -> minidom.Document:
    return minidom.parseString(svg)


def _strip_metadata(svg: str) -> str:
    """Drop the reproducibility <metadata> block so paint can be compared."""

    start = svg.find("<metadata")
    if start < 0:
        return svg
    end = svg.find("</metadata>", start)
    if end < 0:
        return svg
    return svg[:start] + svg[end + len("</metadata>") :]


def run_cli(args: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class ComposabilityTests(unittest.TestCase):
    """Adding/removing a layer must not perturb other named RNG streams."""

    def test_blackhole_present_absent_leaves_other_layers_unchanged(self) -> None:
        world = World.from_seed("composability probe", "aurora")
        # Force blackhole off, capture stars stream first values + full SVG of stars-only stack.
        world.features["blackhole"] = False
        # Capture independent stream draws for non-blackhole layers.
        probes = ("stars", "nebula", "planets", "orbits", "background")
        draws_off = {name: world.stream(name).random() for name in probes}

        world_on = World.from_seed("composability probe", "aurora")
        world_on.features["blackhole"] = True
        draws_on = {name: world_on.stream(name).random() for name in probes}
        self.assertEqual(draws_off, draws_on)

        # Geometry of the starfield layer is identical when blackhole is forced
        # (metadata may list different features — strip it before comparing paint).
        opts = RenderOptions(width=400, height=300, stars=40, planets=2)
        keep = ("background", "stars")
        layers = tuple(L for L in DEFAULT_LAYERS if L.name in keep)
        svg_a = render_scene(world, opts, layers)
        svg_b = render_scene(world_on, opts, layers)
        self.assertEqual(_strip_metadata(svg_a), _strip_metadata(svg_b))

    def test_supernova_stream_independent(self) -> None:
        w = World.from_seed("stream island", "ember")
        a = w.stream("supernova").random()
        b = w.stream("stars").random()
        c = w.stream("supernova").random()
        self.assertEqual(a, c)
        self.assertNotEqual(a, b)

    def test_nebula_clusters_does_not_change_nebula_stream(self) -> None:
        w0 = World.from_seed("cluster probe", "noir")
        w0.features["nebula_clusters"] = False
        n0 = w0.stream("nebula").random()

        w1 = World.from_seed("cluster probe", "noir")
        w1.features["nebula_clusters"] = True
        n1 = w1.stream("nebula").random()
        self.assertEqual(n0, n1)


class BlackholeTests(unittest.TestCase):
    def test_blackhole_deterministic(self) -> None:
        world = World.from_seed("event horizon", "synthwave")
        world.features["blackhole"] = True
        opts = RenderOptions(width=700, height=500, stars=80)
        svg = render_scene(world, opts)
        parse(svg)
        again = World.from_seed("event horizon", "synthwave")
        again.features["blackhole"] = True
        self.assertEqual(svg, render_scene(again, opts))
        # Horizon silhouette is pure black.
        self.assertIn('fill="#000000"', svg)

    def test_blackhole_layer_name_registered(self) -> None:
        names = {layer.name for layer in DEFAULT_LAYERS}
        self.assertIn("blackhole", names)
        self.assertIn("supernova", names)
        self.assertIn("nebula_clusters", names)
        self.assertIsInstance(Blackhole(), Layer)

    def test_without_blackhole_flag_skips_layer(self) -> None:
        world = World.from_seed("no hole", "aurora")
        world.features["blackhole"] = False
        only_bh = (Blackhole(),)
        svg = render_scene(world, RenderOptions(width=200, height=200), only_bh)
        # Empty-ish body: no black fill from the layer.
        self.assertNotIn('fill="#000000"', svg)


class BatchTests(unittest.TestCase):
    def test_batch_writes_n_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "family"
            code, stdout, _ = run_cli([
                "batch", "deep field", "--count", "5", "--out", str(out),
                "--width", "320", "--height", "200", "--stars", "20", "--quiet",
            ])
            self.assertEqual(code, 0)
            svgs = sorted(out.glob("*.svg"))
            self.assertEqual(len(svgs), 5)
            self.assertTrue((out / "index.html").exists())
            self.assertIn("Wrote 5", stdout)
            # Seeds are base#0 … base#4
            text = svgs[0].read_text(encoding="utf-8")
            self.assertTrue(
                any(f"deep field#{i}" in text or f"deep field#{i}" in svgs[i].read_text(encoding="utf-8")
                    for i in range(5))
            )

    def test_batch_members_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "fam"
            self.assertEqual(run_cli([
                "batch", "alpha", "--count", "3", "--out", str(out),
                "--width", "240", "--height", "160", "--stars", "15", "--quiet",
            ])[0], 0)
            bodies = [p.read_text(encoding="utf-8") for p in sorted(out.glob("*.svg"))]
            self.assertEqual(len(set(bodies)), 3)


class DumpWorldTests(unittest.TestCase):
    def test_dump_world_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            code, _, _ = run_cli([
                "dump probe", "--dump-world", str(path), "--palette", "ember",
            ])
            self.assertEqual(code, 0)
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in (
                "seed", "palette", "variant", "mood", "name", "myth",
                "turbulence", "brightness", "density", "reading", "features",
            ):
                self.assertIn(key, data)
            self.assertEqual(data["seed"], "dump probe")
            self.assertEqual(data["palette"], "ember")
            self.assertIsInstance(data["features"], list)

    def test_dump_world_matches_describe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "w.json"
            run_cli(["same seed", "--dump-world", str(path), "--palette", "glacier"])
            dumped = json.loads(path.read_text(encoding="utf-8"))
            expected = World.from_seed("same seed", "glacier").summary()
            self.assertEqual(dumped, expected)


class PalettePreviewTests(unittest.TestCase):
    def test_palette_preview_non_empty(self) -> None:
        svg = palette_preview_svg()
        self.assertTrue(svg)
        self.assertGreater(len(svg), 500)
        self.assertIn("<svg", svg)
        parse(svg)
        for name in PALETTES:
            self.assertIn(name, svg)

    def test_cli_palette_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "palettes.svg"
            code, stdout, _ = run_cli(["palette-preview", "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 400)
            self.assertIn("palettes", stdout.lower())


class AsciiWidthTests(unittest.TestCase):
    def test_ascii_width_flag(self) -> None:
        code, out, _ = run_cli(["seed", "--ascii", "--ascii-width", "48"])
        self.assertEqual(code, 0)
        lines = out.strip().split("\n")
        grid = lines[1:-1]
        self.assertTrue(all(len(row) == 48 for row in grid))

    def test_ascii_ramp_is_dense(self) -> None:
        from starweave.ascii_art import _RAMP

        self.assertGreaterEqual(len(_RAMP), 20)


class ReproduceHardeningTests(unittest.TestCase):
    def test_reproduce_cli_roundtrip(self) -> None:
        original = render_poster(
            "repro harden",
            palette="verdant",
            width=480,
            height=300,
            stars=60,
            planets=2,
            variant=1,
        )
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / "orig.svg"
            dst = Path(directory) / "copy.svg"
            src.write_text(original, encoding="utf-8")
            code, _, _ = run_cli(["--reproduce", str(src), "--out", str(dst)])
            self.assertEqual(code, 0)
            self.assertEqual(dst.read_text(encoding="utf-8"), original)

    def test_reproduce_missing_metadata_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bare.svg"
            bad.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
                encoding="utf-8",
            )
            code, _, err = run_cli(["--reproduce", str(bad), "--out", str(Path(directory) / "x.svg")])
            self.assertEqual(code, 2)
            self.assertIn("no reproducibility metadata", err)


class ListLayersTests(unittest.TestCase):
    def test_list_layers_includes_new(self) -> None:
        code, out, _ = run_cli(["--list-layers"])
        self.assertEqual(code, 0)
        self.assertIn("blackhole", out)
        self.assertIn("supernova", out)
        self.assertIn("nebula_clusters", out)


if __name__ == "__main__":
    unittest.main()
