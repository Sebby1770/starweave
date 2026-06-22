# Starweave

Starweave turns any phrase into a **deterministic** SVG space poster. The same
seed always produces the same universe — so a poster is fully described by its
seed, and you can regenerate it from the metadata baked into the file.

![Example poster](examples/sebby-launch.svg)

It's pure standard-library Python at runtime (no dependencies), and it can emit
static posters, **self-contained animated SVGs**, and **HTML contact-sheet
galleries**.

## The idea

A seed phrase doesn't draw a picture directly. It expands into a **World** — a
small bundle of facts (a mood, intensity knobs, which celestial features exist,
a generated catalogue name) plus a factory of independent random streams. A
stack of **Layers** then paints that world onto an SVG document:

```
 seed ── sha256 ──▶  World ────────────────▶  Scene (layer stack) ──▶  SVG
                    │ mood, density,          │ background, nebula,     │ static
                    │ turbulence,             │ galaxy, aurora, grid,   │ animated
                    │ features{galaxy,moon,   │ orbits, stars,          │ gallery
                    │  comets,aurora,rings…}  │ constellations, comets,
                    │ name "Sigma Lyrae"      │ planets, moon, horizon,
                    └ stream("stars") …       └ title
```

Two properties fall out of that design:

- **Reproducible** — `(seed, palette, variant)` fully determines the poster.
  The world summary and generation params are embedded in the SVG `<metadata>`.
- **Composable** — every layer draws from its *own* named RNG stream
  (`world.stream("stars")`), so adding, dropping, or reordering layers never
  changes another layer's output. The galaxy looks identical whether or not
  comets are drawn.

## Quick start

```bash
python3 -m starweave "Sebby's launch" --palette aurora --out poster.svg
```

Install the CLI:

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -e .
starweave "late night code" --palette auto --out poster.svg --open
```

## Things to try

```bash
# Animated SVG — twinkling stars, drifting nebulae, orbiting planets.
starweave "midnight compiler" --palette synthwave --animate --out anim.svg

# Let the seed choose its own signature palette.
starweave "tidal lock" --palette auto

# A contact sheet of 9 deterministic variants of one phrase.
starweave "deep field" --gallery 9 --out gallery.html --open

# One poster per built-in palette, side by side.
starweave "deep field" --gallery-palettes --out palettes.html

# Seed-space morph: walk the path between two phrases. The structure is held
# from the first seed while palette and mood interpolate — one sky, shifting.
starweave "ember tide" --morph "glacial drift" --frames 9 --out morph.html

# A self-contained web explorer — type a phrase, morph, save the SVG. No deps.
starweave --explorer --out web/explorer.html   # then open it in any browser

# Hear the seed: the same World that paints the poster scores a short tune
# (scale from mood, tempo from turbulence). Pure stdlib -> a deterministic WAV.
starweave "the long quiet between stars" --sonify --seconds 12 --out song.wav

# A different medium entirely: the same world as terminal star-art.
starweave "the long quiet between stars" --ascii --cols 90
```

Some seeds also grow a **strange attractor** — a De Jong chaotic map iterated
thousands of times, whose four parameters come from the phrase, so each one
settles into its own luminous, deterministic swirl.

A prebuilt copy lives at [`web/explorer.html`](web/explorer.html) — it can even
**play the seed's tune** in-browser (Web Audio), mirroring `--sonify`. The
poster's mood is partly read from the phrase itself: vowel-rich phrases render
brighter, consonant-heavy ones more turbulent, longer words denser. Some seeds
also grow an **L-system filament** — a branching structure that emerges from a
tiny rewrite grammar rather than being hand-placed. Inspect a seed with:

```bash
starweave "the long quiet between stars" --describe   # see the "reading"

# Inspect the world a seed expands into, without drawing anything.
starweave "orbit coffee" --describe --palette auto

# Sculpt the composition: keep or drop named layers.
starweave "clean sky" --without galaxy,comets,grid
starweave "minimal"   --only background,stars,title
```

## CLI reference

| Flag | Meaning |
| --- | --- |
| `--out PATH` | Output file (`.svg`, or `.html` for galleries). |
| `--width` / `--height` | Canvas size (default 1440×900). |
| `--stars` / `--planets` | Counts (the world scales density around these). |
| `--palette NAME` | One of the built-ins, or `auto` to pick from the seed. |
| `--variant N` | A different deterministic draw of the same seed. |
| `--animate` | Emit an animated SVG (twinkle / drift / orbit). |
| `--only A,B` / `--without A,B` | Include or exclude layers by name. |
| `--gallery [N]` | HTML contact sheet of N seed variants (default 6). |
| `--gallery-palettes` | Gallery with one poster per palette. |
| `--morph SEED_B [--frames N]` | Interpolate the seed-space from the seed to `SEED_B`. |
| `--explorer` | Write a self-contained interactive web explorer (HTML). |
| `--sonify [--seconds N]` | Render the seed as a deterministic WAV tune. |
| `--ascii [--cols N]` | Render the seed as terminal star-art. |
| `--describe` | Print the seed's world as JSON and exit. |
| `--title` / `--no-title` | Override or hide the poster title. |
| `--list-palettes` / `--list-layers` | Discoverability. |

Ten palettes ship in the box: `aurora`, `ember`, `midnight`, `solar`, `rose`,
`noir`, `synthwave`, `glacier`, `verdant`, `gilded` — plus `auto`.

## Library use

```python
from starweave import render_poster, World

svg = render_poster("late night code", palette="auto", animate=True)

world = World.from_seed("late night code", "auto")
print(world.name, world.summary()["features"])
```

## Project layout

```
src/starweave/
  world.py    seed -> World (mood, knobs, features, name, RNG streams)
  layers.py   composable Layer classes painted back-to-front
  scene.py    World + layers -> SvgDoc
  svg.py      SVG document builder (defs, CSS animation, unique ids, metadata)
  palette.py  ten palettes + deterministic "auto"
  naming.py   deterministic catalogue names and captions
  gallery.py  many posters inlined on one self-contained HTML page
  cli.py      argument parsing and file output
```

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

CI runs the suite on Python 3.10–3.13 and smoke-tests the CLI on every push.

## License

MIT — see [LICENSE](LICENSE).
