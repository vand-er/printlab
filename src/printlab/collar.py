"""Collar builders shared by the Clamp and its test prints: hinge, Latch, Battery and Cart collars.

Each builder takes the part's flat `Params` (any object with the fields below), the bore
and the collar height, so every part can reuse them at its own sizes.

Collar frame (closed pose): bore centred on the Z axis, Door on +Y, fixed half (the
Cradle stub) on -Y, hinge on -X, Latch on +X. The Door opens anticlockwise (seen from
above) about the hinge axis. Everything stands on z = 0.

Fields used: fdm_offset, wall, gap, open_angle; pin_diameter, knuckle_wall, knuckle_cone,
knuckle_facets; latch_height, arm_thickness, arm_length, arm_root, catch_depth, catch_ramp,
catch_flat, hook_length, hook_land, tab_width, tab_reach; and for the Cart collar
brass_height, brass_margin, glass_diameter, lip_clearance, lip_thickness, travel,
rib_width, rib_head_width, rib_head_depth, rib_reach, carriage_wall.
"""

import math

from build123d import Align, Axis, Box, Cylinder, Part, Plane, Polygon, Pos, RegularPolygon, extrude


def bore(p, nominal: float) -> float:
    """The modelled bore: nominal plus the FDM offset."""
    return nominal + p.fdm_offset


def outer_radius(p, bore_d: float) -> float:
    return bore_d / 2 + p.wall


def knuckle_radius(p) -> float:
    return p.pin_diameter / 2 + p.gap + p.knuckle_wall


def hinge_axis_x(p, bore_d: float) -> float:
    """X of the hinge axis: the knuckle keep-out just touches the collar ring."""
    return -(outer_radius(p, bore_d) + knuckle_radius(p) + p.gap)


