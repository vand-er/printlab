"""Clamp builders shared by the Lever strip and the full Clamp: Cradle, collars, Lever, Link.

A Clamp is a Cradle carrying a Battery collar, a sliding Cart collar stacked on it and an
over-centre Lever. The Lever pivots on the back of the Cradle (opposite the fire button);
a Link from its crank pin to a pin on the Cart collar pulls the collar down by the Stroke
as the Lever goes over centre. The stop is the Lever lying flat on the Cradle. Everything
prints closed and in place, Battery axis vertical (Z), Lever locked.

Clamp frame: the collars' frame from `printlab.collar` (bore on the Z axis, Doors on +Y,
hinges on -X, Latches on +X). The Cradle's back stands behind the collars (-Y). The
Lever, Link and pin heads are layers along X on the +X side, so each moves in a YZ plane:

    lug | Lever | Link | pin heads        (lever_face_x is the Lever's outer face)

Every body's underside rests on the bed or, across a `gap`, on the body below it: the
Cart collar prints on top of the Battery collar, so the Battery Latch runs full height
under the Cart Latch.

Builders take the part's `Params`, a `ClampParams`.
"""

import math
from dataclasses import dataclass

from build123d import (
    Align,
    Axis,
    Cylinder,
    Edge,
    Face,
    Part,
    Plane,
    Polygon,
    Pos,
    Rot,
    Wire,
    extrude,
)

from printlab.collar import (
    EMBED,
    FUSE,
    CollarParams,
    Pose,
    bore,
    bore_cut,
    box,
    carriage_back_y,
    carriage_half_width,
    cart_body,
    cart_collar_height,
    cart_door,
    cart_rib,
    cradle_stub,
    door,
    knuckle_radius,
    latch_arm,
    outer_radius,
    pose_door,
)

# Numerical settings, not printed dimensions.
SOLVE_STEPS = 100  # bisection steps when solving the crank angle for a stroke
CIRCLE_FACETS = 48  # facets of a circle used as an outline
HULL_FACETS = 720  # facets per disc when finding which discs a hull runs round
DIGITS = 9  # decimals points are rounded to before comparing them
SAME = 1e-6  # mm (or radians); values closer than this coincide


@dataclass(frozen=True)
class ClampParams(CollarParams):
    """The sizes every Clamp builder reads: the collar sizes plus the Cradle and Lever."""

    # Bores: the Test plate's middle sizes until it picks them
    battery_nominal_bore: float = 12.8  # mm, labelled size
    cart_nominal_bore: float = 12.2  # mm, labelled size
    battery_collar_height: float = 12.0  # mm; its Latch runs full height to carry the Cart Latch
    # Cradle
    cradle_back_depth: float = 2.0  # mm, the Cradle's back behind the collars (load-bearing)
    # Lever (over-centre linkage)
    lever_face_x: float = 5.2  # mm, x of the Lever's outer face; the Link runs just outside
    pivot_offset: float = 3.4  # mm from the Cradle's back face to the pivot axis
    crank_radius: float = 3.0  # mm, pivot to crank pin
    link_length: float = 13.0  # mm, crank pin to Link pin
    past_centre: float = 8.0  # degrees the crank sits past dead centre when locked
    centre_drop_cap: float = 0.1  # mm, most the collar may drop past the Stroke at centre
    link_pin_height: float = 2.5  # mm, Link pin above the Cart collar's underside
    lever_width: float = 3.0  # mm, along X
    link_width: float = 2.0  # mm, along X
    lug_width: float = 2.0  # mm, along X: the Cradle lug carrying the pivot pin
    head_width: float = 1.2  # mm, along X: pin heads that keep the Link on
    head_size: float = 2.4  # mm, half-diagonal of each diamond pin head


# --- Sizes derived from Params ---


def battery_bore(p: ClampParams) -> float:
    return bore(p, p.battery_nominal_bore)


def cart_bore(p: ClampParams) -> float:
    return bore(p, p.cart_nominal_bore)


def cart_floor_z(p: ClampParams) -> float:
    """z of the Cart collar's underside, locked: a `gap` above the Battery collar."""
    return p.battery_collar_height + p.gap


