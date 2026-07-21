"""Composable poster layers.

Each layer is a small object with a ``name`` and a ``build(world, doc, opts)``
method that appends elements (and any defs / CSS) to an :class:`~starweave.svg.SvgDoc`.
Layers are painted back-to-front in the order the scene lists them.

A layer pulls *only* from its own named RNG stream (``world.stream(self.name)``),
so the set of layers can change without perturbing any other layer's output.
"""

from __future__ import annotations

import math
import random

from .options import RenderOptions
from .svg import SvgDoc, esc, fmt
from .world import World


class Layer:
    name: str = "layer"
    #: When set, the layer only draws if ``world.has(requires)`` is true.
    requires: str | None = None

    def applies(self, world: World) -> bool:
        return self.requires is None or world.has(self.requires)

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:  # pragma: no cover
        raise NotImplementedError

    def rng(self, world: World) -> random.Random:
        return world.stream(self.name)


# --------------------------------------------------------------------------- #
# Background, defs, gradients, filters
# --------------------------------------------------------------------------- #
class Background(Layer):
    name = "background"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        start, end = world.palette.background
        doc.add_def(
            f'<linearGradient id="{doc.ref("space")}" x1="0%" x2="100%" y1="0%" y2="100%">'
            f'<stop offset="0%" stop-color="{start}" />'
            f'<stop offset="100%" stop-color="{end}" /></linearGradient>'
        )
        doc.add_def(
            f'<filter id="{doc.ref("soft")}" x="-30%" y="-30%" width="160%" height="160%">'
            '<feGaussianBlur stdDeviation="24" /></filter>'
        )
        doc.add_def(
            f'<filter id="{doc.ref("glow")}" x="-60%" y="-60%" width="220%" height="220%">'
            '<feGaussianBlur stdDeviation="5" result="blur" />'
            '<feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>'
            '</filter>'
        )
        doc.add(
            f'<rect width="{opts.width}" height="{opts.height}" fill="{doc.url("space")}" />'
        )


# --------------------------------------------------------------------------- #
# Nebula clouds
# --------------------------------------------------------------------------- #
class Nebula(Layer):
    name = "nebula"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        count = round(6 + 8 * world.density)
        shapes = []
        for _ in range(count):
            cx = rng.uniform(-0.05 * w, 1.05 * w)
            cy = rng.uniform(-0.05 * h, 1.05 * h)
            rx = rng.uniform(w * 0.08, w * 0.25)
            ry = rng.uniform(h * 0.06, h * 0.22)
            color = rng.choice(world.palette.nebula)
            opacity = rng.uniform(0.10, 0.18 + 0.18 * world.turbulence)
            rotation = rng.uniform(0, 180)
            shapes.append(
                f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(rx)}" ry="{fmt(ry)}" '
                f'fill="{color}" opacity="{opacity:.2f}" filter="{doc.url("soft")}" '
                f'transform="rotate({fmt(rotation)} {fmt(cx)} {fmt(cy)})" />'
            )

        attrs = ' style="mix-blend-mode: screen"'
        if opts.animate:
            amp = 6 + 10 * world.turbulence
            dur = rng.uniform(14, 24)
            doc.add_keyframes(
                "drift",
                f"from{{transform:translate(0,0)}}to{{transform:translate({fmt(amp)}px,{fmt(-amp * 0.6)}px)}}",
            )
            doc.add_rule(
                f".{doc.ref('drift')}{{animation:{doc.ref('drift')} {dur:.1f}s ease-in-out infinite alternate}}"
            )
            attrs += f' class="{doc.ref("drift")}"'
        doc.add(f"<g{attrs}>\n" + "\n".join(shapes) + "\n</g>")


# --------------------------------------------------------------------------- #
# Nebula clusters — tighter packs of overlapping cloudlets
# --------------------------------------------------------------------------- #
class NebulaClusters(Layer):
    """Dense sub-clusters of nebula blobs, each pack sharing a local centre.

    Uses its own RNG stream (``nebula_clusters``) so the base nebula wash is
    unchanged whether this layer is present or not.
    """

    name = "nebula_clusters"
    requires = "nebula_clusters"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        packs = rng.randint(2, 4)
        shapes: list[str] = []
        for _ in range(packs):
            px = rng.uniform(0.1 * w, 0.9 * w)
            py = rng.uniform(0.1 * h, 0.9 * h)
            members = rng.randint(3, 6)
            base_color = rng.choice(world.palette.nebula)
            for _ in range(members):
                cx = px + rng.uniform(-0.08 * w, 0.08 * w)
                cy = py + rng.uniform(-0.08 * h, 0.08 * h)
                rx = rng.uniform(w * 0.03, w * 0.09)
                ry = rng.uniform(h * 0.025, h * 0.08)
                color = base_color if rng.random() < 0.7 else rng.choice(world.palette.nebula)
                opacity = rng.uniform(0.08, 0.16 + 0.1 * world.turbulence)
                rotation = rng.uniform(0, 180)
                shapes.append(
                    f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(rx)}" ry="{fmt(ry)}" '
                    f'fill="{color}" opacity="{opacity:.2f}" filter="{doc.url("soft")}" '
                    f'transform="rotate({fmt(rotation)} {fmt(cx)} {fmt(cy)})" />'
                )
        doc.add(
            '<g style="mix-blend-mode: screen">\n' + "\n".join(shapes) + "\n</g>"
        )


