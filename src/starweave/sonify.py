"""Turn a seed into a short, deterministic piece of music.

The same World that paints the poster also scores a tune: the palette's mood
picks the scale, turbulence sets the tempo, brightness sets the timbre, and a
dedicated RNG stream walks the melody. Pure standard library — additive sine/
triangle synthesis written straight to a 16-bit mono WAV, so the same phrase
always sounds the same.
"""

from __future__ import annotations

import io
import math
import struct
import wave

from .world import World

SAMPLE_RATE = 44100

# Scale degrees (semitone offsets from the root) keyed by palette mood.
_SCALES = {
    "serene": [0, 2, 4, 7, 9],            # major pentatonic
    "radiant": [0, 2, 4, 5, 7, 9, 11],    # major
    "turbulent": [0, 2, 3, 5, 7, 9, 10],  # dorian
    "glacial": [0, 3, 5, 7, 10],          # minor pentatonic
    "balanced": [0, 2, 3, 5, 7, 8, 10],   # natural minor
}


def _scale_for(world: World) -> list[int]:
    return _SCALES.get(world.palette.mood, _SCALES["balanced"])


def _osc(freq: float, t: float, kind: str = "sine") -> float:
    x = 2.0 * math.pi * freq * t
    if kind == "tri":
        return (2.0 / math.pi) * math.asin(math.sin(x))
    return math.sin(x)


def _place(buf: list[float], start: float, dur: float, freq: float,
           amp: float, kind: str = "sine") -> None:
    i0 = int(start * SAMPLE_RATE)
    n = int(dur * SAMPLE_RATE)
    if n <= 0:
        return
    attack = max(1, int(0.010 * SAMPLE_RATE))
    release = max(1, int(0.060 * SAMPLE_RATE))
    end = min(len(buf), i0 + n)
    for i in range(end - i0):
        idx = i0 + i
        # Simple attack/release envelope to avoid clicks.
        if i < attack:
            env = i / attack
        elif i > n - release:
            env = max(0.0, (n - i) / release)
        else:
            env = 1.0
        buf[idx] += amp * env * _osc(freq, i / SAMPLE_RATE, kind)


def sonify(world: World, seconds: float = 12.0) -> bytes:
    """Render ``world`` to a deterministic mono 16-bit WAV (returned as bytes)."""

    seconds = max(1.0, float(seconds))
    rng = world.stream("music")
    scale = _scale_for(world)
    # Root note wanders a few semitones around C3 (≈130.8 Hz).
    root = 130.81 * (2 ** ((rng.randrange(0, 5) - 2) / 12.0))
    bpm = 78.0 + world.turbulence * 64.0
    beat = 60.0 / bpm
    n_samples = int(SAMPLE_RATE * seconds)
    buf = [0.0] * n_samples
    timbre = "tri" if world.brightness < 0.5 else "sine"

    # Melody: a random walk over the scale, occasional rests, octave hops.
    octaves = [0, 12, 12, 24]
    t = 0.0
    while t < seconds:
        dur = beat * rng.choice([0.5, 0.5, 1.0, 1.0, 1.0, 2.0])
        if rng.random() < 0.12:
            t += dur
            continue
        semis = rng.choice(scale) + rng.choice(octaves)
        freq = root * (2 ** (semis / 12.0))
        _place(buf, t, dur * 0.92, freq, amp=0.20 * (0.6 + 0.4 * world.brightness), kind=timbre)
        t += dur

    # Bass: the root, an octave down, pulsing every two beats.
    t = 0.0
    while t < seconds:
        _place(buf, t, beat * 1.8, root / 2.0, amp=0.16, kind="tri")
        t += beat * 2.0

    # Normalise with headroom, then quantise to int16.
    peak = max(abs(x) for x in buf) if buf else 0.0
    gain = min(1.0, 0.9 / peak) if peak > 1e-6 else 0.0
    frames = bytearray()
    for x in buf:
        v = int(max(-1.0, min(1.0, x * gain)) * 32767)
        frames += struct.pack("<h", v)

    out = io.BytesIO()
    writer = wave.open(out, "wb")
    writer.setnchannels(1)
    writer.setsampwidth(2)
    writer.setframerate(SAMPLE_RATE)
    writer.writeframes(bytes(frames))
    writer.close()
    return out.getvalue()
