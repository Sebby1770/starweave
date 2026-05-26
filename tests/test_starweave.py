from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from starweave.cli import main
from starweave.render import render_poster


class RenderPosterTests(unittest.TestCase):
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
        with self.assertRaises(ValueError):
            render_poster("bad width", width=0)


class CliTests(unittest.TestCase):
    def test_cli_writes_svg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "poster.svg"
            result = main(
                [
                    "cli seed",
                    "--out",
                    str(output),
                    "--width",
                    "320",
                    "--height",
                    "220",
                    "--stars",
                    "20",
                    "--planets",
                    "1",
                ]
            )
            self.assertEqual(result, 0)
            self.assertTrue(output.exists())
            self.assertIn("cli seed", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