# --------------------------------------------------------------------------- #
# Black hole — event horizon + accretion disk + photon ring
# --------------------------------------------------------------------------- #
class Blackhole(Layer):
    """A silhouette event horizon ringed by a glowing photon shell and a
    tilted accretion disk. Entirely driven by the ``blackhole`` stream."""

    name = "blackhole"
    requires = "blackhole"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        cx = w * rng.uniform(0.28, 0.72)
        cy = h * rng.uniform(0.28, 0.65)
        r = min(w, h) * rng.uniform(0.045, 0.09)
        tilt = rng.uniform(-28, 28)
        disk_color = rng.choice(world.palette.accent)
        hot = rng.choice(world.palette.stars)
        cool = rng.choice(world.palette.nebula)

        # Soft ambient glow behind the whole system.
        glow_id = doc.ref("bhglow")
        doc.add_def(
            f'<radialGradient id="{glow_id}" cx="50%" cy="50%" r="50%">'
            f'<stop offset="0%" stop-color="{hot}" stop-opacity="0.55" />'
            f'<stop offset="55%" stop-color="{disk_color}" stop-opacity="0.18" />'
            f'<stop offset="100%" stop-color="{disk_color}" stop-opacity="0" />'
            f"</radialGradient>"
        )
        parts: list[str] = [f'<g transform="rotate({fmt(tilt)} {fmt(cx)} {fmt(cy)})">']

        # Ambient glow.
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r * 3.2)}" '
            f'fill="url(#{glow_id})" opacity="0.85" />'
        )

        # Accretion disk — outer soft ellipse + inner brighter band.
        parts.append(
            f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(r * 2.8)}" ry="{fmt(r * 0.55)}" '
            f'fill="{disk_color}" opacity="0.22" filter="{doc.url("soft")}" />'
        )
        parts.append(
            f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(r * 2.15)}" ry="{fmt(r * 0.38)}" '
            f'fill="none" stroke="{hot}" stroke-width="{max(2.0, r * 0.18):.1f}" '
            f'opacity="0.55" filter="{doc.url("glow")}" />'
        )
        # Doppler-hot crescent on one side of the disk.
        parts.append(
            f'<ellipse cx="{fmt(cx + r * 0.9)}" cy="{fmt(cy)}" '
            f'rx="{fmt(r * 0.7)}" ry="{fmt(r * 0.22)}" '
            f'fill="{hot}" opacity="0.35" filter="{doc.url("soft")}" />'
        )
        parts.append(
            f'<ellipse cx="{fmt(cx - r * 0.85)}" cy="{fmt(cy)}" '
            f'rx="{fmt(r * 0.55)}" ry="{fmt(r * 0.18)}" '
            f'fill="{cool}" opacity="0.2" filter="{doc.url("soft")}" />'
        )

        # Photon ring — thin luminous shell just outside the horizon.
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r * 1.12)}" '
            f'fill="none" stroke="{hot}" stroke-width="{max(1.4, r * 0.12):.1f}" '
            f'opacity="0.9" filter="{doc.url("glow")}" />'
        )
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r * 1.05)}" '
            f'fill="none" stroke="{disk_color}" stroke-width="{max(0.8, r * 0.06):.1f}" '
            f'opacity="0.65" />'
        )

        # Event horizon — pure black silhouette.
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}" '
            f'fill="#000000" opacity="0.98" />'
        )
        # Faint lensing rim on the horizon edge.
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}" '
            f'fill="none" stroke="{hot}" stroke-width="0.6" opacity="0.25" />'
        )

        spin = ""
        if opts.animate:
            dur = rng.uniform(28, 55)
            spin = (
                f'<animateTransform attributeName="transform" type="rotate" '
                f'from="0 {fmt(cx)} {fmt(cy)}" to="360 {fmt(cx)} {fmt(cy)}" '
                f'dur="{dur:.0f}s" repeatCount="indefinite" additive="sum" />'
            )
        parts.append(spin)
        parts.append("</g>")
        doc.add("\n".join(parts))
        doc.shared["blackhole_center"] = (cx, cy, r)


# --------------------------------------------------------------------------- #
# Supernova remnant — expanding shell of glowing arcs
# --------------------------------------------------------------------------- #
class Supernova(Layer):
    """A supernova remnant: concentric faint arcs and filament wisps around a
    bright core. Driven solely by the ``supernova`` stream."""

    name = "supernova"
    requires = "supernova"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        cx = w * rng.uniform(0.2, 0.8)
        cy = h * rng.uniform(0.15, 0.75)
        base_r = min(w, h) * rng.uniform(0.08, 0.18)
        color = rng.choice(world.palette.nebula)
        accent = rng.choice(world.palette.accent)
        hot = rng.choice(world.palette.stars)

        parts: list[str] = ['<g style="mix-blend-mode: screen">']
        # Soft remnant core wash.
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(base_r * 0.45)}" '
            f'fill="{color}" opacity="0.14" filter="{doc.url("soft")}" />'
        )
        # Concentric remnant shells.
        shells = rng.randint(2, 4)
        for i in range(shells):
            rr = base_r * (0.55 + 0.35 * i + rng.uniform(-0.05, 0.05))
            op = 0.18 + 0.08 * world.brightness - i * 0.03
            stroke = accent if i % 2 == 0 else color
            dash = f"{rng.uniform(6, 18):.1f} {rng.uniform(10, 28):.1f}"
            parts.append(
                f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rr)}" '
                f'fill="none" stroke="{stroke}" stroke-width="{rng.uniform(1.2, 2.8):.1f}" '
                f'opacity="{max(0.06, op):.2f}" stroke-dasharray="{dash}" '
                f'filter="{doc.url("glow")}" />'
            )
        # Arc fragments / filament wisps.
        arcs = rng.randint(3, 6)
        for _ in range(arcs):
            start = rng.uniform(0, math.tau)
            sweep = rng.uniform(0.4, 1.4)
            rr = base_r * rng.uniform(0.5, 1.25)
            x1 = cx + math.cos(start) * rr
            y1 = cy + math.sin(start) * rr
            x2 = cx + math.cos(start + sweep) * rr
            y2 = cy + math.sin(start + sweep) * rr
            # Approximate arc with a quadratic bezier through the mid angle.
            mid = start + sweep / 2
            mx = cx + math.cos(mid) * rr * 1.08
            my = cy + math.sin(mid) * rr * 1.08
            parts.append(
                f'<path d="M {fmt(x1)} {fmt(y1)} Q {fmt(mx)} {fmt(my)} {fmt(x2)} {fmt(y2)}" '
                f'fill="none" stroke="{hot}" stroke-width="{rng.uniform(0.8, 1.8):.1f}" '
                f'opacity="{rng.uniform(0.2, 0.45):.2f}" stroke-linecap="round" '
                f'filter="{doc.url("glow")}" />'
            )
        parts.append("</g>")
        doc.add("\n".join(parts))


