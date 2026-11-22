import itertools
import math
from dataclasses import replace

import pytest
from build123d import Axis, GeomType, Pos, Vector

from printlab import nudge
from printlab.checks import check_fit, check_part, hole_diameters
from printlab.export import PETG_DENSITY
from printlab.parts import load_part

model = load_part("clamp-lever-strip")

STROKES = {"0-3": 0.3, "0-6": 0.6, "0-9": 0.9}  # spec #10: Strokes of 0.3, 0.6 and 0.9 mm
CAPS = ("cap-pivot", "cap-crank", "cap-link")
PINS = ("pin-battery", "pin-cart", "pin-pivot", "pin-crank", "pin-link")
PRINTED = ("cradle", "battery-door", "cart-body", "cart-door", "lever", "link", *CAPS)
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


def of(bodies, label):
    """One Clamp's bodies, by their names without the Stroke label."""
    return {n.removesuffix(f"-{label}"): b for n, b in bodies.items() if n.endswith(f"-{label}")}


# --- As printed ---


def test_prints_every_body_apart_as_one_valid_solid_and_no_pins(printed):
    assert set(printed) == {f"{b}-{s}" for b in PRINTED for s in STROKES}
    for name, body in printed.items():
        report = check_part(body)
        assert report.ok, (name, report.problems)


APART = 1.0  # mm; two 0.5 mm lines, so nothing on the bed can fuse to its neighbour


def test_bodies_lie_apart_on_the_bed_but_the_cart_collar_on_its_rib(printed):
    params = model.Params()
    for a, b in itertools.combinations(printed, 2):
        if {a.rsplit("-", 2)[0], b.rsplit("-", 2)[0]} == {"cradle", "cart-body"} and a[-3:] == b[-3:]:
            continue  # the Cart collar slides on its rib, a gap off, as before
        assert printed[a].distance_to(printed[b]) > APART, (a, b)
    for name, body in printed.items():
        if not name.startswith("cart-body-"):  # it prints on the Battery collar, a gap up
            assert body.bounding_box().min.Z == pytest.approx(0, abs=1e-6), name
    for label in STROKES:
        lift = printed[f"cart-body-{label}"].bounding_box().min.Z
        assert lift == pytest.approx(params.battery_collar_height + params.gap, abs=1e-6)


def hole_axes(body):
    """Unit axis of every round hole in a body."""
    return [
        face.axis_of_rotation.direction
        for face in body.faces().filter_by(GeomType.CYLINDER)
        if face.is_circular_concave
    ]


def test_lever_link_and_caps_print_flat_with_their_pin_holes_vertical(printed):
    for label in STROKES:
        for b in FLAT:
            axes = hole_axes(printed[f"{b}-{label}"])
            assert axes, b
            assert all(abs(abs(a.Z) - 1) < 1e-6 for a in axes), b


OVERHANG = 45.0  # degrees from vertical a face may lean before it needs support
SAMPLES = 5  # points per face edge-to-edge where the overhang is read
LEDGE = 0.5  # mm; a ledge no wider than one 0.5 mm line prints without support


def is_ledge(body, point):
    """Whether the body's own wall stands under the point within one line width."""
    solid = body.solids()[0]
    return any(
        solid.is_inside(point + Vector(r * math.cos(a), r * math.sin(a), -0.1))
        for r in (LEDGE / 2, LEDGE)
        for a in (i * math.pi / 4 for i in range(8))
    )


def test_prints_without_supports(printed):
    params = model.Params()
    limit = -math.sin(math.radians(OVERHANG)) - 1e-3
    unsupported = []
    for name, body in printed.items():
        others = [b for n, b in printed.items() if n != name]
        for face in body.faces():
            if face.bounding_box().min.Z < 1e-3:
                continue  # on the bed
            for u, v in itertools.product(range(SAMPLES), repeat=2):
                at = (u / (SAMPLES - 1), v / (SAMPLES - 1))
                point = face.position_at(*at)
                if face.distance_to(point) > 1e-6 or face.normal_at(*at).Z >= limit:
                    continue
                if min(o.distance_to(point) for o in others) <= params.gap + 1e-3:
                    continue  # rests on the body below across the gap
                if not is_ledge(body, point):
                    unsupported.append((name, tuple(round(c, 2) for c in point)))
    assert unsupported == []


def test_strip_is_within_its_gram_budget(printed):
    assert model.GRAM_BUDGET == 20.0  # spec #10: the Lever strip is about 20 g
    volume = sum(body.volume for body in printed.values())
    assert volume / 1000 * PETG_DENSITY <= model.GRAM_BUDGET