def _column(radius: float, z0: float, z1: float) -> Part:
    """A round column on the hinge axis (local frame, axis at the origin)."""
    return Pos(0, 0, z0) * Cylinder(radius, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _below_spike(p, apex: float) -> Part:
    """Everything below a faceted spike on the hinge axis with its apex at z = apex.

    Knuckle ends are these spikes rather than flat, so each overhang is at most
    `knuckle_cone` from vertical. Facets, not true cones: the distance checks are
    exact on planes but not on cones.
    """
    slope = math.tan(math.radians(p.knuckle_cone))  # mm inward per mm up
    bottom = -1.0
    tip = 0.05  # flat top, inside the pin, so the spike never degenerates to a point
    rise = (apex - bottom) - tip / slope
    base = RegularPolygon(tip + rise * slope, p.knuckle_facets, major_radius=False)
    return Pos(0, 0, bottom) * extrude(base, rise, taper=p.knuckle_cone)


def _hinge_zones(p, height: float, axis_x: float) -> dict[str, Part]:
    """Hinge solids about the axis: knuckles, pin and the keep-outs they need."""
    r_pin = p.pin_diameter / 2
    r_k = knuckle_radius(p)
    r_c = r_k + p.gap  # keep-out radius around a knuckle
    slope = math.tan(math.radians(p.knuckle_cone))
    # Half the vertical gap between facing spikes: `gap` along their normal, plus how far a
    # ridge between facets stands proud of a facet once the Door has turned part of a facet.
    ridge = r_c * (1 - math.cos(math.pi / p.knuckle_facets)) / slope
    d = (p.gap / math.sin(math.radians(p.knuckle_cone)) + ridge) / 2
    # Spike apexes: the two knuckle interfaces sit at a third and two thirds of the height
    # at the knuckle rim.
    a1 = height / 3 + r_k / slope
    a2 = 2 * height / 3 + r_k / slope

    def between(r_in, r_out, lower, upper):
        ring = _column(r_out, -1, height + 1) - _column(r_in, -2, height + 2)
        return (ring & _below_spike(p, upper)) - _below_spike(p, lower)

    full = _column(r_k, 0, height)
    stub_knuckles = (
        (full & _below_spike(p, a1 - d))
        + (full - _below_spike(p, a2 + d))
        + _column(r_pin, 0, height)
    )
    door_knuckle = between(r_pin + p.gap, r_k, a1 + d, a2 - d)
    # Where the Door's knuckle is, grown by the gap: the stub keeps out.
    door_keepout = between(r_pin, r_c, a1 - d, a2 + d)
    # Where the stub's knuckles and pin are, grown by the gap: the Door keeps out.
    stub_keepout = _column(r_c, -1, height + 1) - between(r_pin + p.gap, r_c + 1, a1 + d, a2 - d)
    place = Pos(axis_x, 0, 0)
    return {
        "stub_knuckles": place * stub_knuckles,
        "door_knuckle": place * door_knuckle,
        "door_keepout": place * door_keepout,
        "stub_keepout": place * stub_keepout,
    }


def _half_ring(p, bore_d: float, height: float, side: int) -> Part:
    """The collar ring on one side of the split: side +1 is the Door, -1 the stub."""
    r_o = outer_radius(p, bore_d)
    ring = Cylinder(r_o, height, align=(Align.CENTER, Align.CENTER, Align.MIN))
    half = Pos(0, side * (p.gap / 2 + r_o), 0) * Box(
        2 * r_o + 2, 2 * r_o, height, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    return ring & half


def _hinge_web(p, bore_d: float, height: float, side: int) -> Part:
    """Block joining the knuckles to the ring, on one side of the split."""
    r_o = outer_radius(p, bore_d)
    axis_x = hinge_axis_x(p, bore_d)
    x1 = -r_o + p.wall / 2
    width = knuckle_radius(p) - p.gap / 2
    return Pos((axis_x + x1) / 2, side * (p.gap / 2 + width / 2), 0) * Box(
        x1 - axis_x, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def bore_cut(bore_d: float, height: float) -> Part:
    return Pos(0, 0, -1) * Cylinder(
        bore_d / 2, height + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def box(x0: float, x1: float, y0: float, y1: float, z1: float, z0: float = 0.0) -> Part:
    """An axis-aligned box from (x0, y0, z0) to (x1, y1, z1)."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, z0) * Box(
        x1 - x0, y1 - y0, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def _prism(points: list[tuple[float, float]], height: float) -> Part:
    """An XY outline extruded up from the bed, whichever way the outline winds."""
    return extrude(Polygon(*points, align=None), height, dir=(0, 0, 1))


def _catch_far_y(p) -> float:
    """|y| of the catch's holding face, behind which the hook sits."""
    return p.gap / 2 + p.catch_ramp + p.catch_flat


def _arm_inner_x(p, bore_d: float) -> float:
    return outer_radius(p, bore_d) + p.catch_depth + p.gap


def _hook_face_y(p) -> float:
    """y of the hook face that bears on the catch."""
    return -(_catch_far_y(p) + p.gap)


def latch_arm(p, bore_d: float, latch_height: float | None = None) -> Part:
    """The Latch's free beam: from the root block to the hook, bending in XY."""
    h = p.latch_height if latch_height is None else latch_height
    x0 = _arm_inner_x(p, bore_d)
    y_hold = _hook_face_y(p)
    return box(x0, x0 + p.arm_thickness, y_hold, y_hold + p.arm_length, h)


def _latch(p, bore_d: float, h: float) -> Part:
    """Door side of the Latch: root block, arm, hook and thumb tab.

    The root block is cut by the bore with the rest of the Door, so it starts at x = 0.
    """
    x0 = _arm_inner_x(p, bore_d)
    x1 = x0 + p.arm_thickness
    y_hold = _hook_face_y(p)
    y_tip = y_hold - p.hook_length
    y_root = y_hold + p.arm_length
    root = box(0, x1, y_root, y_root + p.arm_root, h)
    arm = box(x0, x1, y_tip, y_root + 0.01, h)
    # Hook: square holding face, lead-in chamfer on the tip side.
    lead = p.hook_length - p.hook_land
    hook = _prism(
        [(x0 + 0.01, y_hold), (x0 - p.catch_depth, y_hold),
         (x0 - p.catch_depth, y_tip + lead), (x0 + 0.01, y_tip)],
        h,
    )
    tab = box(x1 - 0.01, x1 + p.tab_reach, y_tip, y_tip + p.tab_width, h)
    return root + arm + hook + tab


def _catch(p, bore_d: float, h: float) -> Part:
    """Stub side of the Latch: a ramped catch on the ring's outer face."""
    r_o = outer_radius(p, bore_d)
    y_near = -p.gap / 2
    y_ramp = y_near - p.catch_ramp
    y_far = -_catch_far_y(p)
    top = r_o + p.catch_depth
    return _prism(
        [(r_o - p.wall / 2, y_near), (r_o, y_near), (top, y_ramp), (top, y_far),
         (r_o - p.wall / 2, y_far)],
        h,
    ) + box(0, r_o, y_far, y_near, h)


def cradle_stub(p, bore_d: float, height: float, latch_height: float | None = None) -> Part:
    """The fixed half of a collar: half ring, hinge knuckles with pin, and the catch."""
    h = p.latch_height if latch_height is None else latch_height
    zones = _hinge_zones(p, height, hinge_axis_x(p, bore_d))
    body = _half_ring(p, bore_d, height, -1) + _hinge_web(p, bore_d, height, -1)
    body = body - zones["door_keepout"] + zones["stub_knuckles"]
    body = body + _catch(p, bore_d, h)
    return body - bore_cut(bore_d, height)


def door(p, bore_d: float, height: float, latch_height: float | None = None) -> Part:
    """The hinged half of a collar, closed: half ring, middle knuckle and Latch."""
    h = p.latch_height if latch_height is None else latch_height
    zones = _hinge_zones(p, height, hinge_axis_x(p, bore_d))
    body = _half_ring(p, bore_d, height, +1) + _hinge_web(p, bore_d, height, +1)
    body = body - zones["stub_keepout"] + zones["door_knuckle"]
    body = body + _latch(p, bore_d, h)
    return body - bore_cut(bore_d, height)


def pose_door(p, part: Part, bore_d: float, pose: str) -> Part:
    """The Door as printed ("closed") or swung open about its hinge ("open")."""
    if pose == "closed":
        return part
    if pose == "open":
        axis = Axis((hinge_axis_x(p, bore_d), 0, 0), (0, 0, 1))
        return part.rotate(axis, p.open_angle)
    raise ValueError(f"unknown pose {pose!r}")


# --- Cart collar: a sliding body on a T-headed rib, and a Door ---


def cart_collar_height(p) -> float:
    """The Cart collar grips brass only: the brass height less the margin."""
    return p.brass_height - p.brass_margin


def _lip(p, bore_d: float, height: float, side: int) -> Part | None:
    """The lip at the collar top on one side of the split, or None if it clears the bore."""
    lip_d = p.glass_diameter + 2 * p.lip_clearance
    if lip_d >= bore_d - 0.02:
        return None
    ring = Pos(0, 0, height - p.lip_thickness) * (
        Cylinder(bore_d / 2 + 0.01, p.lip_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
        - Cylinder(lip_d / 2, 3 * p.lip_thickness)
    )
    return ring & _half_ring(p, bore_d, height, side)


def _with_lip(p, part: Part, bore_d: float, height: float, side: int) -> Part:
    lip = _lip(p, bore_d, height, side)
    return part if lip is None else part + lip


def carriage_back_y(p, bore_d: float) -> float:
    """y of the carriage's back face, which faces the spine."""
    depth = p.carriage_wall + p.rib_head_depth + 2 * p.gap
    return -(outer_radius(p, bore_d) + depth)


def carriage_half_width(p) -> float:
    """Half the carriage's width along X."""
    return p.rib_head_width / 2 + p.gap + p.carriage_wall


def _head_y(p, bore_d: float) -> tuple[float, float]:
    """(back, front) y of the rib's T head inside the carriage."""
    back = carriage_back_y(p, bore_d) + p.carriage_wall + p.gap
    return back, back + p.rib_head_depth


def _head_bottom_z(p) -> float:
    """z of the head's underside at the bottom of travel: above the carriage's tooth
    (`carriage_wall` tall at its lowest) by the travel and the gap."""
    return p.carriage_wall + p.travel + p.gap


def _xz_prism(points: list[tuple[float, float]], y0: float, y1: float) -> Part:
    """An XZ outline swept along Y from y0 to y1."""
    solid = extrude(Plane.XZ * Polygon(*points, align=None), y1 - y0)
    return Pos(0, y0 - solid.bounding_box().min.Y, 0) * solid


def cart_rib(p, bore_d: float, height: float) -> Part:
    """The Cradle's T-headed rib the Cart collar slides on, from the spine to its head.

    The head's flanges start above a tooth on the carriage and taper in at 45° underneath,
    so they print unsupported; at the top of travel the tooth is `gap` (normal to the
    45° faces) below them, which is the upper stop.
    """
    a, b = p.rib_width / 2, p.rib_head_width / 2
    y_back, y_front = _head_y(p, bore_d)
    y0 = carriage_back_y(p, bore_d) - p.rib_reach - 0.5  # 0.5 mm into the spine
    neck = box(-a, a, y0, y_front, height)
    zb = _head_bottom_z(p)
    head = _xz_prism(
        [(-a, zb), (a, zb), (b, zb + b - a), (b, height), (-b, height), (-b, zb + b - a)],
        y_back, y_front,
    )
    return neck + head


def _slot(p, bore_d: float, height: float) -> Part:
    """The carriage's cut: the rib grown by `gap`, with the head's cavity run down by
    the travel so the head clears it anywhere along the travel."""
    a, b, g = p.rib_width / 2, p.rib_head_width / 2, p.gap
    y_back, y_front = _head_y(p, bore_d)
    neck = Pos(0, 0, -1) * box(-a - g, a + g, carriage_back_y(p, bore_d) - 1, y_front + g, height + 2)
    # The head outline, each edge offset outward by g, then lowered by the travel.
    zb = _head_bottom_z(p) - p.travel
    x_low = a + g * (math.sqrt(2) - 1)
    z_side = zb + (b - a) + g * (1 - math.sqrt(2))
    top = height + 1
    cavity = _xz_prism(
        [(-x_low, zb - g), (x_low, zb - g), (b + g, z_side), (b + g, top),
         (-b - g, top), (-b - g, z_side)],
        y_back - g, y_front + g,
    )
    return neck + cavity


def cart_body(p, bore_d: float, height: float) -> Part:
    """The Cart collar's sliding body at the bottom of travel: the stub's half ring,
    hinge and catch, a lip, and a carriage with a T-slot around the rib."""
    hw = carriage_half_width(p)
    y_in = -(outer_radius(p, bore_d) - p.wall / 2)  # inside the ring wall
    carriage = box(-hw, hw, carriage_back_y(p, bore_d), y_in, height)
    carriage = carriage - _slot(p, bore_d, height) - bore_cut(bore_d, height)
    body = cradle_stub(p, bore_d, height) + carriage
    return _with_lip(p, body, bore_d, height, -1)


def cart_door(p, bore_d: float, height: float) -> Part:
    """The Cart collar's Door, closed: the collar Door with a lip."""
    return _with_lip(p, door(p, bore_d, height), bore_d, height, +1)


def travel_z(p, travel: str | float) -> float:
    """How far the Cart collar sits above the bottom of its travel: "bottom", "top" or mm."""
    if travel == "bottom":
        return 0.0
    if travel == "top":
        return p.travel
    if isinstance(travel, (int, float)) and 0 <= travel <= p.travel:
        return float(travel)
    raise ValueError(f"unknown travel {travel!r}")
