"""Tests for the deterministic World model, palettes, and naming."""

from __future__ import annotations

import unittest

from starweave.palette import PALETTES, resolve_palette_name
from starweave.world import World


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


if __name__ == "__main__":
    unittest.main()
