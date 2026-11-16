"""Clamp lever strip: three small Clamps, one per Stroke, to pick the Stroke on the real Cart.

Each Clamp is a Cradle carrying a Battery collar, a sliding Cart collar stacked on it and
an over-centre Lever. The Lever pivots on the back of the Cradle (opposite the fire
button); a Link from its crank pin to a pin on the Cart collar pulls the collar down by
the Stroke as the Lever goes over centre. The stop is the Lever lying flat on the Cradle.
Everything prints closed and in place, Battery axis vertical (Z), Lever locked.

Clamp frame: the collars' frame from `printlab.collar` (bore on the Z axis, Doors on +Y,
hinges on -X, Latches on +X). The Cradle's spine stands behind the collars (-Y). The
Lever, Link and pin heads are layers along X on the +X side, so each moves in a YZ plane:

    lug | Lever | Link | pin heads        (toggle_x is the Lever's outer face)

Every body's underside rests on the bed or, across a `gap`, on the body below it: the
Cart collar prints on top of the Battery collar, so the Battery Latch runs full height
under the Cart Latch.

Reusable for the Clamp (#14): `solve_toggle`, `cradle`, `lever`, `link`, `cart_collar`,
`battery_collar` and `clamp` all take `Params` (and the Stroke).
"""

import math
from dataclasses import dataclass

from build123d import Align, Axis, Cylinder, Part, Plane, Polygon, Pos, Rot, Text, extrude

from printlab.collar import (
    bore,
    bore_cut,
    box,
    cart_body,
    cart_collar_height,
    cart_door,
    cart_rib,
    carriage_back_y,
    carriage_half_width,
    cradle_stub,
    door,
    outer_radius,
    pose_door,
)

GRAM_BUDGET = 20.0  # g; the CLI warns above this


@dataclass(frozen=True)
class Params:
    # The strip
    strokes: tuple[float, ...] = (0.3, 0.6, 0.9)  # mm, one Clamp per Stroke
    pitch: float = 30.0  # mm between Clamp centres; room for open Doors
    # Bores: the Test plate's middle sizes until it picks them
    battery_nominal_bore: float = 12.8  # mm, labelled size
    cart_nominal_bore: float = 12.2  # mm, labelled size
    fdm_offset: float = 0.2  # mm added to each bore; FDM holes print undersize
    # Collars (as the Test plate)
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
    # Labels
    label_size: float = 3.5  # mm font size of the Stroke labels
    label_relief: float = 0.4  # mm
    tag_length: float = 10.0  # mm, label tag along X, off the spine's -X side
    tag_depth: float = 5.0  # mm, along Y
    tag_thickness: float = 1.0  # mm


# --- Sizes derived from Params ---


def battery_bore(p: Params) -> float:
    return bore(p, p.battery_nominal_bore)


def cart_bore(p: Params) -> float:
    return bore(p, p.cart_nominal_bore)


def cart_floor_z(p: Params) -> float:
    """z of the Cart collar's underside, locked: a `gap` above the Battery collar."""
    return p.battery_collar_height + p.gap


def spine_y(p: Params) -> tuple[float, float]:
    """(back, front) y of the spine; the front is where the rib's neck starts."""
    front = carriage_back_y(p, cart_bore(p)) - p.rib_reach
    return front - p.spine_depth, front


def seat_z(p: Params, stroke: float) -> float:
    """z of the Seat: with the Lever open the Cart collar's lip rests on the ledge."""
    top_open = cart_floor_z(p) + stroke + cart_collar_height(p)
    return top_open - p.lip_thickness - p.brass_height


def _eye_radius(p: Params) -> float:
    """Outer radius of a ring around a pin: pin, gap and wall."""
    return p.pin_diameter / 2 + p.gap + p.knuckle_wall


def _boss_radius(p: Params) -> float:
    """Outer radius of material carrying a pin."""
    return p.pin_diameter / 2 + p.knuckle_wall


def _ear_y(p: Params) -> tuple[float, float]:
    """(back, front) y of the Cart collar's ear, which carries the Link pin."""
    back, front = spine_y(p)
    return front + p.gap, -(outer_radius(p, cart_bore(p)) - p.wall / 2)


def _layers(p: Params) -> dict[str, tuple[float, float]]:
    """X extents of the toggle's layers."""
    x = p.toggle_x
    lever = (x - p.lever_width, x)
    lug = (lever[0] - p.gap - p.lug_width, lever[0] - p.gap)
    link = (x + p.gap, x + p.gap + p.link_width)
    head = (link[1] + p.gap, link[1] + p.gap + p.head_width)
    return {"lug": lug, "lever": lever, "link": link, "head": head}


# --- Over-centre toggle kinematics (YZ plane) ---