# --------------------------------------------------------------------------- #
# Galaxy — a logarithmic spiral of faint stars
# --------------------------------------------------------------------------- #
class Galaxy(Layer):
    name = "galaxy"
    requires = "galaxy"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        cx = w * rng.uniform(0.3, 0.7)
        cy = h * rng.uniform(0.3, 0.7)
        arms = rng.choice((2, 3, 4))
        scale = min(w, h) * rng.uniform(0.018, 0.03)
        twist = rng.uniform(0.22, 0.42)
        points_per_arm = round(70 + 90 * world.density)
        tilt = rng.uniform(-35, 35)
        squash = rng.uniform(0.45, 0.7)
        color = rng.choice(world.palette.nebula)
        star_color = world.palette.stars[0]

        dots = []
        for arm in range(arms):
            base = arm * (math.tau / arms)
            for i in range(points_per_arm):
                t = i / points_per_arm * rng.uniform(3.2, 4.0)
                radius = scale * math.exp(twist * t)
                jitter = rng.uniform(-0.18, 0.18) * radius
                angle = base + t
                px = cx + math.cos(angle) * (radius + jitter)
                py = cy + math.sin(angle) * (radius + jitter) * squash
                size = rng.uniform(0.4, 1.4)
                op = rng.uniform(0.2, 0.7) * (1 - i / points_per_arm * 0.6)
                fill = star_color if rng.random() < 0.7 else color
                dots.append(
                    f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="{fmt(size)}" '
                    f'fill="{fill}" opacity="{op:.2f}" />'
                )

        core = (
            f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(scale * 5)}" '
            f'ry="{fmt(scale * 5 * squash)}" fill="{color}" opacity="0.28" '
            f'filter="{doc.url("soft")}" />'
        )
        spin = ""
        if opts.animate:
            dur = rng.uniform(90, 150)
            spin = (
                f'<animateTransform attributeName="transform" type="rotate" '
                f'from="0 {fmt(cx)} {fmt(cy)}" to="360 {fmt(cx)} {fmt(cy)}" '
                f'dur="{dur:.0f}s" repeatCount="indefinite" additive="sum" />'
            )
        doc.add(
            f'<g transform="rotate({fmt(tilt)} {fmt(cx)} {fmt(cy)})" opacity="0.9">{spin}'
            + core
            + "\n"
            + "\n".join(dots)
            + "</g>"
        )
        # Share geometry so dust_lane can cut across the same spiral.
        doc.shared["galaxy"] = {
            "cx": cx,
            "cy": cy,
            "tilt": tilt,
            "squash": squash,
            "scale": scale,
            "arms": arms,
        }


# --------------------------------------------------------------------------- #
# Dust lane — dark absorption bands across a galaxy
# --------------------------------------------------------------------------- #
class DustLane(Layer):
    """Dark dust lanes cut across the galaxy disk when both ``galaxy`` and
    ``dust_lane`` features are on. Own stream ``dust_lane``."""

    name = "dust_lane"
    requires = "dust_lane"

    def applies(self, world: World) -> bool:
        return world.has("dust_lane") and world.has("galaxy")

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        geo = doc.shared.get("galaxy")
        if not geo:
            return
        rng = self.rng(world)
        cx = float(geo["cx"])  # type: ignore[index]
        cy = float(geo["cy"])  # type: ignore[index]
        tilt = float(geo["tilt"])  # type: ignore[index]
        squash = float(geo["squash"])  # type: ignore[index]
        scale = float(geo["scale"])  # type: ignore[index]
        shade = world.palette.background[0]
        deep = world.palette.background[1]

        lanes = rng.randint(2, 4)
        parts: list[str] = [
            f'<g transform="rotate({fmt(tilt)} {fmt(cx)} {fmt(cy)})" '
            f'style="mix-blend-mode: multiply">'
        ]
        for i in range(lanes):
            # Slightly offset curved bands across the disk major axis.
            offset = (i - (lanes - 1) / 2) * scale * rng.uniform(1.2, 2.4)
            length = scale * rng.uniform(18, 32)
            thickness = scale * rng.uniform(0.9, 2.2)
            # Soft ellipse = absorption lane.
            color = shade if i % 2 == 0 else deep
            op = rng.uniform(0.22, 0.42) * (0.7 + 0.3 * world.density)
            rot = rng.uniform(-12, 12)
            parts.append(
                f'<ellipse cx="{fmt(cx + offset * 0.15)}" cy="{fmt(cy + offset)}" '
                f'rx="{fmt(length)}" ry="{fmt(thickness * squash)}" '
                f'fill="{color}" opacity="{op:.2f}" filter="{doc.url("soft")}" '
                f'transform="rotate({fmt(rot)} {fmt(cx)} {fmt(cy)})" />'
            )
            # Thinner darker core of the lane.
            parts.append(
                f'<ellipse cx="{fmt(cx + offset * 0.1)}" cy="{fmt(cy + offset)}" '
                f'rx="{fmt(length * 0.85)}" ry="{fmt(thickness * squash * 0.35)}" '
                f'fill="{deep}" opacity="{min(0.55, op + 0.12):.2f}" '
                f'transform="rotate({fmt(rot)} {fmt(cx)} {fmt(cy)})" />'
            )
        parts.append("</g>")
        doc.add("\n".join(parts))


