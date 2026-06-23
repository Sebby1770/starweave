"""Tests for the deterministic World model, palettes, and naming."""

from __future__ import annotations

import unittest

from starweave.options import RenderOptions
from starweave.morph import morph_cells
from starweave.palette import PALETTES, blend_palette, resolve_palette_name
from starweave.world import World, semantics


class WorldTests(unittest.TestCase):
    def test_world_is_deterministic(self) -> None:
        a = World.from_seed("repeatable", "aurora", 0)
        b = World.from_seed("repeatable", "aurora", 0)
        self.assertEqual(a.summary(), b.summary())

    def test_variant_changes_the_world(self) -> None:
        a = World.from_seed("same seed", "aurora", 0)
        b = World.from_seed("same seed", "aurora", 1)
        self.assertNotEqual(a.summary(), b.summary())

    def test_streams_are_independent_and_named(self) -> None:
        world = World.from_seed("streams", "aurora")
        stars_a = world.stream("stars").random()
        stars_b = world.stream("stars").random()
        comets = world.stream("comets").random()
        # Same stream name -> same sequence; different name -> different.
        self.assertEqual(stars_a, stars_b)
        self.assertNotEqual(stars_a, comets)

    def test_knobs_are_in_range(self) -> None:
        for seed in ("a", "bb", "three words here", "x" * 40):
            world = World.from_seed(seed, "auto")
            for value in (world.turbulence, world.brightness, world.density):
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_features_are_booleans_and_stable(self) -> None:
        world = World.from_seed("feature seed", "midnight")
        self.assertTrue(all(isinstance(v, bool) for v in world.features.values()))
        again = World.from_seed("feature seed", "midnight")
        self.assertEqual(world.features, again.features)

    def test_myth_is_generated_deterministic_and_named(self) -> None:
        world = World.from_seed("a myth", "aurora")
        self.assertTrue(world.myth)
        self.assertEqual(world.myth, World.from_seed("a myth", "aurora").myth)
        self.assertNotEqual(world.myth, World.from_seed("other myth", "aurora").myth)
        self.assertNotIn("the the ", world.myth.lower())  # no double article
        self.assertEqual(world.summary()["myth"], world.myth)

    def test_summary_features_match_flags(self) -> None:
        world = World.from_seed("summary", "solar")
        listed = set(world.summary()["features"])
        flagged = {k for k, v in world.features.items() if v}
        self.assertEqual(listed, flagged)


class PaletteTests(unittest.TestCase):
    def test_auto_is_deterministic_and_real(self) -> None:
        first = resolve_palette_name("auto", "some phrase")
        second = resolve_palette_name("auto", "some phrase")
        self.assertEqual(first, second)
        self.assertIn(first, PALETTES)

    def test_auto_varies_by_seed(self) -> None:
        names = {resolve_palette_name("auto", f"seed {i}") for i in range(40)}
        self.assertGreater(len(names), 1)

    def test_explicit_name_passes_through(self) -> None:
        self.assertEqual(resolve_palette_name("ember", "ignored"), "ember")


class BlendTests(unittest.TestCase):
    def test_blend_endpoints_match_originals(self) -> None:
        a, b = PALETTES["ember"], PALETTES["glacier"]
        self.assertEqual(blend_palette(a, b, 0.0).nebula, a.nebula)
        self.assertEqual(blend_palette(a, b, 1.0).nebula, b.nebula)

    def test_blend_midpoint_is_valid_hex(self) -> None:
        mid = blend_palette(PALETTES["ember"], PALETTES["glacier"], 0.5)
        for role in (mid.background, mid.nebula, mid.stars, mid.planets, mid.accent):
            for color in role:
                self.assertRegex(color, r"^#[0-9a-f]{6}$")

    def test_blended_world_holds_structure_interpolates_mood(self) -> None:
        a = World.from_seed("ember tide", "ember")
        b = World.from_seed("glacial drift", "glacier")
        mid = World.blended(a, b, 0.5)
        # density (element counts) is held from A; mood knobs move toward B.
        self.assertEqual(mid.density, a.density)
        lo, hi = sorted((a.turbulence, b.turbulence))
        self.assertGreaterEqual(mid.turbulence, lo - 1e-9)
        self.assertLessEqual(mid.turbulence, hi + 1e-9)


class SemanticTests(unittest.TestCase):
    def test_signals_are_in_range(self) -> None:
        for text in ("a", "the quiet sky", "crwth blvd", "x" * 30):
            sem = semantics(text)
            for key in ("vowel_ratio", "brightness", "turbulence", "density"):
                self.assertGreaterEqual(sem[key], 0.0)
                self.assertLessEqual(sem[key], 1.0)

    def test_vowels_brighten_consonants_roughen(self) -> None:
        bright = World.from_seed("aurora oasis aria", "midnight")
        rough = World.from_seed("crwth blvd grmph", "midnight")
        self.assertGreater(bright.brightness, rough.brightness)
        self.assertGreater(rough.turbulence, bright.turbulence)

    def test_reading_is_deterministic_and_reported(self) -> None:
        a = World.from_seed("seed phrase", "ember")
        b = World.from_seed("seed phrase", "ember")
        self.assertEqual(a.reading, b.reading)
        self.assertIn("vowel_ratio", a.summary()["reading"])


class MorphTests(unittest.TestCase):
    def test_morph_produces_requested_frames(self) -> None:
        opts = RenderOptions(width=320, height=220, stars=40)
        cells = morph_cells("alpha", "omega", frames=5, palette="auto", opts=opts)
        self.assertEqual(len(cells), 5)

    def test_morph_is_deterministic(self) -> None:
        opts = RenderOptions(width=320, height=220, stars=40)
        first = morph_cells("a", "b", frames=4, palette="ember", opts=opts)
        second = morph_cells("a", "b", frames=4, palette="ember", opts=opts)
        self.assertEqual([c.svg for c in first], [c.svg for c in second])

    def test_morph_frames_have_distinct_ids(self) -> None:
        # Distinct variant per frame -> distinct id prefix, so inlined SVGs on
        # one page don't share gradient ids.
        opts = RenderOptions(width=320, height=220, stars=40)
        cells = morph_cells("a", "b", frames=3, palette="ember", opts=opts)
        self.assertNotEqual(cells[0].svg, cells[1].svg)


if __name__ == "__main__":
    unittest.main()
