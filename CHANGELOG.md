# Changelog

All notable changes to Starweave are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.6.0] — 2026-07-21

Pulsars, dust lanes, theme packs, multi-seed lists, SVG minify, validate,
Okabe–Ito / colorblind palette, and morph frame export — still pure stdlib.

### Added
- **pulsar** / **dust_lane** layers with independent RNG streams
- **Theme packs** (`noir`, `biolume`, `ember`, `ice`) via `--theme`
- **`--seed-list`** multi-seed batch into a directory
- **`--minify`** lightweight SVG whitespace collapse
- **`starweave validate`** reproducibility metadata check
- **colorblind / okabe-ito** palette
- **`--out-dir`** with `--morph` writes `frame_00.svg` …
- Wallpaper, seed-list, and theme CLI tests

### Changed
- Version **0.6.0**

## [0.5.0] — 2026-07-19

Wormholes, satellites, wallpaper sizes, seed-space diff, batch manifests, and
hash stamps — still pure standard-library Python with zero runtime dependencies.

### Added

**New layers**

- `wormhole` — concentric distorted rings funneling into a dark throat; own RNG
  stream (`wormhole`), feature flag with ~24% odds.
- `satellite` — tiny craft / station with solar panels near a host planet when
  the `satellite` feature is on and planets are present; stream `satellite`.
- `stamp` — optional corner micro-label (only when `--stamp` is set).

**Wallpaper mode**

- `--wallpaper 1920x1080` or presets `desktop` / `1080p` / `1440p` / `4k` set
  width and height (overrides `--width` / `--height`).

**Seed diff**

- `starweave diff "seed a" "seed b"` prints which World knobs, reading stats,
  and features differ (text by default; `--json` for machine-readable output).

**Batch manifest**

- `starweave batch` writes `manifest.json` alongside `index.html`, listing each
  member's seed, path, palette, and world name. Disable with `--no-manifest`.

**Hash stamp**

- Every SVG embeds a short content hash of seed + params in `<metadata>`
  (`stamp` field).
- `--stamp` draws that hash as a corner micro-label.

**Seed from file**

- `--seed-file PATH` reads the seed phrase from a file (first non-empty,
  non-`#` line). Cannot be combined with a positional seed.

**Tests**

- Wormhole determinism and stream independence; wallpaper size parsing and CLI;
  diff text/JSON; batch manifest shape; stamp metadata + label; seed-file.

### Changed

- Version bump to **0.5.0**.
- `--quiet` also suppresses the final “Wrote …” status line on single renders
  (galleries/batch already used it for progress).

## [0.4.0] — 2026-07-19

Black holes, seed families, world dumps, and palette previews — still pure
standard-library Python with zero runtime dependencies.

### Added

**New layers**

- `blackhole` — event-horizon silhouette, tilted accretion disk, photon-ring
  glow; own RNG stream (`blackhole`), feature flag with ~22% odds.
- `supernova` — remnant shells and filament arcs around a bright core; stream
  `supernova`.
- `nebula_clusters` — tighter packs of overlapping cloudlets on top of the base
  nebula wash; stream `nebula_clusters`. New features are appended to the
  feature table so older feature rolls stay stable.

**Seed family / batch CLI**

- `starweave batch "base" --count 12 --out family/` writes 12 variants with
  seeds `base#0` … `base#11`, plus an optional `index.html` contact page.
- Terminal progress (dots + percent on stderr) for batch and galleries.

**World dump & palettes**

- `--dump-world FILE` exports World knobs / features / name / myth as JSON
  without rendering (or alongside `--out`).
- `starweave palette-preview --out palettes.svg` — swatch-strip SVG of every
  built-in palette; `--list-palettes` still lists names and moods.

**ASCII**

- Denser default character ramp for terminal star-art.
- `--ascii-width N` (alongside existing `--cols`).

**Tests**

- Composability: blackhole / supernova / nebula_clusters present or absent does
  not change other named stream outputs.
- Batch writes N files; dump-world JSON keys; palette-preview non-empty;
  blackhole determinism; reproduce hardening.

### Changed

- Version bump to **0.4.0**.
- Gallery rendering reports progress on stderr (disable with `--quiet`).

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

**Reproducibility**

- Every SVG embeds its generation parameters, and `--reproduce FILE` regenerates
  a poster byte-for-byte from them — a poster is fully recoverable from itself.
- A `py.typed` marker so downstream type checkers see the package's type hints.

**Quality**

- Unit tests covering determinism, well-formed XML across every palette/variant,
  animation, metadata round-trip, layer selection, morph, semantics, myths,
  sonification, ASCII, the attractor, and the explorer.
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
