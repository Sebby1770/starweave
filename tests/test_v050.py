"""Tests for the 0.5.0 features: wormhole, satellite, wallpaper, diff, manifest, stamp, seed-file."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import xml.dom.minidom as minidom
from pathlib import Path

from starweave import __version__
from starweave.cli import main
from starweave.layers import DEFAULT_LAYERS, Satellite, Wormhole
from starweave.options import WALLPAPER_PRESETS, RenderOptions, parse_wallpaper
from starweave.render import render_poster
from starweave.scene import content_hash, render_scene
from starweave.world import World, diff_worlds, format_diff


def parse(svg: str) -> minidom.Document:
    return minidom.parseString(svg)


def run_cli(args: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class VersionTests(unittest.TestCase):
    def test_version_is_050(self) -> None:
        self.assertEqual(__version__, "0.5.0")


class WormholeTests(unittest.TestCase):
    def test_wormhole_deterministic(self) -> None:
        world = World.from_seed("throat of night", "synthwave")
        world.features["wormhole"] = True
        opts = RenderOptions(width=700, height=500, stars=80)
        svg = render_scene(world, opts)
        parse(svg)
        again = World.from_seed("throat of night", "synthwave")
        again.features["wormhole"] = True
        self.assertEqual(svg, render_scene(again, opts))
        # Funnel throat is pure black.
        self.assertIn('fill="#000000"', svg)

    def test_wormhole_stream_independent(self) -> None:
        w = World.from_seed("stream island worm", "ember")
        a = w.stream("wormhole").random()
        b = w.stream("stars").random()
        c = w.stream("wormhole").random()
        self.assertEqual(a, c)
        self.assertNotEqual(a, b)

    def test_wormhole_present_absent_leaves_other_streams(self) -> None:
        probes = ("stars", "nebula", "planets", "blackhole", "background")
        w_off = World.from_seed("composability worm", "aurora")
        w_off.features["wormhole"] = False
        draws_off = {name: w_off.stream(name).random() for name in probes}

        w_on = World.from_seed("composability worm", "aurora")
        w_on.features["wormhole"] = True
        draws_on = {name: w_on.stream(name).random() for name in probes}
        self.assertEqual(draws_off, draws_on)

    def test_wormhole_layer_registered(self) -> None:
        names = {layer.name for layer in DEFAULT_LAYERS}
        self.assertIn("wormhole", names)
        self.assertIn("satellite", names)
        self.assertIn("stamp", names)
        self.assertIsInstance(Wormhole(), Wormhole)

    def test_without_wormhole_flag_skips_layer(self) -> None:
        world = World.from_seed("no throat", "aurora")
        world.features["wormhole"] = False
        svg = render_scene(world, RenderOptions(width=200, height=200), (Wormhole(),))
        # Layer builds nothing when feature is off (applies() is False).
        self.assertNotIn("whthroat", svg)


class SatelliteTests(unittest.TestCase):
    def test_satellite_near_planet(self) -> None:
        world = World.from_seed("docked station", "noir")
        world.features["satellite"] = True
        opts = RenderOptions(width=600, height=400, stars=40, planets=3)
        # Include orbits + planets + satellite so positions exist.
        layers = tuple(
            L for L in DEFAULT_LAYERS if L.name in ("background", "orbits", "planets", "satellite")
        )
        svg = render_scene(world, opts, layers)
        parse(svg)
        # Craft has solar-panel rects.
        self.assertIn("<rect", svg)
        again = World.from_seed("docked station", "noir")
        again.features["satellite"] = True
        self.assertEqual(svg, render_scene(again, opts, layers))

    def test_satellite_skips_without_planets(self) -> None:
        world = World.from_seed("empty orbit", "aurora")
        world.features["satellite"] = True
        opts = RenderOptions(width=300, height=200, planets=0)
        # Force planets=0 — Satellite.build returns early.
        # But planets must be > 0 for RenderOptions validation in render_poster.
        # Call layer directly via scene with planets=0 opts.
        from starweave.layers import Planets

        layers = (Planets(), Satellite())
        # planets=0 is allowed on RenderOptions dataclass itself.
        svg = render_scene(world, opts, layers)
        self.assertNotIn("<rect", svg)


class WallpaperTests(unittest.TestCase):
    def test_presets(self) -> None:
        self.assertEqual(parse_wallpaper("1080p"), (1920, 1080))
        self.assertEqual(parse_wallpaper("desktop"), (1920, 1080))
        self.assertEqual(parse_wallpaper("1440p"), (2560, 1440))
        self.assertEqual(parse_wallpaper("4k"), (3840, 2160))
        self.assertEqual(set(WALLPAPER_PRESETS), {"desktop", "1080p", "1440p", "4k"})

    def test_wxh(self) -> None:
        self.assertEqual(parse_wallpaper("1920x1080"), (1920, 1080))
        self.assertEqual(parse_wallpaper("800x600"), (800, 600))

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            parse_wallpaper("not-a-size")
        with self.assertRaises(ValueError):
            parse_wallpaper("0x100")

    def test_cli_wallpaper_sets_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "wall.svg"
            code, _, _ = run_cli([
                "desktop sky", "--wallpaper", "1080p", "--out", str(out),
                "--stars", "30", "--planets", "1", "--quiet",
            ])
            self.assertEqual(code, 0)
            svg = out.read_text(encoding="utf-8")
            self.assertIn('width="1920"', svg)
            self.assertIn('height="1080"', svg)
            doc = parse(svg)
            node = doc.getElementsByTagName("starweave")[0]
            params = json.loads(node.getAttribute("data-params"))
            self.assertEqual(params["size"], [1920, 1080])

    def test_cli_wallpaper_wxh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "custom.svg"
            code, _, _ = run_cli([
                "custom wall", "--wallpaper", "1280x720", "--out", str(out),
                "--stars", "20", "--quiet",
            ])
            self.assertEqual(code, 0)
            self.assertIn('width="1280"', out.read_text(encoding="utf-8"))


class DiffTests(unittest.TestCase):
    def test_diff_detects_differences(self) -> None:
        a = World.from_seed("alpha seed", "aurora")
        b = World.from_seed("beta seed phrase longer", "aurora")
        d = diff_worlds(a, b)
        self.assertFalse(d["identical"])
        self.assertEqual(d["seed_a"], "alpha seed")
        self.assertEqual(d["seed_b"], "beta seed phrase longer")
        # Different letter shape -> reading / knobs almost always differ.
        self.assertTrue(d["knobs"] or d["reading"] or d["features"]["only_a"] or d["features"]["only_b"])

    def test_diff_identical_same_seed(self) -> None:
        a = World.from_seed("same", "ember")
        b = World.from_seed("same", "ember")
        d = diff_worlds(a, b)
        self.assertTrue(d["identical"])
        text = format_diff(d)
        self.assertIn("identical: yes", text)

    def test_diff_json_format(self) -> None:
        a = World.from_seed("a", "aurora")
        b = World.from_seed("b", "aurora")
        payload = format_diff(diff_worlds(a, b), as_json=True)
        data = json.loads(payload)
        self.assertIn("knobs", data)
        self.assertIn("features", data)

    def test_cli_diff_text_and_json(self) -> None:
        code, out, _ = run_cli(["diff", "seed one", "seed two"])
        self.assertEqual(code, 0)
        self.assertIn("seed a:", out)
        self.assertIn("seed b:", out)

        code, out, _ = run_cli(["diff", "seed one", "seed two", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["seed_a"], "seed one")
        self.assertEqual(data["seed_b"], "seed two")


class ManifestTests(unittest.TestCase):
    def test_batch_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "family"
            code, stdout, _ = run_cli([
                "batch", "deep field", "--count", "4", "--out", str(out),
                "--width", "320", "--height", "200", "--stars", "20", "--quiet",
            ])
            self.assertEqual(code, 0)
            manifest_path = out / "manifest.json"
            self.assertTrue(manifest_path.exists())
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(data["base"], "deep field")
            self.assertEqual(data["count"], 4)
            self.assertEqual(len(data["members"]), 4)
            for i, member in enumerate(data["members"]):
                self.assertEqual(member["seed"], f"deep field#{i}")
                self.assertEqual(member["index"], i)
                self.assertIn("path", member)
                self.assertIn("palette", member)
                self.assertIn("world_name", member)
                self.assertTrue((out / member["path"]).exists())
            self.assertIn("manifest", stdout.lower())


class StampTests(unittest.TestCase):
    def test_content_hash_stable(self) -> None:
        world = World.from_seed("hash me", "aurora")
        opts = RenderOptions(width=400, height=300, stars=50, planets=2)
        h1 = content_hash(world, opts)
        h2 = content_hash(world, opts)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 10)

    def test_metadata_includes_stamp(self) -> None:
        svg = render_poster("stamp meta", width=400, height=300, stars=40, planets=1)
        doc = parse(svg)
        node = doc.getElementsByTagName("starweave")[0]
        params = json.loads(node.getAttribute("data-params"))
        self.assertIn("stamp", params)
        self.assertEqual(len(params["stamp"]), 10)

    def test_stamp_flag_draws_label(self) -> None:
        plain = render_poster("stamp draw", width=400, height=300, stars=30, stamp=False)
        stamped = render_poster("stamp draw", width=400, height=300, stars=30, stamp=True)
        self.assertNotEqual(plain, stamped)
        # Micro-label is monospace corner text with the hash.
        world = World.from_seed("stamp draw", "aurora")
        opts = RenderOptions(width=400, height=300, stars=30, stamp=True)
        expected = content_hash(world, opts)
        self.assertIn(expected, stamped)
        # CLI
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "s.svg"
            code, _, _ = run_cli([
                "stamp draw", "--stamp", "--out", str(out),
                "--width", "400", "--height", "300", "--stars", "30", "--quiet",
            ])
            self.assertEqual(code, 0)
            self.assertIn(expected, out.read_text(encoding="utf-8"))


class SeedFileTests(unittest.TestCase):
    def test_seed_file_reads_phrase(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            seed_path = Path(directory) / "phrase.txt"
            seed_path.write_text("# comment\nfrom file seed\n", encoding="utf-8")
            out = Path(directory) / "poster.svg"
            code, _, _ = run_cli([
                "--seed-file", str(seed_path), "--out", str(out),
                "--width", "320", "--height", "200", "--stars", "20", "--quiet",
            ])
            self.assertEqual(code, 0)
            svg = out.read_text(encoding="utf-8")
            self.assertIn("from file seed", svg)

    def test_seed_file_and_positional_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            seed_path = Path(directory) / "s.txt"
            seed_path.write_text("file seed\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                run_cli(["positional", "--seed-file", str(seed_path)])

    def test_seed_file_missing_errors(self) -> None:
        with self.assertRaises(SystemExit):
            run_cli(["--seed-file", "/nonexistent/path/seed.txt", "--describe"])


class QuietDefaultsTests(unittest.TestCase):
    def test_quiet_suppresses_wrote_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "q.svg"
            code, stdout, _ = run_cli([
                "quiet seed", "--out", str(out), "--width", "200", "--height", "150",
                "--stars", "10", "--quiet",
            ])
            self.assertEqual(code, 0)
            self.assertEqual(stdout.strip(), "")
            self.assertTrue(out.exists())

    def test_list_layers_includes_v050(self) -> None:
        code, out, _ = run_cli(["--list-layers"])
        self.assertEqual(code, 0)
        self.assertIn("wormhole", out)
        self.assertIn("satellite", out)
        self.assertIn("stamp", out)


if __name__ == "__main__":
    unittest.main()