def cradle_back_y(p: ClampParams) -> tuple[float, float]:
    """(back, front) y of the Cradle's back; the front is where the rib's neck starts."""
    front = carriage_back_y(p, cart_bore(p)) - p.rib_reach
    return front - p.cradle_back_depth, front


def _boss_radius(p: ClampParams) -> float:
    """Outer radius of material carrying a pin."""
    return p.pin_diameter / 2 + p.knuckle_wall


def _ear_y(p: ClampParams) -> tuple[float, float]:
    """(back, front) y of the Cart collar's ear, which carries the Link pin."""
    _, front = cradle_back_y(p)
    return front + p.gap, -(outer_radius(p, cart_bore(p)) - p.wall / 2)


def linkage_layers(p: ClampParams) -> dict[str, tuple[float, float]]:
    """X extents of the linkage's layers: lug, Lever, Link and pin heads."""
    x = p.lever_face_x
    lever = (x - p.lever_width, x)
    lug = (lever[0] - p.gap - p.lug_width, lever[0] - p.gap)
    link = (x + p.gap, x + p.gap + p.link_width)
    head = (link[1] + p.gap, link[1] + p.gap + p.head_width)
    return {"lug": lug, "lever": lever, "link": link, "head": head}


# --- Over-centre linkage kinematics (YZ plane) ---


@dataclass(frozen=True)
class Linkage:
    """Pivot P on the Cradle, crank pin C on the Lever, Link pin L on the Cart collar.

    L slides along Z at y = link_y. Crank angles are measured in the YZ plane from +Y
    towards +Z (a positive rotation about +X). The collar is lowest with P between C and
    L (dead centre); locked is `past_centre` past it, towards the stop.
    """

    pivot: tuple[float, float]  # (y, z)
    radius: float
    length: float
    link_y: float
    centre: float  # crank angle at dead centre, radians
    locked: float
    opened: float

    def crank(self, angle: float) -> tuple[float, float]:
        y, z = self.pivot
        return y + self.radius * math.cos(angle), z + self.radius * math.sin(angle)

    def link_pin(self, angle: float) -> tuple[float, float]:
        cy, cz = self.crank(angle)
        return self.link_y, cz + math.sqrt(self.length**2 - (self.link_y - cy) ** 2)

    def angle(self, pose: Pose | str) -> float:
        return {Pose.CLOSED: self.locked, Pose.OPEN: self.opened, Pose.CENTRE: self.centre}[
            Pose(pose)
        ]


def solve_linkage(
    p: ClampParams, stroke: float, pivot_y: float, link_y: float, link_z: float
) -> Linkage:
    """The linkage whose Link pin sits at (link_y, link_z) when locked and rises by `stroke`
    when the Lever opens. The pivot height follows from the locked pose."""
    r, length = p.crank_radius, p.link_length
    dy = link_y - pivot_y
    reach = length - r  # pivot to Link pin at dead centre
    if reach <= abs(dy):
        raise ValueError("Link too short to reach past the pivot")
    centre = math.atan2(-math.sqrt(reach**2 - dy**2), -dy)
    locked = centre + math.radians(p.past_centre)

    def rise(angle):  # Link pin height above the pivot
        return r * math.sin(angle) + math.sqrt(length**2 - (dy - r * math.cos(angle)) ** 2)

    # Opening turns the crank back through centre; the pin rises until the far dead centre.
    lo, hi = locked - centre, locked - centre + math.pi
    if rise(locked - hi) - rise(locked) < stroke:
        raise ValueError(f"stroke {stroke} mm is beyond this linkage")
    for _ in range(SOLVE_STEPS):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if rise(locked - mid) - rise(locked) < stroke else (lo, mid)
    pivot = (pivot_y, link_z - rise(locked))
    return Linkage(pivot, r, length, link_y, centre, locked, locked - (lo + hi) / 2)


def clamp_linkage(p: ClampParams, stroke: float) -> Linkage:
    """This Clamp's linkage: pivot behind the Cradle's back, Link pin on the Cart collar's ear."""
    back, _ = cradle_back_y(p)
    ear_back, ear_front = _ear_y(p)
    link_z = cart_floor_z(p) + p.link_pin_height
    return solve_linkage(p, stroke, back - p.pivot_offset, (ear_back + ear_front) / 2, link_z)


