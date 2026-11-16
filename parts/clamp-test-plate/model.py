"""Clamp test plate: Battery and Cart collar samples at three bores each.

Each Battery sample is a short Cradle stub with a print-in-place hinged collar Door, shut by
a hook-snap Latch with a thumb tab, and labelled with its nominal bore. It prints
closed, Battery axis vertical (Z). Pick the bore that grips the Battery.

Each Cart sample is a Cart collar: a sliding body (the stub's half ring, hinge and catch,
plus a carriage) and a Door, gripping the brass base by friction. The carriage slides
`travel` up a T-headed rib on the plate, which stops it turning; the carriage roof
landing on the rib's top is the upper stop. A lip on top registers on the Cart's ledge.
It prints at the bottom of its travel. Pick the bore that grips the brass.

Sample frame (closed pose): bore centred on the Z axis, Door on +Y, Cradle stub on
-Y, hinge on -X, Latch on +X. The Door opens anticlockwise (seen from above) about
the hinge axis. Cart samples use the same frame, turned 180° so the carriage faces
the spine.

The builders (`hinge_axis_x`, `cradle_stub`, `door`, `latch_arm`) take the bore and
collar height as arguments so the Cart collar samples, Lever strip and Clamp can
reuse them with their own sizes. The Cart collar builders (`cart_body`, `cart_door`,
`cart_rib`, `travel_z`) do the same; a Link pulls the collar down by moving it with
`travel_z`.
"""

import math
from dataclasses import dataclass

from build123d import (
    Align,
    Axis,
    Box,
    Cylinder,
    Part,
    Plane,
    Polygon,
    Pos,
    RegularPolygon,
    Rot,
    Text,
    extrude,
)

GRAM_BUDGET = 8.0  # g; the CLI warns above this

# Modelling tolerances, not printed dimensions.
OVERLAP = 0.01  # mm two solids share so their union fuses into one
SPIKE_TIP = 0.05  # mm flat top of a knuckle spike, inside the pin, so it never degenerates to a point


@dataclass(frozen=True)
class Params:
    # Samples
    nominal_bores: tuple[float, ...] = (12.6, 12.8, 13.0)  # mm, labelled sizes
    fdm_offset: float = 0.2  # mm added to each bore; FDM holes print undersize
    pitch: float = 32.0  # mm between sample centres; room for an open Door
    # Collar
    collar_height: float = 9.0  # mm, Battery sample; below the 12 mm collar to save filament
    wall: float = 1.3  # mm, collar ring wall (load-bearing)
    gap: float = 0.3  # mm, print-in-place clearance between Door and stub
    open_angle: float = 90.0  # degrees the Door swings in the open pose
    # Hinge: three knuckles, stub-Door-stub, with an integral pin on the stub
    pin_diameter: float = 2.4  # mm (load-bearing)
    knuckle_wall: float = 1.2  # mm, Door knuckle ring around the pin (load-bearing)
    knuckle_cone: float = 45.0  # degrees from vertical; spiked knuckle ends print unsupported
    knuckle_facets: int = 16  # facets around each knuckle spike
    # Latch: horizontal hook arm on the Door, catch on the stub
    latch_height: float = 4.5  # mm, arm height from the bed
    arm_thickness: float = 1.4  # mm, radial; the arm bends in the XY plane
    arm_length: float = 8.0  # mm, free beam from root to hook; about 2.6 % strain to snap
    arm_root: float = 2.0  # mm, root block joining the arm to the Door
    catch_depth: float = 0.8  # mm the hook engages behind the catch
    catch_ramp: float = 2.5  # mm lead-in ramp the hook rides over
    catch_flat: float = 1.0  # mm flat top of the catch
    hook_length: float = 1.5  # mm along the arm
    hook_land: float = 0.5  # mm flat at the hook's tip; the rest is lead-in chamfer
    tab_width: float = 1.5  # mm thumb tab along the arm
    tab_reach: float = 2.5  # mm the thumb tab stands out from the arm
    # Cart collar samples. Cart sizes are estimates; the brass height is a ruler reading.
    cart_nominal_bores: tuple[float, ...] = (12.0, 12.2, 12.4)  # mm, labelled sizes
    brass_height: float = 10.0  # mm, Seat to ledge
    brass_margin: float = 1.0  # mm the collar stops short of the brass height
    glass_diameter: float = 11.9  # mm, glass tank above the ledge
    lip_clearance: float = 0.1  # mm per side between the lip and the glass
    lip_thickness: float = 0.8  # mm, lip at the collar top, inside the collar height
    travel: float = 2.0  # mm the collar slides on its rib
    rib_width: float = 2.0  # mm, the rib's neck
    rib_head_width: float = 5.0  # mm, the rib's T head inside the carriage
    rib_head_depth: float = 1.2  # mm
    rib_reach: float = 1.0  # mm of neck between the spine and the carriage
    carriage_wall: float = 1.2  # mm, carriage walls and roof (load-bearing)
    # Plate
    spine_width: float = 3.5  # mm, strip joining the stubs and ribs
    spine_height: float = 1.0  # mm; carries no load
    label_size: float = 3.5  # mm font size of the bore labels
    label_relief: float = 0.4  # mm the labels stand up from the spine


