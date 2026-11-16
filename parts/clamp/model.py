"""The Clamp: holds a Cart seated and coaxial on the Battery with a fixed Stroke.

One print-in-place file, printed closed with the Battery axis vertical (Z): a Cradle
spanning the Seat, the 12 mm Battery collar gripping the top of the Battery above the
fire button, the sliding Cart collar gripping the brass base, and the over-centre Lever
on the back (opposite the fire button), lying flat when locked.

The geometry is the Lever strip's, from `printlab.clamp` (frame and builders described
there), at one Stroke and without a label. For pocket carry every sharp outside edge
(one not at a joint with another body, nor in a bore) gets a 45° chamfer of `edge_break`.
The sections stay solid, for clear PETG.
"""

import math
from dataclasses import dataclass

from build123d import Axis, Edge, Face, GeomType, Part, Vector, Wire, chamfer, extrude, revolve

from printlab.clamp import battery_bore, cart_bore, locked_bodies, pose_bodies

SHARP_ANGLE = 115.0  # degrees; a convex edge whose faces meet under this is sharp
JOINT_MARGIN = 0.1  # mm past the gap within which an edge faces another body (a joint)


@dataclass(frozen=True)
class Params:
    # Sizes the test prints pick; Cart sizes are estimates until then.
    battery_nominal_bore: float = 12.8  # mm, the Test plate's pick
    cart_nominal_bore: float = 12.2  # mm, the Test plate's pick
    stroke: float = 0.6  # mm, the Lever strip's pick
    fdm_offset: float = 0.2  # mm added to each bore; FDM holes print undersize
    # Collars (as the Lever strip)
    battery_collar_height: float = 12.0  # mm; its Latch runs full height to carry the Cart Latch
    wall: float = 1.3  # mm, collar ring wall (load-bearing)
    gap: float = 0.3  # mm, print-in-place clearance everywhere
    open_angle: float = 90.0  # degrees each Door swings in the open pose
    pin_diameter: float = 2.4  # mm, every pin: hinges and the Lever's three (load-bearing)
    knuckle_wall: float = 1.2  # mm, ring around each pin (load-bearing)
    knuckle_cone: float = 45.0  # degrees from vertical
    knuckle_facets: int = 16
    latch_height: float = 4.5  # mm, Cart collar Latch arm height
    arm_thickness: float = 1.4  # mm, radial; the arm bends in the XY plane
    arm_length: float = 8.0  # mm
    arm_root: float = 2.0  # mm
    catch_depth: float = 0.8  # mm
    catch_ramp: float = 2.5  # mm
    catch_flat: float = 1.0  # mm
    hook_length: float = 1.5  # mm
    hook_land: float = 0.5  # mm
    tab_width: float = 1.5  # mm
    tab_reach: float = 2.5  # mm
    # Cart collar. Cart sizes are estimates; the brass height is a ruler reading.
    brass_height: float = 10.0  # mm, Seat to ledge
    brass_margin: float = 1.0  # mm the collar stops short of the brass height
    glass_diameter: float = 11.9  # mm
    lip_clearance: float = 0.1  # mm per side
    lip_thickness: float = 0.8  # mm; the lip rests on the ledge with the Lever open
    travel: float = 2.0  # mm the collar may slide on its rib; the Stroke uses part of it
    rib_width: float = 2.0  # mm
    rib_head_width: float = 5.0  # mm
    rib_head_depth: float = 1.2  # mm
    rib_reach: float = 1.0  # mm of neck between the spine and the carriage
    carriage_wall: float = 1.2  # mm (load-bearing)
    # Cradle
    spine_depth: float = 2.0  # mm, the spine behind the collars (load-bearing)
    # Lever (over-centre toggle)
    toggle_x: float = 5.2  # mm, x of the Lever's outer face; the Link runs just outside
    pivot_offset: float = 3.4  # mm from the Cradle's back face to the pivot axis
    crank_radius: float = 3.0  # mm, pivot to crank pin
    link_length: float = 13.0  # mm, crank pin to Link pin
    overtravel: float = 8.0  # degrees the crank sits past centre when locked
    centre_drop_cap: float = 0.1  # mm, most the collar may drop past the Stroke at centre
    link_pin_height: float = 2.5  # mm, Link pin above the Cart collar's underside
    lever_width: float = 3.0  # mm, along X
    link_width: float = 2.0  # mm, along X
    lug_width: float = 2.0  # mm, along X: the Cradle lug carrying the pivot pin
    head_width: float = 1.2  # mm, along X: pin heads that keep the Link on
    head_size: float = 2.4  # mm, half-diagonal of each diamond pin head
    # Pocket carry
    edge_break: float = 0.4  # mm, 45° chamfer on every sharp outside edge


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
    q, t = edge.position_at(at), edge.tangent_at(at)
    n1, n2 = faces[0].normal_at(q), faces[1].normal_at(q)
    u1, u2 = t.cross(n1).normalized(), t.cross(n2).normalized()
    u1 = -u1 if u1.dot(n2) > 0 else u1
    u2 = -u2 if u2.dot(n1) > 0 else u2
    return q, u1, u2


