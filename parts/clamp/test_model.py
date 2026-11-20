import math
from dataclasses import replace
from itertools import combinations

import pytest
import trimesh
from build123d import Axis, Box, Cylinder, GeomType, Pos, Rot, Vector

from printlab import nudge
from printlab.checks import check_fit, check_part, hole_diameters
from printlab.export import PETG_DENSITY
from printlab.parts import load_part

model = load_part("clamp")

CAPS = ("cap-pivot", "cap-crank", "cap-link")
PINS = ("pin-battery", "pin-cart", "pin-pivot", "pin-crank", "pin-link")
BODIES = ("cradle", "battery-door", "cart-body", "cart-door", "lever", "link", *CAPS)
FLAT = ("lever", "link", *CAPS)  # print flat, Pin holes vertical


@pytest.fixture(scope="module")
def printed():
    return model.build()


@pytest.fixture(scope="module")
def closed():
    return model.build(pose="closed")


@pytest.fixture(scope="module")
def opened():
    return model.build(pose="open")


@pytest.fixture(scope="module")
def centre():
    return model.build(pose="centre")


# --- As printed ---


def test_prints_every_body_apart_as_one_valid_solid_and_no_pins(printed):
    assert set(printed) == set(BODIES)
    for name, body in printed.items():
        report = check_part(body)
        assert report.ok, (name, report.problems)


APART = 1.0  # mm; two 0.5 mm lines, so nothing on the bed can fuse to its neighbour


def test_bodies_lie_apart_on_the_bed_but_the_cart_collar_on_its_rib(printed):
    params = model.Params()
    for a, b in combinations(printed, 2):
        if {a, b} == {"cradle", "cart-body"}:
            continue  # the Cart collar's slide stays printed in place, a gap off its rib
        assert printed[a].distance_to(printed[b]) > APART, (a, b)
    for name, body in printed.items():
        if name != "cart-body":  # it prints on the Battery collar, a gap up
            assert body.bounding_box().min.Z == pytest.approx(0, abs=1e-6), name
    lift = printed["cart-body"].bounding_box().min.Z
    assert lift == pytest.approx(params.battery_collar_height + params.gap, abs=1e-6)


def hole_axes(body):
    """Unit axis of every round hole in a body."""
    return [
        face.axis_of_rotation.direction
        for face in body.faces().filter_by(GeomType.CYLINDER)
        if face.is_circular_concave
    ]


def test_lever_link_and_caps_print_flat_with_their_pin_holes_vertical(printed):
    for b in FLAT:
        axes = hole_axes(printed[b])
        assert axes, b
        assert all(abs(abs(a.Z) - 1) < 1e-6 for a in axes), b


def test_clamp_is_within_its_gram_budget(printed):
    # The Clamp on printed pins, before ticket #23, was about 4.9 g.
    assert model.GRAM_BUDGET == 5.0
    volume = sum(body.volume for body in printed.values())
    assert volume / 1000 * PETG_DENSITY <= model.GRAM_BUDGET


def diameters_along(body, axis):
    """Diameters of the round holes in a body whose axis runs along `axis` (0 X, 2 Z)."""
    return {
        round(2 * face.radius, 3)
        for face in body.faces().filter_by(GeomType.CYLINDER)
        if face.is_circular_concave and abs(abs(tuple(face.axis_of_rotation.direction)[axis]) - 1) < 1e-6
    }


# Ticket #20: the Pin strip's provisional middle sizes, until it is printed and judged.
PRESS = 1.85  # mm press fit, vertical and horizontal alike
CLEARANCE = 2.15  # mm clearance