# --- Solids ---


def _yz_prism(points: list[tuple[float, float]], x0: float, x1: float) -> Part:
    """A YZ outline swept along X from x0 to x1."""
    return Pos(x0, 0, 0) * extrude(Plane.YZ * Polygon(*points, align=None), x1 - x0)


def _x_pin(radius: float, centre: tuple[float, float], x0: float, x1: float) -> Part:
    """A round pin along X."""
    return Pos(x0, *centre) * Rot(0, 90, 0) * Cylinder(
        radius, x1 - x0, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def _circle(centre: tuple[float, float], radius: float, n: int = CIRCLE_FACETS) -> list[tuple[float, float]]:
    y, z = centre
    return [(y + radius * math.cos(2 * math.pi * i / n), z + radius * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def _hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convex hull, anticlockwise (Andrew's monotone chain)."""
    pts = sorted(set((round(y, DIGITS), round(z, DIGITS)) for y, z in points))

    def half(seq):
        out = []
        for q in seq:
            while len(out) >= 2 and (
                (out[-1][0] - out[-2][0]) * (q[1] - out[-2][1])
                - (out[-1][1] - out[-2][1]) * (q[0] - out[-2][0])
            ) <= 0:
                out.pop()
            out.append(q)
        return out

    lower, upper = half(pts), half(reversed(pts))
    return lower[:-1] + upper[:-1]


Disc = tuple[tuple[float, float], float]  # ((y, z), radius); radius 0 is a corner


def _disc_hull_prism(discs: list[Disc], x0: float, x1: float) -> Part:
    """The convex hull of discs in the YZ plane, with true arcs and tangent lines, swept
    along X from x0 to x1. True arcs, not facets, so its edges chamfer cleanly."""
    # Which discs the hull runs round, in order: from the hull of finely faceted discs.
    owner = {}
    for i in sorted(range(len(discs)), key=lambda i: discs[i][1]):  # larger discs win ties
        (y, z), r = discs[i]
        points = _circle((y, z), r, HULL_FACETS) if r > 0 else [(y, z)]
        owner.update({(round(a, DIGITS), round(b, DIGITS)): i for a, b in points})
    order = [owner[q] for q in _hull(list(owner))]
    order = [i for k, i in enumerate(order) if i != order[k - 1]]

    def tangent(a: Disc, b: Disc) -> tuple[tuple[float, float], tuple[float, float]]:
        """Points where the outer tangent from a to b (hull on its left) touches each."""
        (ya, za), ra = a
        (yb, zb), r_b = b
        dy, dz = yb - ya, zb - za
        length = math.hypot(dy, dz)
        cos_t = (ra - r_b) / length
        sin_t = math.sqrt(max(0.0, 1 - cos_t * cos_t))
        ny = cos_t * dy / length + sin_t * dz / length
        nz = cos_t * dz / length - sin_t * dy / length
        return (ya + ra * ny, za + ra * nz), (yb + r_b * ny, zb + r_b * nz)

    lines = [tangent(discs[a], discs[b]) for a, b in zip(order, order[1:] + order[:1])]
    edges = []
    for k, i in enumerate(order):
        (y, z), r = discs[i]
        start, end = lines[k - 1][1], lines[k][0]  # arrive from the last line, leave on the next
        if r > 0:
            a0 = math.atan2(start[1] - z, start[0] - y)
            a1 = math.atan2(end[1] - z, end[0] - y)
            sweep = (a1 - a0) % (2 * math.pi)
            if sweep > SAME:
                mid = a0 + sweep / 2
                edges.append(Edge.make_three_point_arc(
                    (x0, *start), (x0, y + r * math.cos(mid), z + r * math.sin(mid)), (x0, *end)
                ))
        if math.dist(lines[k][0], lines[k][1]) > SAME:
            edges.append(Edge.make_line((x0, *lines[k][0]), (x0, *lines[k][1])))
    face = Face(Wire(edges))
    return extrude(face, amount=x1 - x0, dir=(1, 0, 0))


def _rect(y0: float, y1: float, z0: float, z1: float) -> list[tuple[float, float]]:
    return [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]


def _pin_with_head(p: ClampParams, centre: tuple[float, float], x0: float) -> Part:
    """A pin from x0 out through the Link, ending in a diamond head that keeps the Link on.

    The diamond's lowest corner is on the pin's axis, so the head grows out of the pin at
    45° and prints unsupported.
    """
    y, z = centre
    h0, h1 = linkage_layers(p)["head"]
    s = p.head_size
    head = _yz_prism([(y, z), (y + s, z + s), (y, z + 2 * s), (y - s, z + s)], h0, h1)
    return _x_pin(p.pin_diameter / 2, centre, x0, h1) + head


def battery_collar(p: ClampParams) -> tuple[Part, Part]:
    """(Cradle stub, Door) of the Battery collar; the Latch runs full height."""
    bore_d, h = battery_bore(p), p.battery_collar_height
    return cradle_stub(p, bore_d, h, latch_height=h), door(p, bore_d, h, latch_height=h)


def cradle(p: ClampParams, stroke: float) -> Part:
    """The Cradle: Battery collar stub, its back, rib for the Cart collar, and the pivot lug
    with its pin."""
    linkage = clamp_linkage(p, stroke)
    back, front = cradle_back_y(p)
    hw = carriage_half_width(p)
    hb = p.battery_collar_height
    top = cart_floor_z(p) + cart_collar_height(p)
    stub, _ = battery_collar(p)
    # Its back runs full width up to the Battery collar's top, under the Cart collar and
    # behind the lug and the Lever's stop; above, it carries only the rib, so it is only
    # as wide as the rib's head.
    head_hw = p.rib_head_width / 2
    cradle_back = box(-hw, p.lever_face_x, back, front, hb) + box(
        -head_hw, head_hw, back, front, top, z0=hb - EMBED
    )
    ring_inside = -(outer_radius(p, battery_bore(p)) - p.wall / 2)
    web = box(-hw, p.lever_face_x, front - EMBED, ring_inside, hb)
    # The rib, with its neck run down into the web so it stands on it.
    rib = Pos(0, 0, cart_floor_z(p)) * cart_rib(p, cart_bore(p), cart_collar_height(p))
    head_front = carriage_back_y(p, cart_bore(p)) + p.carriage_wall + p.gap + p.rib_head_depth
    neck = box(-p.rib_width / 2, p.rib_width / 2, front - EMBED, head_front,
               cart_floor_z(p) + FUSE, z0=hb - EMBED)
    lx0, lx1 = linkage_layers(p)["lug"]
    py, pz = linkage.pivot
    lug = box(lx0, lx1, py - _boss_radius(p), back + EMBED, pz + _boss_radius(p))
    pin = _x_pin(p.pin_diameter / 2, linkage.pivot, lx1 - EMBED, p.lever_face_x)
    body = stub + cradle_back + web + rib + neck + lug + pin
    return body - bore_cut(battery_bore(p), hb)


def cart_collar(p: ClampParams, stroke: float) -> tuple[Part, Part]:
    """(sliding body, Door) of the Cart collar, locked. The body carries an ear on its
    carriage's +X side with the Link pin."""
    linkage = clamp_linkage(p, stroke)
    bore_d, h = cart_bore(p), cart_collar_height(p)
    ear_back, ear_front = _ear_y(p)
    ear = box(carriage_half_width(p) - FUSE, p.lever_face_x, ear_back, ear_front, h)
    lift = Pos(0, 0, cart_floor_z(p))
    pin = _pin_with_head(p, linkage.link_pin(linkage.locked), p.lever_face_x - EMBED)
    return lift * (cart_body(p, bore_d, h) + ear) + pin, lift * cart_door(p, bore_d, h)


def lever(p: ClampParams, linkage: Linkage) -> Part:
    """The Lever, locked: a convex plate from the pivot hub down to the bed, its front lying
    flat a `gap` off the Cradle's back (the stop), with the crank pin and its head."""
    back, _ = cradle_back_y(p)
    crank = linkage.crank(linkage.locked)
    boss_r = _boss_radius(p)
    corners = [(q, 0.0) for q in _rect(crank[0] - boss_r, back - p.gap, 0, linkage.pivot[1])]
    x0, x1 = linkage_layers(p)["lever"]
    body = _disc_hull_prism([(linkage.pivot, knuckle_radius(p)), (crank, boss_r)] + corners, x0, x1)
    body = body - _x_pin(p.pin_diameter / 2 + p.gap, linkage.pivot, x0 - 1, x1 + 1)
    return body + _pin_with_head(p, crank, x1 - EMBED)


def link(p: ClampParams, linkage: Linkage) -> Part:
    """The Link, locked: eyes on the crank pin and the Link pin, and a foot under the
    crank eye down to the bed."""
    crank, link_pin = linkage.crank(linkage.locked), linkage.link_pin(linkage.locked)
    eye_r = knuckle_radius(p)
    corners = [(q, 0.0) for q in _rect(crank[0] - eye_r, crank[0] + eye_r, 0, crank[1])]
    x0, x1 = linkage_layers(p)["link"]
    hole = p.pin_diameter / 2 + p.gap
    outline = _disc_hull_prism([(crank, eye_r), (link_pin, eye_r)] + corners, x0, x1)
    return outline - _x_pin(hole, crank, x0 - 1, x1 + 1) - _x_pin(
        hole, link_pin, x0 - 1, x1 + 1
    )


def locked_bodies(p: ClampParams, stroke: float) -> dict[str, Part]:
    """One Clamp's bodies as printed: Doors shut, Lever locked."""
    linkage = clamp_linkage(p, stroke)
    _, battery_door = battery_collar(p)
    cart_slider, cart_collar_door = cart_collar(p, stroke)
    return {
        "cradle": cradle(p, stroke),
        "battery-door": battery_door,
        "cart-body": cart_slider,
        "cart-door": cart_collar_door,
        "lever": lever(p, linkage),
        "link": link(p, linkage),
    }


def latch_arms(p: ClampParams) -> dict[str, Part]:
    """Each Door's Latch arm, placed as printed (closed, Lever locked), by Door body name."""
    return {
        "battery-door": latch_arm(p, battery_bore(p), p.battery_collar_height),
        "cart-door": Pos(0, 0, cart_floor_z(p)) * latch_arm(p, cart_bore(p)),
    }


def _x_axis(centre: tuple[float, float]) -> Axis:
    return Axis((0, *centre), (1, 0, 0))


def pose_bodies(
    p: ClampParams, stroke: float, bodies: dict[str, Part], pose: Pose | str
) -> dict[str, Part]:
    """Locked `bodies` moved to `pose` (see `Pose`)."""
    linkage = clamp_linkage(p, stroke)
    angle = linkage.angle(pose)
    doors = Pose.OPEN if Pose(pose) == Pose.OPEN else Pose.CLOSED
    lift = Pos(0, 0, linkage.link_pin(angle)[1] - linkage.link_pin(linkage.locked)[1])
    # The Link turns with the line from its pin to the crank pin, and moves with its pin.
    (cy0, cz0), (ly0, lz0) = linkage.crank(linkage.locked), linkage.link_pin(linkage.locked)
    (cy, cz), (ly, lz) = linkage.crank(angle), linkage.link_pin(angle)
    turn = math.degrees(math.atan2(cz - lz, cy - ly) - math.atan2(cz0 - lz0, cy0 - ly0))
    return {
        "cradle": bodies["cradle"],
        "battery-door": pose_door(p, bodies["battery-door"], battery_bore(p), doors),
        "cart-body": lift * bodies["cart-body"],
        "cart-door": lift * pose_door(p, bodies["cart-door"], cart_bore(p), doors),
        "lever": bodies["lever"].rotate(_x_axis(linkage.pivot), math.degrees(angle - linkage.locked)),
        "link": Pos(0, ly - ly0, lz - lz0) * bodies["link"].rotate(_x_axis((ly0, lz0)), turn),
    }