@dataclass(frozen=True)
class Toggle:
    """Pivot P on the Cradle, crank pin C on the Lever, Link pin L on the Cart collar.

    L slides along Z at y = link_y. Crank angles are measured in the YZ plane from +Y
    towards +Z (a positive rotation about +X). The collar is lowest with P between C and
    L (dead centre); locked is `overtravel` past it, towards the stop.
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

    def angle(self, pose: str) -> float:
        return {"closed": self.locked, "open": self.opened, "centre": self.centre}[pose]


def solve_toggle(p: Params, stroke: float, pivot_y: float, link_y: float, link_z: float) -> Toggle:
    """The toggle whose Link pin sits at (link_y, link_z) when locked and rises by `stroke`
    when the Lever opens. The pivot height follows from the locked pose."""
    r, length = p.crank_radius, p.link_length
    dy = link_y - pivot_y
    reach = length - r  # pivot to Link pin at dead centre
    if reach <= abs(dy):
        raise ValueError("Link too short to reach past the pivot")
    centre = math.atan2(-math.sqrt(reach**2 - dy**2), -dy)
    locked = centre + math.radians(p.overtravel)

    def rise(angle):  # Link pin height above the pivot
        return r * math.sin(angle) + math.sqrt(length**2 - (dy - r * math.cos(angle)) ** 2)

    # Opening turns the crank back through centre; the pin rises until the far dead centre.
    lo, hi = locked - centre, locked - centre + math.pi
    if rise(locked - hi) - rise(locked) < stroke:
        raise ValueError(f"stroke {stroke} mm is beyond this toggle")
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if rise(locked - mid) - rise(locked) < stroke else (lo, mid)
    pivot = (pivot_y, link_z - rise(locked))
    return Toggle(pivot, r, length, link_y, centre, locked, locked - (lo + hi) / 2)


def toggle(p: Params, stroke: float) -> Toggle:
    """This Clamp's toggle: pivot behind the spine, Link pin on the Cart collar's ear."""
    back, _ = spine_y(p)
    ear_back, ear_front = _ear_y(p)
    link_z = cart_floor_z(p) + p.link_pin_height
    return solve_toggle(p, stroke, back - p.pivot_offset, (ear_back + ear_front) / 2, link_z)


# --- Solids ---


def _yz_prism(points: list[tuple[float, float]], x0: float, x1: float) -> Part:
    """A YZ outline swept along X from x0 to x1."""
    return Pos(x0, 0, 0) * extrude(Plane.YZ * Polygon(*points, align=None), x1 - x0)


def _x_pin(radius: float, centre: tuple[float, float], x0: float, x1: float) -> Part:
    """A round pin along X."""
    return Pos(x0, *centre) * Rot(0, 90, 0) * Cylinder(
        radius, x1 - x0, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def _circle(centre: tuple[float, float], radius: float, n: int = 48) -> list[tuple[float, float]]:
    y, z = centre
    return [(y + radius * math.cos(2 * math.pi * i / n), z + radius * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def _hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convex hull, anticlockwise (Andrew's monotone chain)."""
    pts = sorted(set((round(y, 9), round(z, 9)) for y, z in points))

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


def _rect(y0: float, y1: float, z0: float, z1: float) -> list[tuple[float, float]]:
    return [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]


def _pin_with_head(p: Params, centre: tuple[float, float], x0: float) -> Part:
    """A pin from x0 out through the Link, ending in a diamond head that keeps the Link on.

    The diamond's lowest corner is on the pin's axis, so the head grows out of the pin at
    45° and prints unsupported.
    """
    y, z = centre
    h0, h1 = _layers(p)["head"]
    s = p.head_size
    head = _yz_prism([(y, z), (y + s, z + s), (y, z + 2 * s), (y - s, z + s)], h0, h1)
    return _x_pin(p.pin_diameter / 2, centre, x0, h1) + head


def battery_collar(p: Params) -> tuple[Part, Part]:
    """(Cradle stub, Door) of the Battery collar; the Latch runs full height."""
    bore_d, h = battery_bore(p), p.battery_collar_height
    return cradle_stub(p, bore_d, h, latch_height=h), door(p, bore_d, h, latch_height=h)


def cradle(p: Params, stroke: float) -> Part:
    """The Cradle: Battery collar stub, spine, rib for the Cart collar, and the pivot lug
    with its pin. Labelled with the Stroke on a tag off the spine's -X side."""
    t = toggle(p, stroke)
    back, front = spine_y(p)
    hw = carriage_half_width(p)
    hb = p.battery_collar_height
    top = cart_floor_z(p) + cart_collar_height(p)
    stub, _ = battery_collar(p)
    spine = box(-hw, p.toggle_x, back, front, top)
    web = box(-hw, p.toggle_x, front - 0.5, -(outer_radius(p, battery_bore(p)) - p.wall / 2), hb)
    # The rib, with its neck run down into the web so it stands on it.
    rib = Pos(0, 0, cart_floor_z(p)) * cart_rib(p, cart_bore(p), cart_collar_height(p))
    head_front = carriage_back_y(p, cart_bore(p)) + p.carriage_wall + p.gap + p.rib_head_depth
    neck = box(-p.rib_width / 2, p.rib_width / 2, front - 0.5, head_front, cart_floor_z(p) + 0.01,
               z0=hb - 0.5)
    lx0, lx1 = _layers(p)["lug"]
    py, pz = t.pivot
    lug = box(lx0, lx1, py - _boss_radius(p), back + 0.5, pz + _boss_radius(p))
    pin = _x_pin(p.pin_diameter / 2, t.pivot, lx1 - 0.5, p.toggle_x)
    tag = box(-hw - p.tag_length, -hw + 0.5, front - p.tag_depth, front, p.tag_thickness)
    text = Text(f"{stroke:.1f}", p.label_size)
    label = Pos(-hw - p.tag_length / 2, front - p.tag_depth / 2, p.tag_thickness) * extrude(
        text, p.label_relief
    )
    body = stub + spine + web + rib + neck + lug + pin + tag + label
    return body - bore_cut(battery_bore(p), hb)


