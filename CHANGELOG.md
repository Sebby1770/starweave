# Changelog

All notable changes to Starweave are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `--reproduce FILE` — regenerate a poster byte-for-byte from the metadata
  embedded in an existing SVG, closing the reproducibility loop.
- A `py.typed` marker so downstream type checkers see the package's type hints.

## [0.3.0] — 2026-06-21

The release that turns a one-shot poster script into a generative engine and a
multi-medium toolkit. A seed phrase now expands into a deterministic *World*
that a stack of composable layers paints — and that same world can be animated,
morphed, sonified, explored in the browser, or printed as terminal art.

### Added

**Engine**

- A `seed → World → Layer` pipeline (`world.py`, `layers.py`, `scene.py`,
  `svg.py`). Each seed derives a mood, intensity knobs, feature flags, and a
  catalogue name, plus a factory of independent named RNG streams, so layers
  can be added or removed without disturbing one another.
- An `SvgDoc` builder with per-document unique id prefixes (so many posters can
  inline on one page), CSS-animation support, and embedded reproducibility
  metadata.

**New layers**

- Galaxy (logarithmic spiral), aurora band, perspective grid, comets, cratered
  moon, foreground horizon.
- `filament` — a branching structure **grown by an L-system** rather than placed.
- `attractor` — a **De Jong strange attractor**: a chaotic map iterated
  thousands of times, its four parameters drawn from the seed, settling into a
  luminous deterministic swirl.

**Generativity**

- **Semantic seeding** — the phrase's letter statistics steer the art:
  vowel-rich phrases render brighter, consonant-heavy ones more turbulent,
  longer words denser.
- **Seed-space morph** (`--morph SEED_B`) — interpolate between two seeds; the
  structure is held while palette and mood flow from one to the other.
- **Constellation myths** (`--myth`) — each named constellation gets a short,
  deterministic origin legend.
- 10 colour palettes (up from 4) plus `--palette auto`, `--variant`, and
  `--only`/`--without` layer selection.

**New media**

- **Animated SVG** (`--animate`) — self-contained twinkle / drift / orbit.
- **Sonification** (`--sonify`) — the same world scored as a deterministic WAV
  (scale from mood, tempo from turbulence, melody from a stream); pure stdlib.
- **ASCII rendering** (`--ascii`) — the world as terminal star-art.
- **HTML galleries** — `--gallery N` (variants) and `--gallery-palettes`.

**Web**

- A self-contained, dependency-free **web explorer** (`--explorer`, prebuilt at
  `web/explorer.html`): type a phrase, watch it generate, drag the morph slider,
  shuffle, **play the tune** (Web Audio), and save the SVG.

**Quality**

- 45 unit tests (up from 5) covering determinism, well-formed XML across every
  palette/variant, animation, metadata, layer selection, morph, semantics,
  sonification, ASCII, and the explorer.
- GitHub Actions CI on Python 3.10–3.13 with a CLI smoke test.

### Changed

- Rebuilt from a single 255-line file into a documented package. `render_poster`
  keeps its original signature and output contract — the original tests still
  pass unchanged.

### Fixed

- Dropped a deprecated `License ::` classifier that broke `pip install` on
  modern setuptools (PEP 639).

## [0.1.0]

- The original single-file generator: one static SVG poster from a seed phrase,
  four palettes, a fixed set of layers.
