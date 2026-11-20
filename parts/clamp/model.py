"""The Clamp: holds a Cart seated and coaxial on the Battery with a fixed Stroke.

A Cradle spanning the Seat, the 12 mm Battery collar gripping the top of the Battery above
the fire button, the sliding Cart collar gripping the brass base, and the over-centre Lever
on the back (opposite the fire button), lying flat when locked.

The geometry is the Lever strip's, from `printlab.clamp` (frame and builders described
there), at one Stroke and without a label. Every joint that turns is assembled on a Pin
(ADR 0003). The `print` pose (the default, and what is exported) lays the bodies apart on
the bed without Pins; `closed` and `open` are the assembled Clamp, each Pin a `pin-…` body.

For pocket carry every sharp outside edge of a printed body (not in a bore, with a stretch
clear of every other body, Pins included) gets a 45° chamfer of `edge_break`; an edge that
only ends at a joint is still an outside edge. An edge facing a Pin is a joint, so no
break cuts into a Pin hole or its lead-in. The sections stay solid, for clear PETG.
"""

import math
from dataclasses import dataclass
from functools import lru_cache

from build123d import (
    Axis,
    Compound,
    Edge,
    Face,
    GeomType,
    Part,
    Vector,
    Wire,
    chamfer,
    extrude,
    revolve,
)

from printlab.clamp import (  # noqa: F401  cap_radius, fit_pairs, knuckle_radius, latch_arms: for the tests and the nudge audit
    ClampParams,
    battery_bore,
    cap_radius,
    cart_bore,
    fit_pairs,
    knuckle_radius,
    latch_arms,
    locked_bodies,
    pose_bodies,
)
from printlab.collar import Pose

GRAM_BUDGET = 5.0  # g, about what the Clamp on printed pins was; the CLI warns above this

SHARP_ANGLE = 115.0  # degrees; a convex edge whose faces meet under this is sharp
# Breaking an edge can bare the edge facing it on the next body, so passes run until one
# breaks nothing, each judging only edges near the last pass's breaks.
MAX_BREAK_PASSES = 4
SLIVER = 1e-3  # mm³; a solid this small left by a cut is a numerical scrap, dropped
SHORT_EDGE = 1e-3  # mm; an edge this short is a numerical scrap, never broken
SAME = 1e-6  # mm; points closer than this coincide
PROBE_STEP = 0.01  # mm a probe steps off an edge to see which side is solid
WALL_PROBE = 0.05  # mm a probe steps out from an edge toward a slanted wall
PARALLEL = 0.999  # |cos| above which two normals count as parallel


@dataclass(frozen=True)
class Params(ClampParams):
    # The shared Clamp sizes (`ClampParams`) start at the Test plate's middle bores.
    stroke: float = 0.6  # mm, the Lever strip's pick
    # Pocket carry
    footprint_limit: tuple[float, float] = (26.0, 30.0)  # mm, X × Y the Clamp may cover
    edge_break: float = 0.4  # mm, 45° chamfer on every sharp outside edge
    # mm past the gap within which an edge faces another body; covers an edge diagonally
    # across the gap from another body's edge (gap·√2)
    joint_margin: float = 0.2


def _faces_by_edge(body: Part) -> dict[Edge, list[Face]]:
    faces_of = {}
    for face in body.faces():
        for edge in face.edges():
            faces_of.setdefault(edge, []).append(face)
    return faces_of


def _bore_radius(p: Params) -> float:
    return max(battery_bore(p), cart_bore(p)) / 2


def _into_faces(edge: Edge, faces: list[Face], at: float) -> tuple[Vector, Vector, Vector]:
    """(point, direction into face 1, direction into face 2) at `at` along a convex edge;
    each direction is perpendicular to the edge, along its face."""
    q, tangent = edge.position_at(at), edge.tangent_at(at)
    n1, n2 = faces[0].normal_at(q), faces[1].normal_at(q)
    u1, u2 = tangent.cross(n1).normalized(), tangent.cross(n2).normalized()
    u1 = -u1 if u1.dot(n2) > 0 else u1
    u2 = -u2 if u2.dot(n1) > 0 else u2
    return q, u1, u2