def bore(p: Params, nominal: float) -> float:
    """The modelled bore: nominal plus the FDM offset."""
    return nominal + p.fdm_offset


def _outer_radius(p: Params, bore_d: float) -> float:
    return bore_d / 2 + p.wall


def _knuckle_radius(p: Params) -> float:
    return p.pin_diameter / 2 + p.gap + p.knuckle_wall


def hinge_axis_x(p: Params, bore_d: float) -> float:
    """X of the hinge axis: the knuckle keep-out just touches the collar ring."""
    return -(_outer_radius(p, bore_d) + _knuckle_radius(p) + p.gap)


def _column(radius: float, z0: float, z1: float) -> Part:
    """A round column on the hinge axis (local frame, axis at the origin)."""
    return Pos(0, 0, z0) * Cylinder(radius, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _below_spike(p: Params, apex: float) -> Part:
    """Everything below a faceted spike on the hinge axis with its apex at z = apex.

    Knuckle ends are these spikes rather than flat, so each overhang is at most
    `knuckle_cone` from vertical. Facets, not true cones: the distance checks are
    exact on planes but not on cones.
    """
    slope = math.tan(math.radians(p.knuckle_cone))  # mm inward per mm up
    bottom = -1.0
    tip = SPIKE_TIP
    rise = (apex - bottom) - tip / slope
    base = RegularPolygon(tip + rise * slope, p.knuckle_facets, major_radius=False)
    return Pos(0, 0, bottom) * extrude(base, rise, taper=p.knuckle_cone)


def _hinge_zones(p: Params, height: float, axis_x: float) -> dict[str, Part]:
    """Hinge solids about the axis: knuckles, pin and the keep-outs they need."""
    r_pin = p.pin_diameter / 2
    r_k = _knuckle_radius(p)
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


def _half_ring(p: Params, bore_d: float, height: float, side: int) -> Part:
    """The collar ring on one side of the split: side +1 is the Door, -1 the stub."""
    r_o = _outer_radius(p, bore_d)
    ring = Cylinder(r_o, height, align=(Align.CENTER, Align.CENTER, Align.MIN))
    half = Pos(0, side * (p.gap / 2 + r_o), 0) * Box(
        2 * r_o + 2, 2 * r_o, height, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    return ring & half


def _hinge_web(p: Params, bore_d: float, height: float, side: int) -> Part:
    """Block joining the knuckles to the ring, on one side of the split."""
    r_o = _outer_radius(p, bore_d)
    axis_x = hinge_axis_x(p, bore_d)
    x1 = -r_o + p.wall / 2
    width = _knuckle_radius(p) - p.gap / 2
    return Pos((axis_x + x1) / 2, side * (p.gap / 2 + width / 2), 0) * Box(
        x1 - axis_x, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def _bore_cut(bore_d: float, height: float) -> Part:
    return Pos(0, 0, -1) * Cylinder(
        bore_d / 2, height + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def _box(x0: float, x1: float, y0: float, y1: float, z1: float) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, 0) * Box(
        x1 - x0, y1 - y0, z1, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def _prism(points: list[tuple[float, float]], height: float) -> Part:
    """An XY outline extruded up from the bed, whichever way the outline winds."""
    return extrude(Polygon(*points, align=None), height, dir=(0, 0, 1))


def _catch_far_y(p: Params) -> float:
    """|y| of the catch's holding face, behind which the hook sits."""
    return p.gap / 2 + p.catch_ramp + p.catch_flat


def _arm_inner_x(p: Params, bore_d: float) -> float:
    return _outer_radius(p, bore_d) + p.catch_depth + p.gap


def _hook_face_y(p: Params) -> float:
    """y of the hook face that bears on the catch."""
    return -(_catch_far_y(p) + p.gap)


def latch_arm(p: Params, bore_d: float) -> Part:
    """The Latch's free beam: from the root block to the hook, bending in XY."""
    x0 = _arm_inner_x(p, bore_d)
    y_hold = _hook_face_y(p)
    return _box(x0, x0 + p.arm_thickness, y_hold, y_hold + p.arm_length, p.latch_height)


def _latch(p: Params, bore_d: float) -> Part:
    """Door side of the Latch: root block, arm, hook and thumb tab.

    The root block is cut by the bore with the rest of the Door, so it starts at x = 0.
    """
    x0 = _arm_inner_x(p, bore_d)
    x1 = x0 + p.arm_thickness
    y_hold = _hook_face_y(p)
    y_tip = y_hold - p.hook_length
    y_root = y_hold + p.arm_length
    root = _box(0, x1, y_root, y_root + p.arm_root, p.latch_height)
    arm = _box(x0, x1, y_tip, y_root + OVERLAP, p.latch_height)
    # Hook: square holding face, lead-in chamfer on the tip side.
    lead = p.hook_length - p.hook_land
    hook = _prism(
        [(x0 + OVERLAP, y_hold), (x0 - p.catch_depth, y_hold),
         (x0 - p.catch_depth, y_tip + lead), (x0 + OVERLAP, y_tip)],
        p.latch_height,
    )
    tab = _box(x1 - OVERLAP, x1 + p.tab_reach, y_tip, y_tip + p.tab_width, p.latch_height)
    return root + arm + hook + tab


def _catch(p: Params, bore_d: float) -> Part:
    """Stub side of the Latch: a ramped catch on the ring's outer face."""
    r_o = _outer_radius(p, bore_d)
    y_near = -p.gap / 2
    y_ramp = y_near - p.catch_ramp
    y_far = -_catch_far_y(p)
    top = r_o + p.catch_depth
    return _prism(
        [(r_o - p.wall / 2, y_near), (r_o, y_near), (top, y_ramp), (top, y_far),
         (r_o - p.wall / 2, y_far)],
        p.latch_height,
    ) + _box(0, r_o, y_far, y_near, p.latch_height)


def cradle_stub(p: Params, bore_d: float, height: float) -> Part:
    """The fixed half of a collar: half ring, hinge knuckles with pin, and the catch."""
    zones = _hinge_zones(p, height, hinge_axis_x(p, bore_d))
    body = _half_ring(p, bore_d, height, -1) + _hinge_web(p, bore_d, height, -1)
    body = body - zones["door_keepout"] + zones["stub_knuckles"]
    body = body + _catch(p, bore_d)
    return body - _bore_cut(bore_d, height)


def door(p: Params, bore_d: float, height: float) -> Part:
    """The hinged half of a collar, closed: half ring, middle knuckle and Latch."""
    zones = _hinge_zones(p, height, hinge_axis_x(p, bore_d))
    body = _half_ring(p, bore_d, height, +1) + _hinge_web(p, bore_d, height, +1)
    body = body - zones["stub_keepout"] + zones["door_knuckle"]
    body = body + _latch(p, bore_d)
    return body - _bore_cut(bore_d, height)


def pose_door(p: Params, part: Part, bore_d: float, pose: str) -> Part:
    """The Door as printed ("closed") or swung open about its hinge ("open")."""
    if pose == "closed":
        return part
    if pose == "open":
        axis = Axis((hinge_axis_x(p, bore_d), 0, 0), (0, 0, 1))
        return part.rotate(axis, p.open_angle)
    raise ValueError(f"unknown pose {pose!r}")


def cart_collar_height(p: Params) -> float:
    """The Cart collar grips brass only: the brass height less the margin."""
    return p.brass_height - p.brass_margin


def _lip(p: Params, bore_d: float, height: float, side: int) -> Part | None:
    """The lip at the collar top on one side of the split, or None if it clears the bore."""
    lip_d = p.glass_diameter + 2 * p.lip_clearance
    if lip_d >= bore_d - 2 * OVERLAP:
        return None
    ring = Pos(0, 0, height - p.lip_thickness) * (
        Cylinder(bore_d / 2 + OVERLAP, p.lip_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
        - Cylinder(lip_d / 2, 3 * p.lip_thickness)
    )
    return ring & _half_ring(p, bore_d, height, side)


def _with_lip(p: Params, part: Part, bore_d: float, height: float, side: int) -> Part:
    lip = _lip(p, bore_d, height, side)
    return part if lip is None else part + lip


def _carriage_back_y(p: Params, bore_d: float) -> float:
    """y of the carriage's back face, which faces the spine."""
    depth = p.carriage_wall + p.rib_head_depth + 2 * p.gap
    return -(_outer_radius(p, bore_d) + depth)


def _head_y(p: Params, bore_d: float) -> tuple[float, float]:
    """(back, front) y of the rib's T head inside the carriage."""
    back = _carriage_back_y(p, bore_d) + p.carriage_wall + p.gap
    return back, back + p.rib_head_depth


def _head_bottom_z(p: Params) -> float:
    """z of the head's underside at the bottom of travel: above the carriage's tooth
    (`carriage_wall` tall at its lowest) by the travel and the gap."""
    return p.carriage_wall + p.travel + p.gap


def _xz_prism(points: list[tuple[float, float]], y0: float, y1: float) -> Part:
    """An XZ outline swept along Y from y0 to y1."""
    solid = extrude(Plane.XZ * Polygon(*points, align=None), y1 - y0)
    return Pos(0, y0 - solid.bounding_box().min.Y, 0) * solid


def cart_rib(p: Params, bore_d: float, height: float) -> Part:
    """The Cradle's T-headed rib the Cart collar slides on, from the spine to its head.

    The head's flanges start above a tooth on the carriage and taper in at 45° underneath,
    so they print unsupported; at the top of travel the tooth is `gap` (normal to the
    45° faces) below them, which is the upper stop.
    """
    a, b = p.rib_width / 2, p.rib_head_width / 2
    y_back, y_front = _head_y(p, bore_d)
    y0 = _carriage_back_y(p, bore_d) - p.rib_reach - 0.5  # 0.5 mm into the spine
    neck = _box(-a, a, y0, y_front, height)
    zb = _head_bottom_z(p)
    head = _xz_prism(
        [(-a, zb), (a, zb), (b, zb + b - a), (b, height), (-b, height), (-b, zb + b - a)],
        y_back, y_front,
    )
    return neck + head


def _slot(p: Params, bore_d: float, height: float) -> Part:
    """The carriage's cut: the rib grown by `gap`, with the head's cavity run down by
    the travel so the head clears it anywhere along the travel."""
    a, b, g = p.rib_width / 2, p.rib_head_width / 2, p.gap
    y_back, y_front = _head_y(p, bore_d)
    neck = Pos(0, 0, -1) * _box(-a - g, a + g, _carriage_back_y(p, bore_d) - 1, y_front + g, height + 2)
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


def cart_body(p: Params, bore_d: float, height: float) -> Part:
    """The Cart collar's sliding body at the bottom of travel: the stub's half ring,
    hinge and catch, a lip, and a carriage with a T-slot around the rib."""
    hw = p.rib_head_width / 2 + p.gap + p.carriage_wall
    y_in = -(_outer_radius(p, bore_d) - p.wall / 2)  # inside the ring wall
    carriage = _box(-hw, hw, _carriage_back_y(p, bore_d), y_in, height)
    carriage = carriage - _slot(p, bore_d, height) - _bore_cut(bore_d, height)
    body = cradle_stub(p, bore_d, height) + carriage
    return _with_lip(p, body, bore_d, height, -1)


def cart_door(p: Params, bore_d: float, height: float) -> Part:
    """The Cart collar's Door, closed: the collar Door with a lip."""
    return _with_lip(p, door(p, bore_d, height), bore_d, height, +1)


def travel_z(p: Params, travel: str | float) -> float:
    """How far the Cart collar sits above the bottom of its travel: "bottom", "top" or mm."""
    if travel == "bottom":
        return 0.0
    if travel == "top":
        return p.travel
    if isinstance(travel, (int, float)) and 0 <= travel <= p.travel:
        return float(travel)
    raise ValueError(f"unknown travel {travel!r}")


def label_name(nominal: float) -> str:
    return f"{nominal:.1f}".replace(".", "-")


def sample_x(p: Params, i: int) -> float:
    return (i - (len(p.nominal_bores) - 1) / 2) * p.pitch


def _spine_y(p: Params) -> tuple[float, float]:
    """(back, front) y of the spine: its front edge lies inside the thinnest Battery ring's wall."""
    front = -(min(bore(p, n) for n in p.nominal_bores) / 2 + p.wall / 2)
    return front - p.spine_width, front


def cart_centre(p: Params, i: int) -> tuple[float, float]:
    """(x, y) of Cart sample i's bore: between the Battery samples, behind the spine."""
    back, _ = _spine_y(p)
    bore_d = bore(p, p.cart_nominal_bores[i])
    return sample_x(p, i) + p.pitch / 2, back + _carriage_back_y(p, bore_d) - p.rib_reach


def _cart_place(p: Params, i: int):
    x, y = cart_centre(p, i)
    return Pos(x, y, 0) * Rot(0, 0, 180)


def _label(p: Params, nominal: float, x: float) -> Part:
    back, front = _spine_y(p)
    text = Text(f"{nominal:.1f}", p.label_size)
    return Pos(x, (back + front) / 2, p.spine_height) * extrude(text, p.label_relief)


def _plate(p: Params) -> Part:
    bores = [bore(p, n) for n in p.nominal_bores]
    back, front = _spine_y(p)
    x0 = sample_x(p, 0) + hinge_axis_x(p, bores[0])
    x1 = max(
        sample_x(p, len(bores) - 1) + _outer_radius(p, bores[-1]),
        cart_centre(p, len(p.cart_nominal_bores) - 1)[0] + p.rib_head_width / 2,
    )
    plate = _box(x0, x1, back, front, p.spine_height)
    for i, (nominal, bore_d) in enumerate(zip(p.nominal_bores, bores)):
        x = sample_x(p, i)
        plate = plate + Pos(x, 0, 0) * cradle_stub(p, bore_d, p.collar_height)
        plate = plate + _label(p, nominal, x)
        plate = plate - Pos(x, 0, 0) * _bore_cut(bore_d, p.collar_height)
    height = cart_collar_height(p)
    for i, nominal in enumerate(p.cart_nominal_bores):
        plate = plate + _cart_place(p, i) * cart_rib(p, bore(p, nominal), height)
        plate = plate + _label(p, nominal, cart_centre(p, i)[0])
    return plate


def build(
    params: Params = Params(), pose: str = "closed", travel: str | float = "bottom"
) -> dict[str, Part]:
    """Named bodies. `pose` opens or closes every Door; `travel` places every Cart collar."""
    bodies = {"plate": _plate(params)}
    for i, nominal in enumerate(params.nominal_bores):
        bore_d = bore(params, nominal)
        closed = door(params, bore_d, params.collar_height)
        bodies[f"door-{label_name(nominal)}"] = Pos(sample_x(params, i), 0, 0) * pose_door(
            params, closed, bore_d, pose
        )
    height = cart_collar_height(params)
    lift = Pos(0, 0, travel_z(params, travel))
    for i, nominal in enumerate(params.cart_nominal_bores):
        bore_d = bore(params, nominal)
        place = lift * _cart_place(params, i)
        name = label_name(nominal)
        bodies[f"cart-body-{name}"] = place * cart_body(params, bore_d, height)
        closed = cart_door(params, bore_d, height)
        bodies[f"cart-door-{name}"] = place * pose_door(params, closed, bore_d, pose)
    return bodies


def cart_latch_arms(params: Params = Params()) -> list[Part]:
    """Each Cart sample's Latch arm, placed as printed (closed pose, bottom of travel)."""
    return [
        _cart_place(params, i) * latch_arm(params, bore(params, n))
        for i, n in enumerate(params.cart_nominal_bores)
    ]


def latch_arms(params: Params = Params()) -> list[Part]:
    """Each sample's Latch arm, placed as printed (closed pose)."""
    return [
        Pos(sample_x(params, i), 0, 0) * latch_arm(params, bore(params, n))
        for i, n in enumerate(params.nominal_bores)
    ]