def test_bores_default_to_the_middle_sizes_plus_the_fdm_offset(printed):
    for label in STROKES:
        # Battery 12.8 and Cart 12.2 mm nominal (spec #10), plus the 0.2 mm offset.
        assert 13.0 in hole_diameters(printed[f"battery-door-{label}"])
        assert 13.0 in hole_diameters(printed[f"cradle-{label}"])
        assert 12.4 in hole_diameters(printed[f"cart-body-{label}"])
        assert 12.4 in hole_diameters(printed[f"cart-door-{label}"])


# --- Pin holes ---

# Press fits told apart from each other, so each hole shows which size it was built at.
DISTINCT = dict(pin_press_hole_vertical=1.8, pin_press_hole_horizontal=1.9)


@pytest.fixture(scope="module")
def distinct():
    params = replace(model.Params(), **DISTINCT)
    return params, model.clamp(params, 0.6, "print")


def diameters_along(body, axis):
    """Diameters of the round holes in a body whose axis runs along `axis` (0 X, 2 Z)."""
    return {
        round(2 * face.radius, 3)
        for face in body.faces().filter_by(GeomType.CYLINDER)
        if face.is_circular_concave and abs(abs(tuple(face.axis_of_rotation.direction)[axis]) - 1) < 1e-6
    }


def test_each_pin_hole_is_the_size_for_its_fit_and_print_direction(distinct):
    params, bodies = distinct
    vertical, horizontal = params.pin_press_hole_vertical, params.pin_press_hole_horizontal
    clearance = params.pin_clearance_hole
    # The Lever and the caps print flat: the press fit for a vertical hole.
    assert vertical in hole_diameters(bodies["lever"])
    for cap in CAPS:
        assert hole_diameters(bodies[cap]) == [vertical], cap
    # The Cradle lug and the Cart collar's ear print upright, their holes along X.
    assert horizontal in diameters_along(bodies["cradle"], 0)
    assert horizontal in diameters_along(bodies["cart-body"], 0)
    # The Lever turns on the pivot Pin and the Link on both of its Pins.
    assert clearance in hole_diameters(bodies["lever"])
    assert hole_diameters(bodies["link"]) == [clearance]
    # The collar hinges: press fit in the stubs, clearance in the Doors.
    assert vertical in diameters_along(bodies["cradle"], 2)
    assert clearance in hole_diameters(bodies["battery-door"])
    assert clearance in hole_diameters(bodies["cart-door"])


# --- Assembled ---


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_assembled_has_every_pin_and_cap(pose, closed, opened):
    bodies = {"closed": closed, "open": opened}[pose]
    assert set(bodies) == {f"{b}-{s}" for b in (*PRINTED, *PINS) for s in STROKES}


PIN_CLEARANCE = 0.15  # mm a side: a 1.75 mm Pin in the 2.05 mm clearance hole
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
    for label in STROKES:
        clamp = of(bodies, label)
        for pin, (turns, holds) in TURNS_IN.items():
            report = check_fit(clamp[pin], clamp[turns], PIN_CLEARANCE)
            assert report.ok, (label, pose, pin, report.problems)
            assert not (clamp[pin] & clamp[holds]).solids(), (label, pose, pin)


