"""Clamp test plate: Battery collar samples at three bores.

Each sample is a short Cradle stub with a print-in-place hinged collar Door, shut by
a hook-snap Latch with a thumb tab, and labelled with its nominal bore. It prints
closed, Battery axis vertical (Z). Pick the bore that grips the Battery.

Sample frame (closed pose): bore centred on the Z axis, Door on +Y, Cradle stub on
-Y, hinge on -X, Latch on +X. The Door opens anticlockwise (seen from above) about
the hinge axis.

The builders (`hinge_axis_x`, `cradle_stub`, `door`, `latch_arm`) take the bore and
collar height as arguments so the Cart collar samples, Lever strip and Clamp can
reuse them with their own sizes.
"""

import math
from dataclasses import dataclass

from build123d import (
    Align,
    Axis,
    Box,
    Cylinder,
    Part,
    Polygon,
    Pos,
    RegularPolygon,
    Text,
    extrude,
)

GRAM_BUDGET = 8.0  # g; the CLI warns above this


@dataclass(frozen=True)
class Params:
    # Samples
    nominal_bores: tuple[float, ...] = (12.6, 12.8, 13.0)  # mm, labelled sizes
    fdm_offset: float = 0.2  # mm added to each bore; FDM holes print undersize
    pitch: float = 36.0  # mm between sample centres; room for an open Door
    # Collar
    collar_height: float = 12.0  # mm, Battery collar
    wall: float = 1.6  # mm, collar ring wall (load-bearing)
    gap: float = 0.3  # mm, print-in-place clearance between Door and stub
    open_angle: float = 90.0  # degrees the Door swings in the open pose
    # Hinge: three knuckles, stub-Door-stub, with an integral pin on the stub
    pin_diameter: float = 2.4  # mm (load-bearing)
    knuckle_wall: float = 1.2  # mm, Door knuckle ring around the pin (load-bearing)
    knuckle_cone: float = 45.0  # degrees from vertical; spiked knuckle ends print unsupported
    knuckle_facets: int = 16  # facets around each knuckle spike
    # Latch: horizontal hook arm on the Door, catch on the stub
    latch_height: float = 6.0  # mm, arm height from the bed
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
    # Plate
    spine_width: float = 5.0  # mm, strip joining the stubs behind the samples
    spine_height: float = 2.0  # mm
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
    tip = 0.05  # flat top, inside the pin, so the spike never degenerates to a point
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
    arm = _box(x0, x1, y_tip, y_root + 0.01, p.latch_height)
    # Hook: square holding face, lead-in chamfer on the tip side.
    lead = p.hook_length - p.hook_land
    hook = _prism(
        [(x0 + 0.01, y_hold), (x0 - p.catch_depth, y_hold),
         (x0 - p.catch_depth, y_tip + lead), (x0 + 0.01, y_tip)],
        p.latch_height,
    )
    tab = _box(x1 - 0.01, x1 + p.tab_reach, y_tip, y_tip + p.tab_width, p.latch_height)
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


def label_name(nominal: float) -> str:
    return f"{nominal:.1f}".replace(".", "-")


def sample_x(p: Params, i: int) -> float:
    return (i - (len(p.nominal_bores) - 1) / 2) * p.pitch


def _plate(p: Params) -> Part:
    bores = [bore(p, n) for n in p.nominal_bores]
    y_top = -(min(bores) / 2 + p.wall / 2)  # inside the thinnest ring's wall
    x0 = sample_x(p, 0) + hinge_axis_x(p, bores[0])
    x1 = sample_x(p, len(bores) - 1) + _outer_radius(p, bores[-1])
    spine = _box(x0, x1, y_top - p.spine_width, y_top, p.spine_height)
    plate = spine
    for i, (nominal, bore_d) in enumerate(zip(p.nominal_bores, bores)):
        x = sample_x(p, i)
        plate = plate + Pos(x, 0, 0) * cradle_stub(p, bore_d, p.collar_height)
        label = Text(f"{nominal:.1f}", p.label_size)
        label = Pos(x, y_top - p.spine_width / 2, p.spine_height) * extrude(
            label, p.label_relief
        )
        plate = plate + label
        plate = plate - Pos(x, 0, 0) * _bore_cut(bore_d, p.collar_height)
    return plate


def build(params: Params = Params(), pose: str = "closed") -> dict[str, Part]:
    bodies = {"plate": _plate(params)}
    for i, nominal in enumerate(params.nominal_bores):
        bore_d = bore(params, nominal)
        closed = door(params, bore_d, params.collar_height)
        bodies[f"door-{label_name(nominal)}"] = Pos(sample_x(params, i), 0, 0) * pose_door(
            params, closed, bore_d, pose
        )
    return bodies


def latch_arms(params: Params = Params()) -> list[Part]:
    """Each sample's Latch arm, placed as printed (closed pose)."""
    return [
        Pos(sample_x(params, i), 0, 0) * latch_arm(params, bore(params, n))
        for i, n in enumerate(params.nominal_bores)
    ]