def test_each_pin_hole_keeps_its_size_after_the_edge_breaks(printed):
    params = model.Params()
    assert (params.pin_press_hole_vertical, params.pin_press_hole_horizontal) == (PRESS, PRESS)
    assert params.pin_clearance_hole == CLEARANCE
    # Press fits: the Lever and the caps print flat, so vertical holes; the collar stubs'
    # knuckles stand vertical; the Cradle lug and the Cart collar's ear print their holes
    # sideways (along X as built, laid on the bed).
    assert PRESS in hole_diameters(printed["lever"])
    for cap in CAPS:
        assert hole_diameters(printed[cap]) == [PRESS], cap
    for body in ("cradle", "cart-body"):
        assert PRESS in diameters_along(printed[body], 0), body
        assert PRESS in diameters_along(printed[body], 2), body
    # Clearance: the Lever on the pivot Pin, the Link on both its Pins, the Doors on theirs.
    assert CLEARANCE in hole_diameters(printed["lever"])
    assert hole_diameters(printed["link"]) == [CLEARANCE]
    for door in ("battery-door", "cart-door"):
        assert CLEARANCE in hole_diameters(printed[door]), door


SHELL = 0.05  # mm round each Pin hole's mouth, lead-in included, that must stay as built


def hole_shell(params, pin, roofed):
    """A cylinder on the Pin's axis and as long, out past its holes' lead-ins by SHELL. A
    roofed hole (along X) adds its 45° roof: the top corner of a square standing on a corner,
    its sides tangent to the cylinder, above where they touch it."""
    box = pin.bounding_box()
    along = max(range(3), key=lambda i: tuple(box.size)[i])
    hole = params.pin_press_hole_horizontal if roofed else max(
        params.pin_press_hole_vertical, params.pin_clearance_hole
    )
    r = hole / 2 + params.pin_lead_in + SHELL
    length, c = tuple(box.size)[along], box.center()
    rotation = {0: (0, 90, 0), 1: (90, 0, 0), 2: (0, 0, 0)}[along]
    shell = Pos(c) * Rot(*rotation) * Cylinder(r, length)
    if roofed:
        square = Pos(c) * Rot(45, 0, 0) * Box(length, 2 * r, 2 * r)
        above = Pos(c.X, c.Y, c.Z + r / math.sqrt(2) + r) * Box(length, 4 * r, 2 * r)
        shell = shell + (square & above)
    return shell


PIN_PATHS = {  # the bodies each Pin passes through
    "pin-battery": ("cradle", "battery-door"),
    "pin-cart": ("cart-body", "cart-door"),
    "pin-pivot": ("cradle", "lever", "cap-pivot"),
    "pin-crank": ("lever", "link", "cap-crank"),
    "pin-link": ("cart-body", "link", "cap-link"),
}
ROOFED = {("pin-pivot", "cradle"), ("pin-link", "cart-body")}  # holes printed sideways


# A press fit 10 % wider stands a roof's apex further off its Pin than the joint margin.
WIDE_ROOF = {"pin_press_hole_horizontal": 2.05}


@pytest.mark.parametrize("sizes", [{}, WIDE_ROOF], ids=["default", "wide-roof"])
def test_edge_breaks_leave_every_pin_hole_and_its_lead_in_whole(sizes, closed):
    params = replace(model.Params(), **sizes)
    closed = model.build(params, "closed") if sizes else closed
    built = model.locked_bodies(params, params.stroke)  # locked, before the edge breaks
    for pin, bodies in PIN_PATHS.items():
        for b in bodies:
            shell = hole_shell(params, built[pin], (pin, b) in ROOFED)
            before, after = (built[b] & shell).volume, (closed[b] & shell).volume
            assert after == pytest.approx(before, abs=1e-3), (pin, b)


# --- Assembled ---


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_assembled_has_every_pin_and_cap(pose, closed, opened):
    bodies = {"closed": closed, "open": opened}[pose]
    assert set(bodies) == {*BODIES, *PINS}


PIN_CLEARANCE = 0.2  # mm a side, ticket #20: a 1.75 mm Pin in the 2.15 mm clearance hole
TURNS_IN = {  # spec #18, "Which part a Pin presses into": (turns in, presses into)
    "pin-battery": ("battery-door", "cradle"),
    "pin-cart": ("cart-door", "cart-body"),
    "pin-pivot": ("lever", "cradle"),
    "pin-crank": ("link", "lever"),
    "pin-link": ("link", "cart-body"),
}


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_each_pin_turns_in_one_part_and_presses_into_the_other(pose, closed, opened):
    bodies = {"closed": closed, "open": opened}[pose]
    for pin, (turns, holds) in TURNS_IN.items():
        report = check_fit(bodies[pin], bodies[turns], PIN_CLEARANCE)
        assert report.ok, (pose, pin, report.problems)
        assert not (bodies[pin] & bodies[holds]).solids(), (pose, pin)