# --------------------------------------------------------------------------- #
# Pulsar — lighthouse beacon beams from a compact object
# --------------------------------------------------------------------------- #
class Pulsar(Layer):
    """Beacon beams / lighthouse pulses from a compact stellar remnant.

    Entirely driven by the ``pulsar`` stream so other layers stay stable.
    """

    name = "pulsar"
    requires = "pulsar"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        cx = w * rng.uniform(0.25, 0.75)
        cy = h * rng.uniform(0.2, 0.7)
        core_r = min(w, h) * rng.uniform(0.008, 0.018)
        beam_len = min(w, h) * rng.uniform(0.28, 0.55)
        n_beams = rng.choice((2, 2, 4))  # usually opposite pair
        base_angle = rng.uniform(0, math.tau)
        hot = rng.choice(world.palette.stars)
        accent = rng.choice(world.palette.accent)
        glow = rng.choice(world.palette.nebula)

        parts: list[str] = ['<g style="mix-blend-mode: screen">']
        # Soft ambient halo.
        halo_id = doc.ref("pshalo")
        doc.add_def(
            f'<radialGradient id="{halo_id}" cx="50%" cy="50%" r="50%">'
            f'<stop offset="0%" stop-color="{hot}" stop-opacity="0.85" />'
            f'<stop offset="40%" stop-color="{accent}" stop-opacity="0.25" />'
            f'<stop offset="100%" stop-color="{glow}" stop-opacity="0" />'
            f"</radialGradient>"
        )
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(core_r * 6)}" '
            f'fill="url(#{halo_id})" opacity="0.9" />'
        )

        # Lighthouse beams — tapered wedges of light.
        for i in range(n_beams):
            ang = base_angle + i * (math.tau / n_beams)
            half = rng.uniform(0.06, 0.12)  # half-width in radians
            # Outer tip of the beam.
            tip_x = cx + math.cos(ang) * beam_len
            tip_y = cy + math.sin(ang) * beam_len
            # Wide base near the core, tapering out — two side points near tip.
            side = beam_len * math.tan(half)
            px = -math.sin(ang) * side
            py = math.cos(ang) * side
            # Near-core width.
            near = core_r * 1.4
            nx = -math.sin(ang) * near
            ny = math.cos(ang) * near
            path = (
                f"M {fmt(cx + nx)} {fmt(cy + ny)} "
                f"L {fmt(tip_x + px)} {fmt(tip_y + py)} "
                f"L {fmt(tip_x - px)} {fmt(tip_y - py)} "
                f"L {fmt(cx - nx)} {fmt(cy - ny)} Z"
            )
            op = 0.12 + 0.18 * world.brightness
            parts.append(
                f'<path d="{path}" fill="{hot}" opacity="{op:.2f}" '
                f'filter="{doc.url("soft")}" />'
            )
            # Brighter spine of the beam.
            parts.append(
                f'<line x1="{fmt(cx)}" y1="{fmt(cy)}" '
                f'x2="{fmt(tip_x)}" y2="{fmt(tip_y)}" '
                f'stroke="{accent}" stroke-width="{max(0.8, core_r * 0.35):.1f}" '
                f'opacity="{0.35 + 0.25 * world.brightness:.2f}" '
                f'stroke-linecap="round" filter="{doc.url("glow")}" />'
            )

        # Compact object core.
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(core_r)}" '
            f'fill="{hot}" opacity="0.98" filter="{doc.url("glow")}" />'
        )
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(core_r * 0.45)}" '
            f'fill="#ffffff" opacity="0.9" />'
        )

        if opts.animate:
            dur = rng.uniform(4, 10)
            # Pulse opacity on the whole group via SMIL for self-contained SVG.
            parts.append(
                f'<animate attributeName="opacity" values="0.55;1;0.55" '
                f'dur="{dur:.1f}s" repeatCount="indefinite" />'
            )
            # Slow rotation of the beacon.
            spin_dur = rng.uniform(18, 40)
            parts.append(
                f'<animateTransform attributeName="transform" type="rotate" '
                f'from="0 {fmt(cx)} {fmt(cy)}" to="360 {fmt(cx)} {fmt(cy)}" '
                f'dur="{spin_dur:.0f}s" repeatCount="indefinite" />'
            )
        parts.append("</g>")
        doc.add("\n".join(parts))
        doc.shared["pulsar_center"] = (cx, cy, core_r)


# --------------------------------------------------------------------------- #
# Strange attractor — order out of chaos
# --------------------------------------------------------------------------- #
class Attractor(Layer):
    """A De Jong strange attractor: iterate a chaotic map thousands of times and
    plot where it lands. The four parameters come from the seed, so each phrase
    settles into its own luminous, deterministic swirl — chaos that never
    repeats yet always lands the same way for the same words."""

    name = "attractor"
    requires = "attractor"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        a = rng.uniform(-2.5, 2.5)
        b = rng.uniform(-2.5, 2.5)
        c = rng.uniform(-2.5, 2.5)
        d = rng.uniform(-2.5, 2.5)
        points = round(2600 + 2200 * world.density)

        cx = w * rng.uniform(0.42, 0.58)
        cy = h * rng.uniform(0.4, 0.55)
        scale = min(w, h) * 0.42 / 2.2  # De Jong stays within ~[-2.2, 2.2]
        color = rng.choice(world.palette.stars)

        x = y = 0.0
        segs = []
        for _ in range(points):
            nx = math.sin(a * y) - math.cos(b * x)
            ny = math.sin(c * x) - math.cos(d * y)
            x, y = nx, ny
            # "M X Y h.01" with a round linecap draws a single faint dot — far
            # more compact than thousands of <circle> elements.
            segs.append(f"M{fmt(cx + x * scale)} {fmt(cy + y * scale)}h.01")

        doc.add(
            f'<path d="{"".join(segs)}" stroke="{color}" stroke-width="0.9" '
            f'stroke-linecap="round" fill="none" '
            f'opacity="{0.42 + 0.3 * world.brightness:.2f}" filter="{doc.url("glow")}" />'
        )


# --------------------------------------------------------------------------- #
# Aurora band — a soft horizontal ribbon of light
# --------------------------------------------------------------------------- #
class AuroraBand(Layer):
    name = "aurora"
    requires = "aurora"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        bands = rng.choice((2, 3))
        ribbons = []
        for b in range(bands):
            y0 = h * rng.uniform(0.2, 0.7)
            amp = h * rng.uniform(0.03, 0.09)
            color = rng.choice(world.palette.accent)
            steps = 8
            top = []
            for s in range(steps + 1):
                x = w * s / steps
                y = y0 + math.sin(s * 0.9 + b) * amp
                top.append(f"{fmt(x)},{fmt(y)}")
            thickness = h * rng.uniform(0.04, 0.1)
            bottom = []
            for s in range(steps, -1, -1):
                x = w * s / steps
                y = y0 + math.sin(s * 0.9 + b) * amp + thickness
                bottom.append(f"{fmt(x)},{fmt(y)}")
            pts = " ".join(top + bottom)
            ribbons.append(
                f'<polygon points="{pts}" fill="{color}" opacity="0.16" '
                f'filter="{doc.url("soft")}" />'
            )
        doc.add('<g style="mix-blend-mode: screen">\n' + "\n".join(ribbons) + "\n</g>")