def exposed_run(edge: Edge, others: Compound, reach: float, step: float) -> float:
    """The longest stretch of `edge` farther than `reach` from the other bodies.

    Judged at points at least `step` apart; a point d from the nearest body shows the next
    |d - reach| of edge is on the same side, so the walk strides over long clear stretches.
    """
    if edge.distance_to(others) > reach:
        return edge.length
    length, s, start, best = edge.length, 0.0, None, 0.0
    while True:
        d = others.distance_to(edge.position_at(s / length))
        if d > reach:
            start = s if start is None else start
            best = max(best, s - start)
        else:
            start = None
        if s >= length:
            return best
        s = min(length, s + max(step, abs(d - reach)))


def sharp_outside_edges(
    p: Params, bodies: dict[str, Part], name: str, near: Compound | None = None,
    tried: Compound | None = None,
) -> list[Edge]:
    """Sharp convex edges of one body that face the outside: not in a bore, and clear of
    every other body for at least `edge_break`, so any stretch longer than the run-out
    where two breaks meet (2 `edge_break`) is caught. An edge that only ends at a joint or
    parting line still faces outside. With `near`, only edges near it are judged; edges
    lying on one `tried` already (a run-out left by an earlier break) are left alone."""
    body = bodies[name]
    solid = body.solids()[0]
    others = Compound(children=[b for n, b in bodies.items() if n != name])
    reach = p.gap + p.joint_margin
    found = []
    for edge, faces in _faces_by_edge(body).items():
        if len(faces) != 2 or edge.length < SHORT_EDGE:
            continue
        q = edge.position_at(0.5)
        if math.hypot(q.X, q.Y) < _bore_radius(p):
            continue
        n1, n2 = faces[0].normal_at(q), faces[1].normal_at(q)
        between = 180 - math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2)))))
        if between >= SHARP_ANGLE or solid.is_inside(q + (n1 - n2) * PROBE_STEP):
            continue
        if near is not None and edge.distance_to(near) > reach + p.edge_break:
            continue
        if tried is not None and all(
            tried.distance_to(edge.position_at(u)) < SAME for u in (0, 0.5, 1)
        ):
            continue
        run = exposed_run(edge, others, reach, p.edge_break)
        if run < edge.length and run < p.edge_break:
            continue
        found.append(edge)
    return found


def _runs_into_a_slanted_wall(body: Part, edge: Edge, faces: list[Face], end: int,
                              size: float) -> bool:
    """Whether the edge's `end` (0 or 1) meets material beyond it across a wall that is not
    square to the edge, where a chamfer cut to the end would gouge that wall."""
    q, u1, u2 = _into_faces(edge, faces, end)
    out = edge.tangent_at(end) * (1 if end else -1)
    if not body.solids()[0].is_inside(q + out * WALL_PROBE + (u1 + u2) * (size / 4)):
        return False
    vertex = min(edge.vertices(), key=lambda v: (Vector(v) - q).length)
    walls = [f for f in body.faces() if f not in faces and any(vertex.is_same(v) for v in f.vertices())]
    return not all(
        w.geom_type == GeomType.PLANE and abs(w.normal_at(q).dot(out)) > PARALLEL for w in walls
    )


def _cutter(body: Part, edge: Edge, faces: list[Face], size: float) -> Part | None:
    """The material a 45° chamfer of `size` removes along a line or arc edge. Where the
    edge runs into a slanted wall the cut stops `size` short, leaving a short run-out."""
    if edge.geom_type not in (GeomType.LINE, GeomType.CIRCLE):
        return None
    closed = edge.is_closed
    trim = [0.0 if closed else size * _runs_into_a_slanted_wall(body, edge, faces, end, size)
            for end in (0, 1)]
    length = edge.length - sum(trim)
    if length <= SHORT_EDGE:
        return None
    start = trim[0] / edge.length
    q, u1, u2 = _into_faces(edge, faces, start)
    triangle = Face(Wire.make_polygon([q, q + u1 * size, q + u2 * size], close=True))
    if edge.geom_type == GeomType.LINE:
        return extrude(triangle, amount=length, dir=edge.tangent_at(start))
    centre, normal = edge.arc_center, edge.normal()
    if normal.cross(q - centre).dot(edge.tangent_at(start)) < 0:
        normal = -normal
    angle = 360.0 if closed else math.degrees(length / edge.radius)
    return revolve(triangle, Axis(centre, normal), angle)