def collides(bodies, moving, dx, without=()):
    """Whether `moving`, moved dx mm along X, runs into another body not named in `without`."""
    shifted = Pos(dx, 0, 0) * bodies[moving]
    return any((shifted & b).solids() for n, b in bodies.items() if n != moving and n not in without)


# Spec #18 puts a cap on each linkage Pin's outer end, +X here, so the caps hold the Lever and
# the Link that way; the other way the lug holds the Lever and the ear the Link.
CAP_HELD = (("lever", 1), ("link", 1))


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_caps_keep_the_lever_and_the_link_from_sliding_along_x(pose, closed, opened):
    bodies = {"closed": closed, "open": opened}[pose]
    for moving in ("lever", "link"):
        for dx in (-1, 1):
            assert collides(bodies, moving, dx), (pose, moving, dx)
    # The caps do that holding: with them off, the same move runs free.
    for moving, dx in CAP_HELD:
        assert not collides(bodies, moving, dx, without=CAPS), (pose, moving, dx)


def test_starts_at_the_middle_sizes(printed):
    params = model.Params()
    # Spec #10: 12.8 mm Battery bore, 12.2 mm Cart bore, 0.6 mm Stroke; plus the 0.2 offset.
    assert (params.battery_nominal_bore, params.cart_nominal_bore) == (12.8, 12.2)
    assert params.stroke == 0.6
    assert 13.0 in hole_diameters(printed["battery-door"])
    assert 13.0 in hole_diameters(printed["cradle"])
    assert 12.4 in hole_diameters(printed["cart-body"])
    assert 12.4 in hole_diameters(printed["cart-door"])


def bore_axes(body, diameter):
    """(x, y, direction) of each bore face of the given diameter."""
    axes = set()
    for face in body.faces().filter_by(GeomType.CYLINDER):
        if face.is_circular_concave and abs(2 * face.radius - diameter) < 1e-3:
            axis = face.axis_of_rotation
            d = axis.direction
            axes.add((round(axis.position.X, 4), round(axis.position.Y, 4), abs(round(d.Z, 4))))
    return axes


def test_cart_and_battery_bores_are_coaxial(closed):
    battery = bore_axes(closed["cradle"], 13.0) | bore_axes(closed["battery-door"], 13.0)
    cart = bore_axes(closed["cart-body"], 12.4) | bore_axes(closed["cart-door"], 12.4)
    assert battery and cart
    assert battery | cart == {(0.0, 0.0, 1.0)}


def fits(params):
    """The Clamp's pairs that meet, as fit pairs: at the gap unless a clearance is given; None
    only mustn't overlap."""
    return (
        # Spec #18: each Pin turns in one part at the Pin clearance, presses into the other,
        # and carries a cap pressed on its outer end (Pin caps).
        *((pin, turns, PIN_CLEARANCE) for pin, (turns, _) in TURNS_IN.items()),
        *((holds, pin, None) for pin, (_, holds) in TURNS_IN.items()),
        *((cap, cap.replace("cap-", "pin-"), None) for cap in CAPS),
        # A gap apart: the Cart collar slides on its rib, the Lever rests on its stop, the
        # Link swings past the ear, and each cap holds its part on its Pin.
        ("cradle", "cart-body"), ("cradle", "lever"), ("cart-body", "link"),
        ("cap-pivot", "lever"), ("cap-crank", "link"), ("cap-link", "link"),
        # The pivot cap clears the crank Pin orbiting it (a Params choice, no spec number).
        ("cap-pivot", "pin-crank", params.cap_clearance),
        # The Pin, not a gap, locates each Door on its stub; the Lever and the Link lie a
        # cap's layer apart, and the Link swings over the pivot cap.
        ("cradle", "battery-door", None), ("cart-body", "cart-door", None),
        ("lever", "link", None), ("cap-pivot", "link", None),
    )


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_every_pair_fits_in_both_poses(pose, closed, opened):
    """Each pair that meets fits; every other pair must not overlap."""
    bodies = {"closed": closed, "open": opened}[pose]
    params = model.Params()
    pairs = fits(params)
    assert nudge.fit_problems(bodies, pairs, params.gap, pose) == []
    paired = {frozenset(pair[:2]) for pair in pairs}
    for a, b in combinations(bodies, 2):
        if frozenset((a, b)) not in paired:
            assert not (bodies[a] & bodies[b]).solids(), (a, b, pose)