# --------------------------------------------------------------------------- #
# Filaments — structure GROWN by an L-system, not hand-placed
# --------------------------------------------------------------------------- #
class Filament(Layer):
    """A branching "cosmic web" grown by rewriting a string, then walked with a
    turtle. The shape isn't authored — it emerges from a tiny grammar, so two
    seeds with the same flag still grow visibly different tendrils."""

    name = "filament"
    requires = "filament"

    _RULES = {"X": "F-[[X]+X]+F[+FX]-X", "F": "FF"}

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height

        # Two rewrite passes give a sparse, recognisable branching plant
        # (three would tangle into a dense net).
        s = "X"
        for _ in range(2):
            s = "".join(self._RULES.get(c, c) for c in s)

        color = rng.choice(world.palette.accent)
        parts = [
            f'<g fill="none" stroke="{color}" stroke-width="0.9" '
            f'opacity="{0.12 + 0.08 * world.brightness:.2f}" '
            f'stroke-linecap="round" filter="{doc.url("glow")}">'
        ]
        for _ in range(rng.randint(1, 2)):
            x = rng.uniform(0.18 * w, 0.82 * w)
            y = h * rng.uniform(0.92, 0.99)  # root near the bottom
            angle = -90 + rng.uniform(-8, 8)  # grow nearly straight up
            step = min(w, h) * rng.uniform(0.018, 0.026)
            turn = rng.uniform(12, 17)  # narrow angle -> tree, not net
            parts.append(self._walk(s, x, y, angle, step, turn))
        parts.append("</g>")
        doc.add("\n".join(parts))

    @staticmethod
    def _walk(s: str, x: float, y: float, angle: float, step: float, turn: float) -> str:
        stack: list[tuple[float, float, float]] = []
        segs: list[str] = []
        for c in s:
            if c == "F":
                nx = x + math.cos(math.radians(angle)) * step
                ny = y + math.sin(math.radians(angle)) * step
                segs.append(f"M {fmt(x)} {fmt(y)} L {fmt(nx)} {fmt(ny)}")
                x, y = nx, ny
            elif c == "+":
                angle += turn
            elif c == "-":
                angle -= turn
            elif c == "[":
                stack.append((x, y, angle))
            elif c == "]" and stack:
                x, y, angle = stack.pop()
        return f'<path d="{" ".join(segs)}" />'


# --------------------------------------------------------------------------- #
# Grid — a faint perspective grid on the lower half
# --------------------------------------------------------------------------- #
class Grid(Layer):
    name = "grid"
    requires = "grid"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        horizon = h * rng.uniform(0.62, 0.74)
        color = world.palette.accent[-1]
        lines = [f'<g stroke="{color}" stroke-width="1" opacity="0.16" fill="none">']
        vanish = w * rng.uniform(0.4, 0.6)
        cols = 14
        for c in range(cols + 1):
            x = w * c / cols
            lines.append(f'<line x1="{fmt(x)}" y1="{fmt(h)}" x2="{fmt(vanish)}" y2="{fmt(horizon)}" />')
        rows = 8
        for r in range(1, rows + 1):
            frac = (r / rows) ** 2.2
            y = horizon + (h - horizon) * frac
            lines.append(f'<line x1="0" y1="{fmt(y)}" x2="{fmt(w)}" y2="{fmt(y)}" />')
        lines.append("</g>")
        doc.add("\n".join(lines))


# --------------------------------------------------------------------------- #
# Orbit lines
# --------------------------------------------------------------------------- #
class Orbits(Layer):
    name = "orbits"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        cx = w * rng.uniform(0.35, 0.65)
        cy = h * rng.uniform(0.35, 0.65)
        doc.shared["orbit_center"] = (cx, cy)
        orbit_count = max(3, opts.planets + 1)
        lines = ['<g fill="none" opacity="0.22">']
        for index in range(orbit_count):
            rx = w * (0.18 + index * 0.07) * rng.uniform(0.88, 1.12)
            ry = h * (0.10 + index * 0.04) * rng.uniform(0.88, 1.12)
            rotation = rng.uniform(-22, 22)
            color = world.palette.accent[index % len(world.palette.accent)]
            dash = f"{rng.uniform(4, 10):.1f} {rng.uniform(8, 22):.1f}"
            lines.append(
                f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(rx)}" ry="{fmt(ry)}" '
                f'stroke="{color}" stroke-width="1.2" stroke-dasharray="{dash}" '
                f'transform="rotate({fmt(rotation)} {fmt(cx)} {fmt(cy)})" />'
            )
        lines.append("</g>")
        doc.add("\n".join(lines))


# --------------------------------------------------------------------------- #
# Star field (and constellation source)
# --------------------------------------------------------------------------- #
class Starfield(Layer):
    name = "stars"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        points = []
        for _ in range(opts.stars):
            x = rng.uniform(0, w)
            y = rng.uniform(0, h)
            radius = rng.triangular(0.35, 2.4, 0.8)
            color = rng.choice(world.palette.stars)
            opacity = rng.uniform(0.38, 0.55 + 0.45 * world.brightness)
            points.append((x, y, radius, color, min(opacity, 1.0)))
        doc.shared["stars"] = points

        if opts.animate:
            doc.add_keyframes("twinkle", "from{opacity:0.25}to{opacity:1}")
            doc.add_rule(
                f".{doc.ref('tw')}{{animation:{doc.ref('twinkle')} 3s ease-in-out infinite alternate}}"
            )

        circles = ['<g>']
        for x, y, radius, color, opacity in points:
            extra = ""
            if opts.animate and rng.random() < 0.45:
                dur = rng.uniform(1.8, 4.5)
                delay = rng.uniform(0, 4)
                extra = f' class="{doc.ref("tw")}" style="animation-duration:{dur:.1f}s;animation-delay:{delay:.1f}s"'
            circles.append(
                f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{radius:.2f}" '
                f'fill="{color}" opacity="{opacity:.2f}"{extra} />'
            )
        circles.append("</g>")
        doc.add("\n".join(circles))


class Constellations(Layer):
    name = "constellations"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        points = doc.shared.get("stars", [])  # type: ignore[assignment]
        if not points:
            return
        rng = self.rng(world)
        bright = sorted(points, key=lambda p: p[2] * p[4], reverse=True)[:36]
        rng.shuffle(bright)
        groups = [bright[i : i + 6] for i in range(0, min(len(bright), 24), 6)]
        lines = ['<g fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.42">']
        for gi, group in enumerate(groups):
            if len(group) < 3:
                continue
            color = world.palette.accent[gi % len(world.palette.accent)]
            coords = [(x, y) for x, y, *_ in group]
            path = " ".join(
                f"{'M' if i == 0 else 'L'} {fmt(x)} {fmt(y)}" for i, (x, y) in enumerate(coords)
            )
            lines.append(f'<path d="{path}" stroke="{color}" stroke-width="1.4" />')
        lines.append("</g>")
        doc.add("\n".join(lines))


