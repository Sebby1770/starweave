"""Tests for the 0.6.0 features: pulsar, dust_lane, themes, seed-list, minify,
validate, colorblind palette, morph frame export."""

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
from starweave.layers import DEFAULT_LAYERS, DustLane, Pulsar
from starweave.minify import minify_svg
from starweave.options import RenderOptions
from starweave.palette import PALETTES, get_palette, resolve_palette_name
from starweave.render import render_poster
from starweave.scene import render_scene
from starweave.themes import THEMES, apply_theme, get_theme
from starweave.validate import validate_svg_file, validate_svg_text
from starweave.world import World


def parse(svg: str) -> minidom.Document:
    return minidom.parseString(svg)


def run_cli(args: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class VersionTests(unittest.TestCase):
    def test_version_is_060(self) -> None:
        self.assertEqual(__version__, "0.6.0")


class PulsarTests(unittest.TestCase):
    def test_pulsar_deterministic(self) -> None:
        world = World.from_seed("lighthouse pulse", "synthwave")
        world.features["pulsar"] = True
        opts = RenderOptions(width=700, height=500, stars=80)
        svg = render_scene(world, opts)
        parse(svg)
        again = World.from_seed("lighthouse pulse", "synthwave")
        again.features["pulsar"] = True
        self.assertEqual(svg, render_scene(again, opts))
        self.assertIn("pshalo", svg)

    def test_pulsar_stream_independent(self) -> None:
        w = World.from_seed("stream island pulsar", "ember")
        a = w.stream("pulsar").random()
        b = w.stream("stars").random()
        c = w.stream("pulsar").random()
        self.assertEqual(a, c)
        self.assertNotEqual(a, b)

    def test_pulsar_present_absent_leaves_other_streams(self) -> None:
        probes = ("stars", "nebula", "planets", "blackhole", "background", "galaxy")
        w_off = World.from_seed("composability pulsar", "aurora")
        w_off.features["pulsar"] = False
        draws_off = {name: w_off.stream(name).random() for name in probes}

        w_on = World.from_seed("composability pulsar", "aurora")
        w_on.features["pulsar"] = True
        draws_on = {name: w_on.stream(name).random() for name in probes}
        self.assertEqual(draws_off, draws_on)

    def test_pulsar_layer_registered(self) -> None:
        names = {layer.name for layer in DEFAULT_LAYERS}
        self.assertIn("pulsar", names)
        self.assertIn("dust_lane", names)
        self.assertIsInstance(Pulsar(), Pulsar)

    def test_without_pulsar_flag_skips_layer(self) -> None:
        world = World.from_seed("no beacon", "aurora")
        world.features["pulsar"] = False
        svg = render_scene(world, RenderOptions(width=200, height=200), (Pulsar(),))
        self.assertNotIn("pshalo", svg)


class DustLaneTests(unittest.TestCase):
    def test_dust_lane_needs_galaxy(self) -> None:
        world = World.from_seed("dusty spiral", "midnight")
        world.features["dust_lane"] = True
        world.features["galaxy"] = False
        layer = DustLane()
        self.assertFalse(layer.applies(world))

        world.features["galaxy"] = True
        self.assertTrue(layer.applies(world))

    def test_dust_lane_draws_with_galaxy(self) -> None:
        world = World.from_seed("lane across arms", "aurora")
        world.features["galaxy"] = True
        world.features["dust_lane"] = True
        opts = RenderOptions(width=600, height=400, stars=40)
        layers = tuple(L for L in DEFAULT_LAYERS if L.name in ("background", "galaxy", "dust_lane"))
        svg = render_scene(world, opts, layers)
        parse(svg)
        # multiply blend for absorption bands
        self.assertIn("multiply", svg)
        again = World.from_seed("lane across arms", "aurora")
        again.features["galaxy"] = True
        again.features["dust_lane"] = True
        self.assertEqual(svg, render_scene(again, opts, layers))

    def test_dust_lane_stream_independent(self) -> None:
        w = World.from_seed("dust stream", "noir")
        a = w.stream("dust_lane").random()
        b = w.stream("galaxy").random()
        self.assertNotEqual(a, b)
        self.assertEqual(a, w.stream("dust_lane").random())


class ThemeTests(unittest.TestCase):
    def test_theme_names(self) -> None:
        self.assertEqual(set(THEMES), {"noir", "biolume", "ember", "ice"})

    def test_theme_palette_mapping(self) -> None:
        self.assertEqual(get_theme("noir").palette, "noir")
        self.assertEqual(get_theme("biolume").palette, "verdant")
        self.assertEqual(get_theme("ember").palette, "ember")
        self.assertEqual(get_theme("ice").palette, "glacier")

    def test_apply_theme_biases_knobs(self) -> None:
        world = World.from_seed("theme probe", "aurora")
        before_t = world.turbulence
        theme = get_theme("ice")
        apply_theme(world, theme)
        # ice multiplies turbulence by 0.45
        self.assertAlmostEqual(world.turbulence, min(1.0, before_t * 0.45), places=5)
        self.assertEqual(world.palette.name, "aurora")  # apply_theme does not swap palette

    def test_render_poster_theme_overrides_palette(self) -> None:
        svg = render_poster("theme sky", theme="noir", width=400, height=300, stars=30)
        doc = parse(svg)
        node = doc.getElementsByTagName("starweave")[0]
        params = json.loads(node.getAttribute("data-params"))
        self.assertEqual(params["world"]["palette"], "noir")

    def test_cli_theme_and_list(self) -> None:
        code, out, _ = run_cli(["--list-themes"])
        self.assertEqual(code, 0)
        self.assertIn("biolume", out)
        self.assertIn("palette=verdant", out)

        with tempfile.TemporaryDirectory() as directory:
            out_path = Path(directory) / "ice.svg"
            code, _, _ = run_cli([
                "frozen lake", "--theme", "ice", "--out", str(out_path),
                "--width", "320", "--height", "200", "--stars", "20", "--quiet",
            ])
            self.assertEqual(code, 0)
            params = json.loads(
                parse(out_path.read_text(encoding="utf-8"))
                .getElementsByTagName("starweave")[0]
                .getAttribute("data-params")
            )
            self.assertEqual(params["world"]["palette"], "glacier")


class ColorblindPaletteTests(unittest.TestCase):
    def test_colorblind_in_palettes(self) -> None:
        self.assertIn("colorblind", PALETTES)
        p = get_palette("colorblind")
        self.assertEqual(p.name, "colorblind")
        self.assertIn("#E69F00", p.nebula)

    def test_okabe_ito_alias(self) -> None:
        self.assertEqual(resolve_palette_name("okabe-ito", "x"), "colorblind")
        self.assertEqual(get_palette("okabe-ito").name, "colorblind")

    def test_render_with_colorblind(self) -> None:
        svg = render_poster("cb sky", palette="colorblind", width=300, height=200, stars=20)
        parse(svg)
        self.assertIn("#E69F00", svg)

    def test_cli_okabe_ito(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "oi.svg"
            code, _, _ = run_cli([
                "safe colors", "--palette", "okabe-ito", "--out", str(out),
                "--width", "300", "--height", "200", "--stars", "15", "--quiet",
            ])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())


class MinifyTests(unittest.TestCase):
    def test_minify_collapses_whitespace(self) -> None:
        svg = render_poster("minify me", width=300, height=200, stars=15)
        mini = minify_svg(svg)
        self.assertLess(len(mini), len(svg))
        parse(mini)  # still well-formed
        # Title text content keeps internal spaces.
        self.assertIn("seed: minify me", mini)

    def test_minify_flag_on_render_poster(self) -> None:
        plain = render_poster("m", width=200, height=150, stars=10, minify=False)
        mini = render_poster("m", width=200, height=150, stars=10, minify=True)
        self.assertLess(len(mini), len(plain))

    def test_cli_minify(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "m.svg"
            code, _, _ = run_cli([
                "compact", "--minify", "--out", str(out),
                "--width", "240", "--height", "160", "--stars", "12", "--quiet",
            ])
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertNotIn("\n\n", text)


class ValidateTests(unittest.TestCase):
    def test_validate_good_poster(self) -> None:
        svg = render_poster("valid seed", width=300, height=200, stars=15)
        result = validate_svg_text(svg, path="mem.svg")
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])
        self.assertIsNotNone(result.params)

    def test_validate_missing_metadata(self) -> None:
        result = validate_svg_text(
            '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>',
            path="bare.svg",
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("missing" in e for e in result.errors))

    def test_cli_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            good = Path(directory) / "good.svg"
            good.write_text(
                render_poster("ok", width=200, height=150, stars=10),
                encoding="utf-8",
            )
            bad = Path(directory) / "bad.svg"
            bad.write_text("<svg></svg>", encoding="utf-8")

            code, out, _ = run_cli(["validate", str(good)])
            self.assertEqual(code, 0)
            self.assertIn("ok", out)

            code, out, _ = run_cli(["validate", str(bad)])
            self.assertEqual(code, 1)
            self.assertIn("FAIL", out)

            code, _, _ = run_cli(["validate", str(good), str(bad)])
            self.assertEqual(code, 1)

    def test_validate_file_missing(self) -> None:
        result = validate_svg_file("/nonexistent/poster.svg")
        self.assertFalse(result.ok)