def cart_collar(p: Params, stroke: float) -> tuple[Part, Part]:
    """(sliding body, Door) of the Cart collar, locked. The body carries an ear on its
    carriage's +X side with the Link pin."""
    t = toggle(p, stroke)
    bore_d, h = cart_bore(p), cart_collar_height(p)
    ear_back, ear_front = _ear_y(p)
    ear = box(carriage_half_width(p) - 0.01, p.toggle_x, ear_back, ear_front, h)
    lift = Pos(0, 0, cart_floor_z(p))
    pin = _pin_with_head(p, t.link_pin(t.locked), p.toggle_x - 0.5)
    return lift * (cart_body(p, bore_d, h) + ear) + pin, lift * cart_door(p, bore_d, h)


def lever(p: Params, t: Toggle) -> Part:
    """The Lever, locked: a convex plate from the pivot hub down to the bed, its front lying
    flat a `gap` off the spine's back (the stop), with the crank pin and its head."""
    back, _ = spine_y(p)
    c = t.crank(t.locked)
    rb = _boss_radius(p)
    outline = _hull(
        _circle(t.pivot, _eye_radius(p)) + _circle(c, rb)
        + _rect(c[0] - rb, back - p.gap, 0, t.pivot[1])
    )
    x0, x1 = _layers(p)["lever"]
    body = _yz_prism(outline, x0, x1)
    body = body - _x_pin(p.pin_diameter / 2 + p.gap, t.pivot, x0 - 1, x1 + 1)
    return body + _pin_with_head(p, c, x1 - 0.5)


def link(p: Params, t: Toggle) -> Part:
    """The Link, locked: eyes on the crank pin and the Link pin, and a foot under the
    crank eye down to the bed."""
    c, l_pin = t.crank(t.locked), t.link_pin(t.locked)
    re = _eye_radius(p)
    outline = _hull(_circle(c, re) + _circle(l_pin, re) + _rect(c[0] - re, c[0] + re, 0, c[1]))
    x0, x1 = _layers(p)["link"]
    hole = p.pin_diameter / 2 + p.gap
    return _yz_prism(outline, x0, x1) - _x_pin(hole, c, x0 - 1, x1 + 1) - _x_pin(
        hole, l_pin, x0 - 1, x1 + 1
    )


def _x_axis(centre: tuple[float, float]) -> Axis:
    return Axis((0, *centre), (1, 0, 0))


def clamp(p: Params, stroke: float, pose: str = "closed") -> dict[str, Part]:
    """One Clamp's bodies in its own frame. `pose`: "closed" (printed: Doors shut, Lever
    locked), "open" (Doors and Lever open) or "centre" (Doors shut, Lever at dead centre)."""
    t = toggle(p, stroke)
    a = t.angle(pose)
    doors = "open" if pose == "open" else "closed"
    _, battery_door = battery_collar(p)
    body, cart_d = cart_collar(p, stroke)
    lift = Pos(0, 0, t.link_pin(a)[1] - t.link_pin(t.locked)[1])
    # The Link turns with the line from its pin to the crank pin, and moves with its pin.
    (cy0, cz0), (ly0, lz0) = t.crank(t.locked), t.link_pin(t.locked)
    (cy, cz), (ly, lz) = t.crank(a), t.link_pin(a)
    turn = math.degrees(math.atan2(cz - lz, cy - ly) - math.atan2(cz0 - lz0, cy0 - ly0))
    return {
        "cradle": cradle(p, stroke),
        "battery-door": pose_door(p, battery_door, battery_bore(p), doors),
        "cart-body": lift * body,
        "cart-door": lift * pose_door(p, cart_d, cart_bore(p), doors),
        "lever": lever(p, t).rotate(_x_axis(t.pivot), math.degrees(a - t.locked)),
        "link": Pos(0, ly - ly0, lz - lz0) * link(p, t).rotate(_x_axis((ly0, lz0)), turn),
    }


def label_name(stroke: float) -> str:
    return f"{stroke:.1f}".replace(".", "-")


def clamp_x(p: Params, i: int) -> float:
    return (i - (len(p.strokes) - 1) / 2) * p.pitch


def build(params: Params = Params(), pose: str = "closed") -> dict[str, Part]:
    """Named bodies of all three Clamps, side by side along X."""
    bodies = {}
    for i, stroke in enumerate(params.strokes):
        place = Pos(clamp_x(params, i), 0, 0)
        for name, part in clamp(params, stroke, pose).items():
            bodies[f"{name}-{label_name(stroke)}"] = place * part
    return bodies