# --------------------------------------------------------------------------- #
# Comets / shooting stars
# --------------------------------------------------------------------------- #
class Comets(Layer):
    name = "comets"
    requires = "comets"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        count = rng.randint(2, 4)
        color = world.palette.stars[0]
        if opts.animate:
            doc.add_keyframes(
                "comet",
                "0%{transform:translate(0,0);opacity:0}"
                "8%{opacity:1}"
                f"100%{{transform:translate({fmt(w * 0.5)}px,{fmt(h * 0.32)}px);opacity:0}}",
            )
            doc.add_rule(
                f".{doc.ref('comet')}{{animation:{doc.ref('comet')} 6s linear infinite}}"
            )
        items = []
        for _ in range(count):
            x = rng.uniform(0, w * 0.7)
            y = rng.uniform(0, h * 0.6)
            length = rng.uniform(w * 0.05, w * 0.12)
            angle = math.radians(rng.uniform(20, 40))
            ex = x + math.cos(angle) * length
            ey = y + math.sin(angle) * length
            cls = ""
            if opts.animate:
                dur = rng.uniform(4.5, 9)
                delay = rng.uniform(0, 6)
                cls = f' class="{doc.ref("comet")}" style="animation-duration:{dur:.1f}s;animation-delay:{delay:.1f}s"'
            items.append(
                f"<g{cls}>"
                f'<line x1="{fmt(x)}" y1="{fmt(y)}" x2="{fmt(ex)}" y2="{fmt(ey)}" '
                f'stroke="{color}" stroke-width="1.6" opacity="0.7" stroke-linecap="round" />'
                f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="2.2" fill="{color}" '
                f'filter="{doc.url("glow")}" /></g>'
            )
        doc.add('<g>' + "\n".join(items) + "</g>")


# --------------------------------------------------------------------------- #
# Planets (optionally orbiting)
# --------------------------------------------------------------------------- #
class Planets(Layer):
    name = "planets"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        cx0, cy0 = doc.shared.get("orbit_center", (w * 0.5, h * 0.5))  # type: ignore[assignment]
        items = [f'<g filter="{doc.url("glow")}">']
        rings_on = world.has("rings")
        planet_positions: list[tuple[float, float, float]] = []
        for index in range(opts.planets):
            angle = rng.uniform(0, math.tau)
            distance_x = w * rng.uniform(0.12, 0.42)
            distance_y = h * rng.uniform(0.08, 0.32)
            cx = cx0 + math.cos(angle) * distance_x
            cy = cy0 + math.sin(angle) * distance_y
            radius = rng.uniform(min(w, h) * 0.018, min(w, h) * 0.052)
            fill = rng.choice(world.palette.planets)
            shade = rng.choice(world.palette.background)
            accent = rng.choice(world.palette.accent)

            spin = ""
            if opts.animate:
                dur = rng.uniform(40, 110)
                direction = "360" if index % 2 == 0 else "-360"
                spin = (
                    f'<animateTransform attributeName="transform" type="rotate" '
                    f'from="0 {fmt(cx0)} {fmt(cy0)}" to="{direction} {fmt(cx0)} {fmt(cy0)}" '
                    f'dur="{dur:.0f}s" repeatCount="indefinite" additive="sum" />'
                )
            body = [f"<g>{spin}"]
            body.append(
                f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(radius)}" fill="{fill}" opacity="0.96" />'
            )
            body.append(
                f'<circle cx="{fmt(cx - radius * 0.28)}" cy="{fmt(cy - radius * 0.25)}" '
                f'r="{fmt(radius * 0.38)}" fill="#ffffff" opacity="0.18" />'
            )
            body.append(
                f'<path d="M {fmt(cx - radius)} {fmt(cy + radius * 0.72)} '
                f'C {fmt(cx - radius * 0.2)} {fmt(cy + radius * 1.15)}, '
                f'{fmt(cx + radius * 0.75)} {fmt(cy + radius * 0.95)}, '
                f'{fmt(cx + radius)} {fmt(cy - radius * 0.1)}" '
                f'fill="none" stroke="{shade}" stroke-width="{max(2, radius * 0.12):.1f}" opacity="0.24" />'
            )
            if rings_on and index % 2 == 0:
                rotation = rng.uniform(-18, 18)
                body.append(
                    f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(radius * 1.75)}" ry="{fmt(radius * 0.38)}" '
                    f'fill="none" stroke="{accent}" stroke-width="{max(1.5, radius * 0.08):.1f}" '
                    f'opacity="0.72" transform="rotate({fmt(rotation)} {fmt(cx)} {fmt(cy)})" />'
                )
            body.append("</g>")
            items.append("".join(body))
            planet_positions.append((cx, cy, radius))
        items.append("</g>")
        doc.shared["planet_positions"] = planet_positions
        doc.add("\n".join(items))


# --------------------------------------------------------------------------- #
# Moon with craters
# --------------------------------------------------------------------------- #
class Moon(Layer):
    name = "moon"
    requires = "moon"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        cx = w * rng.uniform(0.62, 0.85)
        cy = h * rng.uniform(0.18, 0.4)
        radius = min(w, h) * rng.uniform(0.07, 0.12)
        fill = world.palette.stars[0]
        shade = world.palette.background[1]
        crater_color = world.palette.background[0]
        parts = [f'<g filter="{doc.url("glow")}">']
        parts.append(
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(radius)}" fill="{fill}" opacity="0.95" />'
        )
        # a soft terminator shadow
        parts.append(
            f'<circle cx="{fmt(cx + radius * 0.35)}" cy="{fmt(cy - radius * 0.1)}" '
            f'r="{fmt(radius * 0.95)}" fill="{shade}" opacity="0.22" />'
        )
        for _ in range(rng.randint(4, 7)):
            a = rng.uniform(0, math.tau)
            d = rng.uniform(0, radius * 0.7)
            crx = cx + math.cos(a) * d
            cry = cy + math.sin(a) * d
            cr = rng.uniform(radius * 0.05, radius * 0.18)
            parts.append(
                f'<circle cx="{fmt(crx)}" cy="{fmt(cry)}" r="{fmt(cr)}" '
                f'fill="{crater_color}" opacity="0.25" />'
            )
        parts.append("</g>")
        doc.add("\n".join(parts))