class SeedListTests(unittest.TestCase):
    def test_seed_list_writes_many(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            seeds = Path(directory) / "seeds.txt"
            seeds.write_text(
                "# comment\nalpha one\nbeta two\n\ngamma three\n",
                encoding="utf-8",
            )
            out_dir = Path(directory) / "posters"
            code, stdout, _ = run_cli([
                "--seed-list", str(seeds), "--out", str(out_dir),
                "--width", "240", "--height", "160", "--stars", "12", "--quiet",
            ])
            self.assertEqual(code, 0)
            files = sorted(out_dir.glob("*.svg"))
            self.assertEqual(len(files), 3)
            for f in files:
                parse(f.read_text(encoding="utf-8"))
            # seeds appear in metadata of corresponding files
            texts = [f.read_text(encoding="utf-8") for f in files]
            joined = "\n".join(texts)
            self.assertIn("alpha one", joined)
            self.assertIn("beta two", joined)
            self.assertIn("gamma three", joined)

    def test_seed_list_requires_out(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            seeds = Path(directory) / "s.txt"
            seeds.write_text("only one\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                run_cli(["--seed-list", str(seeds)])


class MorphFramesTests(unittest.TestCase):
    def test_out_dir_writes_frame_svgs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out_dir = Path(directory) / "morph_frames"
            code, stdout, _ = run_cli([
                "ember tide", "--morph", "glacial drift", "--frames", "4",
                "--out-dir", str(out_dir),
                "--width", "320", "--height", "200", "--stars", "20",
            ])
            self.assertEqual(code, 0)
            frames = sorted(out_dir.glob("frame_*.svg"))
            self.assertEqual(len(frames), 4)
            self.assertEqual(frames[0].name, "frame_00.svg")
            self.assertEqual(frames[3].name, "frame_03.svg")
            for f in frames:
                parse(f.read_text(encoding="utf-8"))
            self.assertIn("4 frames", stdout.lower())

    def test_out_dir_and_html_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out_dir = Path(directory) / "frames"
            html = Path(directory) / "morph.html"
            code, _, _ = run_cli([
                "a", "--morph", "b", "--frames", "3",
                "--out-dir", str(out_dir), "--out", str(html),
                "--width", "280", "--height", "180", "--stars", "15", "--quiet",
            ])
            self.assertEqual(code, 0)
            self.assertEqual(len(list(out_dir.glob("frame_*.svg"))), 3)
            self.assertTrue(html.exists())


class ListLayersV060Tests(unittest.TestCase):
    def test_list_layers_includes_v060(self) -> None:
        code, out, _ = run_cli(["--list-layers"])
        self.assertEqual(code, 0)
        self.assertIn("pulsar", out)
        self.assertIn("dust_lane", out)


if __name__ == "__main__":
    unittest.main()
