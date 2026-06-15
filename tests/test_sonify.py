"""Tests for deterministic sonification."""

from __future__ import annotations

import io
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from starweave.cli import main
from starweave.sonify import SAMPLE_RATE, sonify
from starweave.world import World


def _read(data: bytes) -> wave.Wave_read:
    return wave.open(io.BytesIO(data), "rb")


class SonifyTests(unittest.TestCase):
    def test_is_a_valid_mono_16bit_wav(self) -> None:
        w = _read(sonify(World.from_seed("test tune", "aurora"), seconds=3))
        self.assertEqual(w.getnchannels(), 1)
        self.assertEqual(w.getsampwidth(), 2)
        self.assertEqual(w.getframerate(), SAMPLE_RATE)

    def test_duration_matches_request(self) -> None:
        w = _read(sonify(World.from_seed("len", "ember"), seconds=4))
        self.assertAlmostEqual(w.getnframes(), 4 * SAMPLE_RATE, delta=SAMPLE_RATE)

    def test_deterministic(self) -> None:
        a = sonify(World.from_seed("same", "midnight"), seconds=3)
        b = sonify(World.from_seed("same", "midnight"), seconds=3)
        self.assertEqual(a, b)

    def test_different_seed_sounds_different(self) -> None:
        a = sonify(World.from_seed("alpha", "aurora"), seconds=3)
        b = sonify(World.from_seed("omega", "aurora"), seconds=3)
        self.assertNotEqual(a, b)

    def test_not_silent(self) -> None:
        w = _read(sonify(World.from_seed("loud", "solar"), seconds=3))
        frames = w.readframes(w.getnframes())
        peak = max(abs(v) for v in struct.unpack(f"<{len(frames) // 2}h", frames))
        self.assertGreater(peak, 1000)

    def test_cli_writes_wav(self) -> None:
        import contextlib

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "tune.wav"
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["cli tune", "--sonify", "--seconds", "2", "--out", str(output)])
            self.assertEqual(code, 0)
            self.assertTrue(output.exists())
            self.assertEqual(_read(output.read_bytes()).getframerate(), SAMPLE_RATE)


if __name__ == "__main__":
    unittest.main()