# --------------------------------------------------------------------------- #
# Wormhole — concentric distorted rings funneling toward a vanishing point
# --------------------------------------------------------------------------- #
class Wormhole(Layer):
    """Concentric, slightly distorted rings that spiral into a dark throat.

    Entirely driven by the ``wormhole`` stream so other layers stay stable.
    """

    name = "wormhole"
    requires = "wormhole"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        cx = w * rng.uniform(0.32, 0.68)
        cy = h * rng.uniform(0.28, 0.62)
        max_r = min(w, h) * rng.uniform(0.14, 0.28)
        rings = rng.randint(7, 12)
        accent = rng.choice(world.palette.accent)
        hot = rng.choice(world.palette.stars)
        cool = rng.choice(world.palette.nebula)
        twist = rng.uniform(0.08, 0.22)
        squash = rng.uniform(0.72, 0.95)

        parts: list[str] = ['<g style="mix-blend-mode: screen">']
        # Soft throat glow.
        throat_id = doc.ref("whthroat")
        doc.add_def(
            f'<radialGradient id="{throat_id}" cx="50%" cy="50%" r="50%">'
            f'<stop offset="0%" stop-color="#000000" stop-opacity="0.95" />'
            f'<stop offset="35%" stop-color="{cool}" stop-opacity="0.25" />'
            f'<stop offset="100%" stop-color="{accent}" stop-opacity="0" />'
            f"</radialGradient>"
        )
        parts.append(
            f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" '
            f'rx="{fmt(max_r * 1.05)}" ry="{fmt(max_r * squash * 1.05)}" '
            f'fill="url(#{throat_id})" opacity="0.9" />'
        )

        for i in range(rings):
            t = (i + 1) / rings
            # Funnel: outer rings large, inner rings collapse toward the throat.
            rr = max_r * (0.12 + 0.88 * (1.0 - t) ** 0.85)
            rot = twist * i * 28 + rng.uniform(-4, 4)
            stroke = hot if i % 3 == 0 else (accent if i % 2 == 0 else cool)
            op = 0.12 + 0.45 * t * (0.5 + 0.5 * world.brightness)
            sw = max(0.6, (2.8 - 2.0 * t) * (0.7 + 0.3 * world.density))
            # Mild radial distortion via dash pattern on alternate rings.
            dash = ""
            if i % 2 == 0:
                dash = f' stroke-dasharray="{rng.uniform(3, 9):.1f} {rng.uniform(4, 14):.1f}"'
            parts.append(
                f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" '
                f'rx="{fmt(rr)}" ry="{fmt(rr * squash)}" '
                f'fill="none" stroke="{stroke}" stroke-width="{sw:.2f}" '
                f'opacity="{op:.2f}" filter="{doc.url("glow")}"{dash} '
                f'transform="rotate({fmt(rot)} {fmt(cx)} {fmt(cy)})" />'
            )

        # Event-throat disc.
        core_r = max_r * rng.uniform(0.06, 0.11)
        parts.append(
            f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" '
            f'rx="{fmt(core_r)}" ry="{fmt(core_r * squash)}" '
            f'fill="#000000" opacity="0.96" />'
        )
        parts.append(
            f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" '
            f'rx="{fmt(core_r * 1.15)}" ry="{fmt(core_r * squash * 1.15)}" '
            f'fill="none" stroke="{hot}" stroke-width="0.8" opacity="0.55" />'
        )

        if opts.animate:
            dur = rng.uniform(40, 80)
            parts.append(
                f'<animateTransform attributeName="transform" type="rotate" '
                f'from="0 {fmt(cx)} {fmt(cy)}" to="360 {fmt(cx)} {fmt(cy)}" '
                f'dur="{dur:.0f}s" repeatCount="indefinite" additive="sum" />'
            )
        parts.append("</g>")
        doc.add("\n".join(parts))
        doc.shared["wormhole_center"] = (cx, cy, max_r)


# --------------------------------------------------------------------------- #
# Satellite — tiny craft / station near a planet
# --------------------------------------------------------------------------- #
class Satellite(Layer):
    """A small orbiting craft or station parked near a planet.

    Uses the ``satellite`` stream. Needs the planets layer to have placed at
    least one body (``doc.shared["planet_positions"]``); otherwise skips.
    """

    name = "satellite"
    requires = "satellite"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        if opts.planets <= 0:
            return
        positions = doc.shared.get("planet_positions") or []
        if not positions:
            return
        rng = self.rng(world)
        # Anchor on one of the earlier planets (deterministic choice).
        host = positions[rng.randrange(len(positions))]
        px, py, pr = host  # type: ignore[misc]
        angle = rng.uniform(0, math.tau)
        dist = pr * rng.uniform(1.8, 3.2)
        sx = px + math.cos(angle) * dist
        sy = py + math.sin(angle) * dist
        body_r = max(1.4, pr * rng.uniform(0.12, 0.22))
        hull = rng.choice(world.palette.stars)
        accent = rng.choice(world.palette.accent)
        panel = rng.choice(world.palette.nebula)

        parts: list[str] = [f'<g filter="{doc.url("glow")}">']
        # Solar panels.
        panel_w = body_r * 2.4
        panel_h = body_r * 0.55
        parts.append(
            f'<rect x="{fmt(sx - panel_w - body_r * 0.2)}" y="{fmt(sy - panel_h / 2)}" '
            f'width="{fmt(panel_w)}" height="{fmt(panel_h)}" '
            f'fill="{panel}" opacity="0.75" rx="0.6" />'
        )
        parts.append(
            f'<rect x="{fmt(sx + body_r * 0.2)}" y="{fmt(sy - panel_h / 2)}" '
            f'width="{fmt(panel_w)}" height="{fmt(panel_h)}" '
            f'fill="{panel}" opacity="0.75" rx="0.6" />'
        )
        # Central bus.
        parts.append(
            f'<rect x="{fmt(sx - body_r * 0.7)}" y="{fmt(sy - body_r * 0.55)}" '
            f'width="{fmt(body_r * 1.4)}" height="{fmt(body_r * 1.1)}" '
            f'fill="{hull}" opacity="0.95" rx="1" />'
        )
        # Antenna / dish.
        parts.append(
            f'<circle cx="{fmt(sx)}" cy="{fmt(sy - body_r * 0.95)}" r="{fmt(body_r * 0.35)}" '
            f'fill="none" stroke="{accent}" stroke-width="0.9" opacity="0.85" />'
        )
        parts.append(
            f'<line x1="{fmt(sx)}" y1="{fmt(sy - body_r * 0.55)}" '
            f'x2="{fmt(sx)}" y2="{fmt(sy - body_r * 0.95)}" '
            f'stroke="{accent}" stroke-width="0.8" opacity="0.8" />'
        )
        # Tiny beacon light.
        parts.append(
            f'<circle cx="{fmt(sx + body_r * 0.35)}" cy="{fmt(sy)}" r="{fmt(max(0.8, body_r * 0.18))}" '
            f'fill="{accent}" opacity="0.95" />'
        )

        # Thin local orbit arc around the host planet.
        orbit_rx = dist * rng.uniform(0.95, 1.05)
        orbit_ry = dist * rng.uniform(0.55, 0.85)
        tilt = math.degrees(angle) + rng.uniform(-20, 20)
        parts.append(
            f'<ellipse cx="{fmt(px)}" cy="{fmt(py)}" '
            f'rx="{fmt(orbit_rx)}" ry="{fmt(orbit_ry)}" '
            f'fill="none" stroke="{accent}" stroke-width="0.6" opacity="0.28" '
            f'stroke-dasharray="2 6" '
            f'transform="rotate({fmt(tilt)} {fmt(px)} {fmt(py)})" />'
        )

        if opts.animate:
            dur = rng.uniform(18, 40)
            parts.append(
                f'<animateTransform attributeName="transform" type="rotate" '
                f'from="0 {fmt(px)} {fmt(py)}" to="360 {fmt(px)} {fmt(py)}" '
                f'dur="{dur:.0f}s" repeatCount="indefinite" additive="sum" />'
            )
        parts.append("</g>")
        doc.add("\n".join(parts))