def fits(params):
    """One Clamp's pairs that meet, as fit pairs: at the gap unless a clearance is given; None
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
    paired = {frozenset(pair[:2]) for pair in pairs}
    for label in STROKES:
        clamp = of(bodies, label)
        assert nudge.fit_problems(clamp, pairs, params.gap, pose) == [], label
        for a, b in itertools.combinations(clamp, 2):
            if frozenset((a, b)) not in paired:
                assert not (clamp[a] & clamp[b]).solids(), (label, a, b, pose)


def collides(clamp, moving, dx, without=()):
    """Whether `moving`, moved dx mm along X, runs into another body not named in `without`."""
    shifted = Pos(dx, 0, 0) * clamp[moving]
    return any((shifted & b).solids() for n, b in clamp.items() if n != moving and n not in without)


# Spec #18 puts a cap on each linkage Pin's outer end, +X here, so the caps hold the Lever and
# the Link that way; the other way the lug holds the Lever and the ear the Link.
CAP_HELD = (("lever", 1), ("link", 1))


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_caps_keep_the_lever_and_the_link_from_sliding_along_x(pose, closed, opened):
    bodies = {"closed": closed, "open": opened}[pose]
    for label in STROKES:
        clamp = of(bodies, label)
        for moving in ("lever", "link"):
            for dx in (-1, 1):
                assert collides(clamp, moving, dx), (label, pose, moving, dx)
        # The caps do that holding: with them off, the same move runs free.
        for moving, dx in CAP_HELD:
            assert not collides(clamp, moving, dx, without=CAPS), (label, pose, moving, dx)


def test_each_cap_and_pin_end_flush_with_the_joint(closed):
    params = model.Params()
    for label in STROKES:
        clamp = of(closed, label)
        for pin, cap in (("pin-pivot", "cap-pivot"), ("pin-crank", "cap-crank"), ("pin-link", "cap-link")):
            assert clamp[pin].bounding_box().max.X == pytest.approx(clamp[cap].bounding_box().max.X)
            assert clamp[pin].bounding_box().size.Y == pytest.approx(params.pin_stock_diameter)
        # Inner ends: flush with the Lever's inner face, and down on the ear's hole floor.
        assert clamp["pin-crank"].bounding_box().min.X == pytest.approx(
            clamp["lever"].bounding_box().min.X
        )
        assert (Pos(-0.05, 0, 0) * clamp["pin-link"] & clamp["cart-body"]).solids()
        assert not (clamp["pin-link"] & clamp["cart-body"]).solids()


# --- The linkage, unchanged by the move to Pins ---

# The record that the linkage is unchanged (spec #18): the pin centres measured on the bodies
# before ticket #22 (printed pins), every Clamp alike, Stroke apart.
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


def linkage_pins(clamp):
    return axis_yz(clamp["pin-pivot"]), axis_yz(clamp["pin-crank"]), axis_yz(clamp["pin-link"])


def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def test_locked_lever_is_past_centre_where_it_was_and_rests_on_its_stop(closed):
    params = model.Params()
    for label in STROKES:
        clamp = of(closed, label)
        pivot, crank, link = linkage_pins(clamp)
        for got, before in zip((pivot, crank, link), (PIVOT, CRANK, LINK_PIN)):
            assert got == pytest.approx(before, abs=1e-3), label
        assert params.past_centre == PAST_CENTRE
        assert past_dead_centre(params, pivot, crank, link) == pytest.approx(PAST_CENTRE, abs=1e-3), label
        # The Link's pull on the crank Pin turns the Lever (sign of its moment about the
        # pivot); turned a further 3° that way, the Lever runs into the Cradle: its stop.
        torque = cross(pivot, crank, link)
        axis = Axis((0, *pivot), (1, 0, 0))
        pushed = clamp["lever"].rotate(axis, math.copysign(3, torque))
        assert (clamp["cradle"] & pushed).solids(), label
        report = check_fit(clamp["cradle"], clamp["lever"], params.gap)
        assert report.ok, (label, report.problems)


def test_each_cart_collar_drops_by_its_stroke_from_open_to_locked(closed, opened):
    for label, stroke in STROKES.items():
        for part in ("cart-body", "cart-door", "pin-link", "cap-link"):
            key = f"{part}-{label}"
            drop = opened[key].bounding_box().min.Z - closed[key].bounding_box().min.Z
            assert drop == pytest.approx(stroke, abs=0.01), key


def test_extra_drop_at_centre_is_within_its_cap(closed):
    params = model.Params()
    assert params.centre_drop_cap == pytest.approx(0.1)
    centre = model.build(pose="centre")
    for label in STROKES:
        key = f"cart-body-{label}"
        extra = closed[key].bounding_box().min.Z - centre[key].bounding_box().min.Z
        # Over centre: the collar dips below locked at centre, by no more than the cap.
        assert 0 < extra <= params.centre_drop_cap, (label, extra)
        for name, body in of(centre, label).items():
            if name != "cart-body" and not name.startswith("pin-"):
                assert not (body & centre[key]).solids(), (name, "centre")


KEEP_OUT = 13.5  # mm below the Seat, spec #10: the fire button's top edge less a margin


@pytest.mark.parametrize("pose", ["closed", "open", "centre"])
def test_no_material_more_than_keep_out_below_the_seat(pose, closed, opened):
    params = model.Params()
    bodies = {"closed": closed, "open": opened}.get(pose) or model.build(pose=pose)
    for label in STROKES:
        # With the Lever open the lip rests on the Cart's ledge, brass_height above the Seat.
        lip_top = opened[f"cart-body-{label}"].bounding_box().max.Z
        seat = lip_top - params.lip_thickness - params.brass_height
        lowest = min(b.bounding_box().min.Z for b in of(bodies, label).values())
        assert lowest >= seat - KEEP_OUT - 1e-6, (label, pose)


# --- Strength ---

# N, assumed: about 2 kg, a firm one-hand press of a Cart onto a Battery, well above what a
# 510 Seat's contact spring needs. The real Preload is NEEDS_TEST (spec #10).
PRELOAD = 20.0
# MPa, OVERTURE HS PETG tensile strength across layers (Z, the lower), TDS V5.2, from
# docs/research/overture-hs-petg.md §3. Shear taken as half of it (Tresca).
PETG_TENSILE = 45.7


def pin_loads(clamp):
    """{Pin: N} on each linkage Pin under the Preload, from the locked linkage's statics."""
    pivot, crank, link = linkage_pins(clamp)
    # The Link is pinned at both ends and carries nothing else, so it pulls along itself; the
    # Cart collar slides along Z, so the pull's Z part is the Preload.
    dy, dz = link[0] - crank[0], link[1] - crank[1]
    length = math.hypot(dy, dz)
    pull = PRELOAD * length / abs(dz)
    on_crank = (pull * dy / length, pull * dz / length)  # on the Lever, toward the Link pin
    # The pull turns the Lever onto its stop, where it first touches the Cradle's back at its
    # foot, farthest below the pivot; the Cradle pushes back along Y, square to its back.
    lever = clamp["lever"].bounding_box()
    foot_z = lever.min.Z
    turning = (crank[0] - pivot[0]) * on_crank[1] - (crank[1] - pivot[1]) * on_crank[0]
    stop = turning / (foot_z - pivot[1])  # its moment about the pivot balances the pull's
    assert stop < 0  # it pushes the Lever away from the Cradle: the Lever is on its stop
    # The pivot Pin takes the rest: the pull and the stop's push together.
    return {
        "pin-pivot": math.hypot(on_crank[0] + stop, on_crank[1]),
        "pin-crank": pull,
        "pin-link": pull,
    }