def break_edges(p: Params, bodies: dict[str, Part]) -> dict[str, Part]:
    """Every printed body with each sharp outside edge chamfered by `edge_break`. Pins are
    not printed, so they are left as they are; an edge facing one is a joint, so no break
    cuts into a Pin hole."""
    near, tried = None, []
    for _ in range(MAX_BREAK_PASSES):
        bodies, broken = _break_pass(p, bodies, near, Compound(children=tried) if tried else None)
        if not broken:
            break
        near, tried = Compound(children=broken), tried + broken
    return bodies


def _break_pass(
    p: Params, bodies: dict[str, Part], near: Compound | None, tried: Compound | None
) -> tuple[dict[str, Part], list[Edge]]:
    """(bodies, edges broken): one pass of `break_edges`, judging only edges `near` the
    last pass's breaks (all edges on the first pass) and not `tried` already.

    OpenCascade's chamfer gives the cleanest corners, so each run of edges that share
    corners is chamfered by it; where it fails on a run, each edge's chamfer is cut out as
    a swept triangle instead.
    """
    broken, edges_broken = {}, []
    for name, body in bodies.items():
        if name.startswith("pin-"):
            broken[name] = body
            continue
        failed = []
        sharp = sharp_outside_edges(p, bodies, name, near, tried)
        edges_broken += sharp
        for run in _runs(sharp):
            # A chamfer may trim the end of a nearby edge in another run, so each edge is
            # found again on the body as it now stands.
            edges = [e for e in (_find(body, original) for original in run) if e is not None]
            try:
                done = chamfer(edges, p.edge_break)
                if done.is_valid and len(done.solids()) == 1:
                    body = done
                    continue
            except Exception:  # OCC raises a bare Exception on a failed chamfer
                pass
            failed += run
        if failed:
            faces_of = _faces_by_edge(body)
            edges = [e for e in (_find(body, original) for original in failed) if e is not None]
            body = body - [
                c for e in edges if (c := _cutter(body, e, faces_of[e], p.edge_break)) is not None
            ]
        broken[name] = _without_slivers(body)
    return broken, edges_broken


def _without_slivers(body: Part) -> Part:
    """The body less any sliver solid a cut left beside it."""
    solids = body.solids()
    if len(solids) < 2 or sorted(s.volume for s in solids)[-2] > SLIVER:
        return body
    return Part(Compound(children=[max(solids, key=lambda s: s.volume)]).wrapped)


def _runs(edges: list[Edge]) -> list[list[Edge]]:
    """The edges grouped into runs that share corners."""
    runs: list[list[Edge]] = []
    for edge in edges:
        touching = [r for r in runs if any(_share_corner(edge, e) for e in r)]
        merged = [edge] + [e for r in touching for e in r]
        runs = [r for r in runs if r not in touching] + [merged]
    return runs


def _share_corner(a: Edge, b: Edge) -> bool:
    return any(u.is_same(v) for u in a.vertices() for v in b.vertices())


def _find(body: Part, original: Edge) -> Edge | None:
    """The body's edge that is, or is what is left of, `original`: the longest edge lying
    on it. None if nothing of it is left."""
    mid, box = original.position_at(0.5), original.bounding_box()
    pad = Vector(SHORT_EDGE, SHORT_EDGE, SHORT_EDGE)
    lo, hi = box.min - pad, box.max + pad

    def within(q: Vector) -> bool:
        return lo.X <= q.X <= hi.X and lo.Y <= q.Y <= hi.Y and lo.Z <= q.Z <= hi.Z

    nearby = [e for e in body.edges() if within(e.position_at(0.5))]
    for e in nearby:
        if abs(e.length - original.length) < SAME and (e.position_at(0.5) - mid).length < SAME:
            return e
    on_it = [
        e for e in nearby
        if e.length > SHORT_EDGE and all(original.distance_to(e.position_at(u)) < SAME for u in (0, 0.5, 1))
    ]
    return max(on_it, key=lambda e: e.length, default=None)


@lru_cache(maxsize=4)
def _edge_broken(params: Params) -> dict[str, Part]:
    """The bodies locked, Pins too, edges broken. Cached: breaking takes most of a build,
    and each pose of the same Params reuses it."""
    return break_edges(params, locked_bodies(params, params.stroke))


def build(params: Params = Params(), pose: Pose | str = Pose.PRINT) -> dict[str, Part]:
    """The Clamp's named bodies in `pose` (see `Pose`)."""
    return pose_bodies(params, params.stroke, _edge_broken(params), pose)