def sharp_outside_edges(p: Params, bodies: dict[str, Part], name: str) -> list[Edge]:
    """Sharp convex edges of one body that face the outside: not a joint or parting line
    (within the gap of another body) and not in a bore."""
    body = bodies[name]
    solid = body.solids()[0]
    others = [b for n, b in bodies.items() if n != name]
    found = []
    for edge, faces in _faces_by_edge(body).items():
        if len(faces) != 2 or edge.length < 1e-3:
            continue
        q = edge.position_at(0.5)
        if math.hypot(q.X, q.Y) < _bore_radius(p):
            continue
        n1, n2 = faces[0].normal_at(q), faces[1].normal_at(q)
        between = 180 - math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2)))))
        if between >= SHARP_ANGLE or solid.is_inside(q + (n1 - n2) * 0.01):
            continue
        if any(edge.distance_to(o) <= p.gap + JOINT_MARGIN for o in others):
            continue
        found.append(edge)
    return found


def _runs_into_a_slanted_wall(body: Part, edge: Edge, faces: list[Face], end: int,
                              size: float) -> bool:
    """Whether the edge's `end` (0 or 1) meets material beyond it across a wall that is not
    square to the edge, where a chamfer cut to the end would gouge that wall."""
    q, u1, u2 = _into_faces(edge, faces, end)
    out = edge.tangent_at(end) * (1 if end else -1)
    if not body.solids()[0].is_inside(q + out * 0.05 + (u1 + u2) * (size / 4)):
        return False
    vertex = min(edge.vertices(), key=lambda v: (Vector(v) - q).length)
    walls = [f for f in body.faces() if f not in faces and any(vertex.is_same(v) for v in f.vertices())]
    return not all(
        w.geom_type == GeomType.PLANE and abs(w.normal_at(q).dot(out)) > 0.999 for w in walls
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
    if length <= 1e-3:
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
    """Every body with each sharp outside edge chamfered by `edge_break`.

    OpenCascade's chamfer gives the cleanest corners, so each run of edges that share
    corners is chamfered by it; where it fails on a run, each edge's chamfer is cut out as
    a swept triangle instead.
    """
    broken = {}
    for name, body in bodies.items():
        failed = []
        for run in _runs(sharp_outside_edges(p, bodies, name)):
            # Runs share no corners, so a chamfer leaves the other runs' edges as they were.
            marks = [(e.position_at(0.5), e.length) for e in run]
            try:
                done = chamfer([_find(body, *m) for m in marks], p.edge_break)
                if done.is_valid and len(done.solids()) == 1:
                    body = done
                    continue
            except Exception:  # OCC raises a bare Exception on a failed chamfer
                pass
            failed += marks
        if failed:
            faces_of = _faces_by_edge(body)
            edges = [_find(body, *m) for m in failed]
            body = body - [
                c for e in edges if (c := _cutter(body, e, faces_of[e], p.edge_break)) is not None
            ]
        broken[name] = body
    return broken


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


def _find(body: Part, midpoint: Vector, length: float) -> Edge:
    """The body's edge with this midpoint and length."""
    return next(
        e for e in body.edges()
        if abs(e.length - length) < 1e-6 and (e.position_at(0.5) - midpoint).length < 1e-6
    )


def build(params: Params = Params(), pose: str = "closed") -> dict[str, Part]:
    """The Clamp's named bodies in `pose`: "closed" (printed), "open" or "centre"."""
    bodies = break_edges(params, locked_bodies(params, params.stroke))
    return pose_bodies(params, params.stroke, bodies, pose)