# --------------------------------------------------------------------------- #
# Horizon — a foreground silhouette
# --------------------------------------------------------------------------- #
class Horizon(Layer):
    name = "horizon"
    requires = "horizon"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        rng = self.rng(world)
        w, h = opts.width, opts.height
        base = h * rng.uniform(0.82, 0.92)
        color = world.palette.background[0]
        steps = 24
        pts = [f"0,{fmt(h)}"]
        y = base
        for s in range(steps + 1):
            x = w * s / steps
            y += rng.uniform(-h * 0.02, h * 0.02)
            y = max(base - h * 0.08, min(base + h * 0.04, y))
            pts.append(f"{fmt(x)},{fmt(y)}")
        pts.append(f"{fmt(w)},{fmt(h)}")
        doc.add(f'<polygon points="{" ".join(pts)}" fill="{color}" opacity="0.96" />')


# --------------------------------------------------------------------------- #
# Title / catalogue text
# --------------------------------------------------------------------------- #
class Title(Layer):
    name = "title"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        if not opts.show_title:
            return
        w, h = opts.width, opts.height
        title = opts.title if opts.title is not None else world.seed
        safe_title = esc(title[:80])
        safe_seed = esc(world.seed[:96])
        catalogue = esc(world.name.upper())
        caption = esc(world.caption[:90])
        accent = world.palette.accent[0]
        x = max(40, w * 0.045)
        y = h - max(56, h * 0.09)
        tag_size = max(11, w * 0.0115)
        doc.add(
            f'<g font-family="Avenir Next, Inter, Segoe UI, sans-serif">'
            f'<text x="{fmt(x)}" y="{fmt(max(34, h * 0.06))}" fill="{accent}" '
            f'font-size="{fmt(tag_size)}" letter-spacing="3" opacity="0.85">'
            f'STARWEAVE · {catalogue}</text>'
            f'<text x="{fmt(x)}" y="{fmt(y)}" fill="#f8fafc" '
            f'font-size="{fmt(max(32, w * 0.044))}" font-weight="800">{safe_title}</text>'
            f'<text x="{fmt(x)}" y="{fmt(y + 30)}" fill="{accent}" '
            f'font-size="{fmt(max(13, w * 0.013))}" opacity="0.88">seed: {safe_seed}</text>'
            f'<text x="{fmt(x)}" y="{fmt(y + 52)}" fill="#cbd5e1" '
            f'font-size="{fmt(max(12, w * 0.0115))}" opacity="0.7" font-style="italic">{caption}</text>'
            f'</g>'
        )


# --------------------------------------------------------------------------- #
# Hash stamp — optional corner micro-label
# --------------------------------------------------------------------------- #
class Stamp(Layer):
    """Tiny corner hash label; only paints when ``opts.stamp`` is true.

    The stamp string itself is computed in the scene (content hash of seed +
    params) and stored on ``doc.shared["stamp"]`` before layers run, or falls
    back to a short seed digest.
    """

    name = "stamp"

    def build(self, world: World, doc: SvgDoc, opts: RenderOptions) -> None:
        if not opts.stamp:
            return
        stamp = doc.shared.get("stamp") or world.seed[:8]
        w, h = opts.width, opts.height
        accent = world.palette.accent[-1]
        size = max(8, min(w, h) * 0.012)
        x = w - max(16, w * 0.02)
        y = h - max(12, h * 0.018)
        doc.add(
            f'<g font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
            f'text-anchor="end" opacity="0.45">'
            f'<text x="{fmt(x)}" y="{fmt(y)}" fill="{accent}" '
            f'font-size="{fmt(size)}" letter-spacing="1">{esc(str(stamp)[:16])}</text>'
            f"</g>"
        )


#: Layers in paint order (back to front). Conditional layers self-skip.
DEFAULT_LAYERS: tuple[Layer, ...] = (
    Background(),
    Nebula(),
    NebulaClusters(),
    Blackhole(),
    Wormhole(),
    Supernova(),
    Pulsar(),
    Galaxy(),
    DustLane(),
    Attractor(),
    AuroraBand(),
    Filament(),
    Grid(),
    Orbits(),
    Starfield(),
    Constellations(),
    Comets(),
    Planets(),
    Satellite(),
    Moon(),
    Horizon(),
    Title(),
    Stamp(),
)

#: Lookup by name, for the ``--only`` / ``--without`` CLI flags.
LAYERS_BY_NAME: dict[str, Layer] = {layer.name: layer for layer in DEFAULT_LAYERS}