KEEP_OUT = 13.5  # mm below the Seat, spec #10: the fire button's top edge less a margin


@pytest.mark.parametrize("pose", ["closed", "open", "centre"])
def test_no_material_more_than_keep_out_below_the_seat(pose, closed, opened, centre):
    params = model.Params()
    bodies = {"closed": closed, "open": opened, "centre": centre}[pose]
    # With the Lever open the lip rests on the Cart's ledge, brass_height above the Seat.
    seat = opened["cart-body"].bounding_box().max.Z - params.lip_thickness - params.brass_height
    lowest = min(b.bounding_box().min.Z for b in bodies.values())
    assert lowest >= seat - KEEP_OUT - 1e-6


def test_cart_collar_drops_by_the_stroke_and_dips_at_centre_within_its_cap(closed, opened, centre):
    params = model.Params()
    assert params.centre_drop_cap == pytest.approx(0.1)
    for part in ("cart-body", "cart-door", "pin-cart", "pin-link", "cap-link"):
        drop = opened[part].bounding_box().min.Z - closed[part].bounding_box().min.Z
        assert drop == pytest.approx(0.6, abs=0.01), part
    extra = closed["cart-body"].bounding_box().min.Z - centre["cart-body"].bounding_box().min.Z
    assert 0 < extra <= params.centre_drop_cap
    for a, b in combinations(BODIES, 2):
        assert not (centre[a] & centre[b]).solids(), (a, b, "centre")


# The record that the linkage is unchanged (spec #18): the pin centres measured on the Clamp
# before ticket #23 (printed pins), as on the Lever strip.
PIVOT = (-16.9, 8.6018)  # (y, z) mm
CRANK = (-18.9822, 6.4421)
LINK_PIN = (-9.025, 14.8)
PAST_CENTRE = 8.0  # degrees, spec #10: the Lever locks about 8° past centre


def past_dead_centre(params, pivot, crank, link_pin):
    """Degrees the crank stands past dead centre, from the Pin centres. At dead centre the
    pivot lies on the Link, so the Link pin, on its slide along Z, stands `link_length` less
    `crank_radius` off the pivot, and the crank points straight away from it."""
    reach = params.link_length - params.crank_radius
    dy = link_pin[0] - pivot[0]
    centre_pin = (link_pin[0], pivot[1] + math.sqrt(reach**2 - dy**2))
    away = math.atan2(pivot[1] - centre_pin[1], pivot[0] - centre_pin[0])
    locked = math.atan2(crank[1] - pivot[1], crank[0] - pivot[0])
    return abs(math.degrees(locked - away))


def axis_yz(pin):
    c = pin.bounding_box().center()
    return c.Y, c.Z


def test_locked_lever_is_past_centre_where_it_was_and_lies_flat_on_its_stop(closed):
    params = model.Params()
    pivot, crank, link_pin = (axis_yz(closed[p]) for p in ("pin-pivot", "pin-crank", "pin-link"))
    for got, before in zip((pivot, crank, link_pin), (PIVOT, CRANK, LINK_PIN)):
        assert got == pytest.approx(before, abs=1e-3)
    assert params.past_centre == PAST_CENTRE
    assert past_dead_centre(params, pivot, crank, link_pin) == pytest.approx(PAST_CENTRE, abs=1e-3)
    assert check_fit(closed["cradle"], closed["lever"], params.gap).ok
    # The Link's pull turns the Lever further; 3° that way it runs into the Cradle: its stop.
    torque = (crank[0] - pivot[0]) * (link_pin[1] - pivot[1]) - (crank[1] - pivot[1]) * (
        link_pin[0] - pivot[0]
    )
    pushed = closed["lever"].rotate(Axis((0, *pivot), (1, 0, 0)), math.copysign(3, torque))
    assert (closed["cradle"] & pushed).solids()
    # Lying flat: the Lever and Link stand no higher than the Cradle.
    top = closed["cradle"].bounding_box().max.Z
    assert max(closed[b].bounding_box().max.Z for b in ("lever", "link")) <= top