def test_the_most_loaded_pin_carries_its_load_in_shear_within_petgs_strength(closed):
    params = model.Params()
    assert params.pin_stock_diameter == 1.75  # spec #18: a 1.75 mm filament offcut
    area = math.pi * params.pin_stock_diameter**2 / 4
    for label in STROKES:
        loads = pin_loads(of(closed, label))
        # Each Pin crosses one shear plane, between the part it presses into and the one it
        # turns in.
        assert max(loads.values()) / area <= PETG_TENSILE / 2, (label, loads)


# --- Walls ---

MIN_WALL = 1.2  # mm, CLAUDE.md design rule for load-bearing walls


def test_no_load_bearing_wall_is_under_the_minimum(printed):
    params = model.Params()
    for label in STROKES:
        for b in ("lever", "link"):
            box = printed[f"{b}-{label}"].bounding_box()
            assert min(box.size.X, box.size.Y, box.size.Z) >= MIN_WALL, b
    assert params.knuckle_wall >= MIN_WALL  # ring round every Pin hole in a joint
    assert params.cradle_back_depth >= MIN_WALL
    assert params.lug_width >= MIN_WALL
    for hole in (params.pin_press_hole_vertical, params.pin_clearance_hole):
        assert model.knuckle_radius(params) - hole / 2 >= MIN_WALL - 1e-9
    # A cap only keeps a part on its Pin and carries no load. It is as wide as the pivot
    # cap can be and clear the crank Pin orbiting it: a 0.925 mm wall at the defaults.
    assert model.cap_radius(params) - params.pin_press_hole_vertical / 2 == pytest.approx(0.925)


# --- Nudge audit ---

# Fields that feed the linkage: the Lever, Link, caps, their Pin holes and the Cart collar's
# slide. The collar builders' own fields are nudged by the Test plate, which shares them.
LINKAGE_FIELDS = (
    "lever_face_x", "pivot_offset", "crank_radius", "link_length", "past_centre",
    "link_pin_height", "lever_width", "link_width", "lug_width", "cap_thickness",
    "cap_clearance", "cradle_back_depth", "battery_collar_height", "gap", "knuckle_wall",
    "pin_lead_in", "pin_lead_in_angle", "pin_roof_angle", "print_gap",
)  # The Pin stock and Pin holes are fixed (CollarParams.FIXED).
POSES = ("print", "closed", "open")  # as printed first


def test_passes_the_audits_checks_unnudged():
    assert nudge.problems("clamp-lever-strip", "gap", 1.0, "fit_pairs", POSES) == []


@pytest.fixture(scope="module")
def nudges():
    """Every linkage field nudged ±10 %, run once across worker processes."""
    return nudge.audit("clamp-lever-strip", "fit_pairs", POSES, only=LINKAGE_FIELDS)


@pytest.mark.slow
@pytest.mark.parametrize("factor", nudge.FACTORS)
@pytest.mark.parametrize("field", LINKAGE_FIELDS)
def test_linkage_survives_plus_minus_ten_percent(field, factor, nudges):
    assert nudges[(field, factor)] == []
