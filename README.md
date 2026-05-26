# Starweave

Starweave is a tiny pure-Python CLI that turns any phrase into a deterministic SVG space poster.

![Example poster](examples/sebby-launch.svg)

## What it does

- Generates repeatable space art from a seed phrase.
- Renders gradients, star fields, constellations, planets, rings, and orbit lines.
- Exports normal SVG files that open in any browser or design tool.
- Uses only the Python standard library at runtime.

## Quick start

```bash
python3 -m starweave "Sebby's launch" --out examples/sebby-launch.svg --palette aurora
```

Install the CLI locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
starweave "late night code" --palette ember --out poster.svg --open
```

## CLI options

```bash
starweave "your seed phrase" \
  --width 1440 \
  --height 900 \
  --stars 320 \
  --planets 5 \
  --palette midnight \
  --out poster.svg
```

List available palettes:

```bash
starweave --list-palettes
```

## Development

Run the test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