SHARP = 115.0  # degrees; a convex edge whose faces meet at less than this is sharp


def exposed_run(edge, others, reach):
    """The longest stretch of `edge` farther than `reach` from every other body, judged on
    points every SAMPLE mm, so an edge that only ends at a joint still counts as exposed."""
    near = [o for o in others if edge.distance_to(o) <= reach]
    if not near:
        return edge.length
    n = max(2, math.ceil(edge.length / SAMPLE) + 1)
    run = best = 0
    for i in range(n):
        q = edge.position_at(i / (n - 1))
        run = run + 1 if all(o.distance_to(q) > reach for o in near) else 0
        best = max(best, run)
    return max(0, best - 1) * edge.length / (n - 1)


SAMPLE = 0.1  # mm between points judged along an edge


def sharp_outside_edges(bodies, name, params):
    """Sharp convex edges of one body that face the outside: not a joint or parting line
    (within the gap of another body), not in a bore, with an exposed stretch longer than
    the run-out left where two edge breaks meet."""
    body = bodies[name]
    solid = body.solids()[0]
    faces_of = {}
    for face in body.faces():
        for edge in face.edges():
            faces_of.setdefault(edge, []).append(face)
    others = [b for n, b in bodies.items() if n != name]
    in_bore = max(params.battery_nominal_bore, params.cart_nominal_bore) / 2 + params.fdm_offset
    found = []
    for edge, faces in faces_of.items():
        if len(faces) != 2 or edge.length <= 2 * params.edge_break:
            continue
        q = edge.position_at(0.5)
        if math.hypot(q.X, q.Y) < in_bore:
            continue
        n1, n2 = faces[0].normal_at(q), faces[1].normal_at(q)
        between = 180 - math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2)))))
        if between >= SHARP or solid.is_inside(q + (n1 - n2) * 0.01):  # blunt or concave
            continue
        if exposed_run(edge, others, params.gap + params.joint_margin) <= 2 * params.edge_break:
            continue
        found.append((name, round(edge.length, 2), round(q.X, 2), round(q.Y, 2), round(q.Z, 2)))
    return found


def test_no_outside_edge_is_left_sharp(closed):
    params = model.Params()
    assert params.edge_break >= 0.3  # mm, a named size, big enough to feel in a pocket
    sharp = [e for name in BODIES for e in sharp_outside_edges(closed, name, params)]
    assert sharp == []


OVERHANG = 0.75  # -normal.Z beyond which a face needs support: about 49° from vertical


def mesh(body):
    vertices, triangles = body.tessellate(tolerance=0.02, angular_tolerance=0.1)
    return trimesh.Trimesh([(v.X, v.Y, v.Z) for v in vertices], triangles)


def test_prints_without_supports(printed):
    """Every downward face is on the bed or rests, across the gap, on another body."""
    params = model.Params()
    unsupported = []
    for name, body in printed.items():
        m = mesh(body)
        down = m.triangles_center[(m.face_normals[:, 2] < -OVERHANG) & (m.area_faces > 1e-4)]
        others = [o for n, o in printed.items() if n != name]
        for x, y, z in {tuple(round(float(v), 2) for v in c) for c in down}:
            if z < 1e-3:  # on the bed
                continue
            if min(o.distance_to(Vector(x, y, z)) for o in others) <= params.gap + 0.06:
                continue  # rests on another body across the gap
            if is_ledge(body, x, y, z):
                continue
            unsupported.append((name, x, y, z))
    assert sorted(unsupported) == []


LEDGE = 0.5  # mm; a ledge no wider than one 0.5 mm line prints without support


def is_ledge(body, x, y, z):
    """Whether the body's own wall stands under (x, y, z) within one line width."""
    solid = body.solids()[0]
    return any(
        solid.is_inside(Vector(x + r * math.cos(a), y + r * math.sin(a), z - 0.1))
        for r in (LEDGE / 2, LEDGE)
        for a in (i * math.pi / 4 for i in range(8))
    )


POSES = ("print", "closed", "open")  # as printed first


@pytest.fixture(scope="module")
def nudges():
    """Every numeric field of the full Clamp's Params nudged ±10 %, edge breaks and all,
    run once across worker processes: {(field, factor): problems}."""
    return nudge.audit("clamp", "fit_pairs", POSES)


@pytest.mark.slow
@pytest.mark.parametrize("factor", nudge.FACTORS)
@pytest.mark.parametrize("field", nudge.numeric_fields(model.Params))
def test_survives_plus_minus_ten_percent(field, factor, nudges):
    assert nudges[(field, factor)] == []


def test_slim_outline_fits_its_footprint_limit(closed):
    params = model.Params()
    lo = [min(getattr(b.bounding_box().min, a) for b in closed.values()) for a in "XY"]
    hi = [max(getattr(b.bounding_box().max, a) for b in closed.values()) for a in "XY"]
    width, depth = hi[0] - lo[0], hi[1] - lo[1]
    limit_x, limit_y = params.footprint_limit
    assert width <= limit_x and depth <= limit_y
    # The limit is a pocket size, not a loose bound: within 1 mm of the outline.
    assert limit_x - width < 1 and limit_y - depth < 1


def test_cradle_above_the_battery_collar_is_only_as_wide_as_the_rib_head(closed):
    """Above the Battery collar the Cradle carries only the rib; the rest is trimmed."""
    params = model.Params()
    top = closed["cradle"].bounding_box().max.Z
    z = (params.battery_collar_height + top) / 2
    slab = Pos(0, 0, z) * Box(100, 100, 0.1)
    assert (closed["cradle"] & slab).bounding_box().size.X <= params.rib_head_width + 1e-6


MIN_WALL = 1.2  # mm, CLAUDE.md design rule for load-bearing walls


def test_each_latch_arm_is_a_horizontal_beam_bending_in_the_layer_plane(closed):
    params = model.Params()
    arms = model.latch_arms(params)
    assert set(arms) == {"battery-door", "cart-door"}
    # Spec #10: the 12 mm Battery collar's Latch runs its full height.
    assert arms["battery-door"].bounding_box().size.Z == pytest.approx(12.0)
    for door, arm in arms.items():
        # The arm belongs to its Door; the edge breaks shave only its corners.
        assert (closed[door] & arm).volume > 0.95 * arm.volume, door
        size = arm.bounding_box().size
        thickness, length = sorted((size.X, size.Y))
        # Long along a horizontal axis, thin along the other, tall in Z: it can only bend
        # about Z, so it deflects within the XY (layer) plane.
        assert length > 3 * thickness, door
        assert size.Z > 2 * thickness, door
        assert thickness >= MIN_WALL, door


def test_no_load_bearing_wall_is_under_the_minimum(closed):
    params = model.Params()
    for b in ("lever", "link"):
        size = closed[b].bounding_box().size
        assert size.X >= MIN_WALL and size.Y >= MIN_WALL, b
    for field in ("wall", "knuckle_wall", "carriage_wall", "cradle_back_depth", "lug_width"):
        assert getattr(params, field) >= MIN_WALL, field
    for hole in (params.pin_press_hole_vertical, params.pin_clearance_hole):
        assert model.knuckle_radius(params) - hole / 2 >= MIN_WALL
    # A cap only keeps a part on its Pin and carries no load: a 1.0 mm wall at the defaults.
    assert model.cap_radius(params) - params.pin_press_hole_vertical / 2 == pytest.approx(1.0)
