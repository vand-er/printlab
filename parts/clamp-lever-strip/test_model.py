import math
from dataclasses import replace
from itertools import combinations

import pytest
from build123d import Axis, GeomType

from printlab.checks import check_fit, check_part, hole_diameters
from printlab.export import PETG_DENSITY
from printlab.parts import load_part

model = load_part("clamp-lever-strip")

STROKES = {"0-3": 0.3, "0-6": 0.6, "0-9": 0.9}  # spec #10: Strokes of 0.3, 0.6 and 0.9 mm
BODIES = ("cradle", "battery-door", "cart-body", "cart-door", "lever", "link")


@pytest.fixture(scope="module")
def closed():
    return model.build()


@pytest.fixture(scope="module")
def opened():
    return model.build(pose="open")


def test_three_clamps_each_one_valid_solid_per_body(closed):
    assert set(closed) == {f"{b}-{s}" for b in BODIES for s in STROKES}
    for name, body in closed.items():
        report = check_part(body)
        assert report.ok, (name, report.problems)


def pin_centres(body, radius):
    """(y, z) of each round pin along X on a body, read from its circular edges."""
    found = set()
    for edge in body.edges().filter_by(GeomType.CIRCLE):
        if abs(edge.radius - radius) < 1e-6 and abs(abs(edge.normal().X) - 1) < 1e-6:
            c = edge.arc_center
            found.add((round(c.Y, 4), round(c.Z, 4)))
    return found


def toggle_pins(bodies, label, params):
    """(pivot, crank pin, Link pin) of one Clamp, from its Cradle, Lever and Cart collar."""
    r = params.pin_diameter / 2
    (pivot,) = pin_centres(bodies[f"cradle-{label}"], r)
    (crank,) = pin_centres(bodies[f"lever-{label}"], r)
    (link,) = pin_centres(bodies[f"cart-body-{label}"], r)
    return pivot, crank, link


def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def test_locked_lever_is_past_centre_on_the_locking_side_and_rests_on_its_stop(closed):
    params = model.Params()
    for label in STROKES:
        pivot, crank, link = toggle_pins(closed, label, params)
        # Not collinear: the crank pin sits about the overtravel (8°) past the pivot-Link line.
        u = (pivot[0] - crank[0], pivot[1] - crank[1])
        v = (link[0] - pivot[0], link[1] - pivot[1])
        past = math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1]))
        assert abs(past) == pytest.approx(8.0, abs=1.0), label
        # The Link's pull on the crank pin turns the Lever (sign of its moment about the
        # pivot); turned a further 3° that way, the Lever runs into the Cradle: its stop.
        torque = cross(pivot, crank, link)  # (crank - pivot) × (link - crank)
        axis = Axis((0, *pivot), (1, 0, 0))
        pushed = closed[f"lever-{label}"].rotate(axis, math.copysign(3, torque))
        assert (closed[f"cradle-{label}"] & pushed).solids(), label
        # ...and turned back towards centre it is free, so it rests there now.
        report = check_fit(closed[f"cradle-{label}"], closed[f"lever-{label}"], params.gap)
        assert report.ok, (label, report.problems)


def test_extra_drop_at_centre_is_within_its_cap(closed):
    params = model.Params()
    assert params.centre_drop_cap == pytest.approx(0.1)
    centre = model.build(pose="centre")
    for label in STROKES:
        key = f"cart-body-{label}"
        extra = closed[key].bounding_box().min.Z - centre[key].bounding_box().min.Z
        # Over centre: the collar dips below locked at centre, by no more than the cap.
        assert 0 < extra <= params.centre_drop_cap, (label, extra)
        for name, body in centre.items():
            if name.endswith(label) and name != key:
                assert not (body & centre[key]).solids(), (name, "centre")


# Moving pairs and their clearance; every other pair in a Clamp only must not overlap.
FIT_PAIRS = (
    ("cradle", "battery-door"),
    ("cradle", "cart-body"),
    ("cart-body", "cart-door"),
    ("cradle", "lever"),
    ("lever", "link"),
    ("cart-body", "link"),
)


def check_clamp(bodies, label, params, pairs=FIT_PAIRS, others=True):
    problems = []
    for a, b in pairs:
        report = check_fit(bodies[f"{a}-{label}"], bodies[f"{b}-{label}"], params.gap)
        problems += [(a, b, p) for p in report.problems]
    if others:
        for a, b in combinations(BODIES, 2):
            if (a, b) not in pairs and (bodies[f"{a}-{label}"] & bodies[f"{b}-{label}"]).solids():
                problems.append((a, b, "overlap"))
    return problems


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_every_pair_fits_in_both_poses(pose, closed, opened):
    bodies = {"closed": closed, "open": opened}[pose]
    for label in STROKES:
        assert check_clamp(bodies, label, model.Params()) == [], (label, pose)


KEEP_OUT = 13.5  # mm below the Seat, spec #10: the fire button's top edge less a margin


@pytest.mark.parametrize("pose", ["closed", "open", "centre"])
def test_no_material_more_than_keep_out_below_the_seat(pose, closed, opened):
    params = model.Params()
    bodies = {"closed": closed, "open": opened}.get(pose) or model.build(pose=pose)
    for label in STROKES:
        # With the Lever open the lip rests on the Cart's ledge, brass_height above the Seat.
        lip_top = opened[f"cart-body-{label}"].bounding_box().max.Z
        seat = lip_top - params.lip_thickness - params.brass_height
        lowest = min(b.bounding_box().min.Z for n, b in bodies.items() if n.endswith(label))
        assert lowest >= seat - KEEP_OUT - 1e-6, (label, pose)


def test_strip_is_within_its_gram_budget(closed):
    assert model.GRAM_BUDGET == 20.0  # spec #10: the Lever strip is about 20 g
    volume = sum(body.volume for body in closed.values())
    assert volume / 1000 * PETG_DENSITY <= model.GRAM_BUDGET


def test_bores_default_to_the_middle_sizes_plus_the_fdm_offset(closed):
    for label in STROKES:
        # Battery 12.8 and Cart 12.2 mm nominal (spec #10), plus the 0.2 mm offset.
        assert 13.0 in hole_diameters(closed[f"battery-door-{label}"])
        assert 13.0 in hole_diameters(closed[f"cradle-{label}"])
        assert 12.4 in hole_diameters(closed[f"cart-body-{label}"])
        assert 12.4 in hole_diameters(closed[f"cart-door-{label}"])


def test_each_clamp_prints_on_the_bed(closed):
    for label in STROKES:
        for b in ("cradle", "battery-door", "lever", "link"):
            assert closed[f"{b}-{label}"].bounding_box().min.Z == pytest.approx(0, abs=1e-6)


MIN_WALL = 1.2  # mm, CLAUDE.md design rule for load-bearing walls


def test_no_load_bearing_wall_is_under_the_minimum(closed):
    params = model.Params()
    for label in STROKES:
        for b in ("lever", "link"):
            box = closed[f"{b}-{label}"].bounding_box()
            assert box.size.X >= MIN_WALL and box.size.Y >= MIN_WALL, b
    assert params.knuckle_wall >= MIN_WALL  # ring around every pin
    assert params.pin_diameter >= 2 * MIN_WALL
    assert params.spine_depth >= MIN_WALL
    assert params.lug_width >= MIN_WALL


# Fields that feed the Lever, Link and the Cart collar's slide. The collar builders' own
# fields are nudged by the Test plate, which shares them.
TOGGLE_FIELDS = (
    "toggle_x", "pivot_offset", "crank_radius", "link_length", "overtravel",
    "link_pin_height", "lever_width", "link_width", "lug_width", "head_width", "head_size",
    "spine_depth", "battery_collar_height", "gap", "pin_diameter", "knuckle_wall",
)
TOGGLE_BODIES = ("cradle", "cart-body", "lever", "link")


@pytest.mark.parametrize("factor", [0.9, 1.1])
@pytest.mark.parametrize("field", TOGGLE_FIELDS)
def test_toggle_survives_plus_minus_ten_percent(field, factor):
    params = model.Params()
    params = replace(params, **{field: getattr(params, field) * factor})
    stroke = max(params.strokes)  # the widest swing
    poses = {pose: model.clamp(params, stroke, pose) for pose in ("closed", "open")}
    for pose, bodies in poses.items():
        bodies = {f"{n}-x": b for n, b in bodies.items() if n in TOGGLE_BODIES}
        for name, body in bodies.items():
            assert check_part(body).ok, (name, pose)
        pairs = tuple((a, b) for a, b in FIT_PAIRS if a in TOGGLE_BODIES and b in TOGGLE_BODIES)
        assert check_clamp(bodies, "x", params, pairs, others=False) == [], pose
    drop = (poses["open"]["cart-body"].bounding_box().min.Z
            - poses["closed"]["cart-body"].bounding_box().min.Z)
    assert drop == pytest.approx(stroke, abs=0.01)


def test_each_cart_collar_drops_by_its_stroke_from_open_to_locked(closed, opened):
    for label, stroke in STROKES.items():
        for part in ("cart-body", "cart-door"):
            key = f"{part}-{label}"
            drop = opened[key].bounding_box().min.Z - closed[key].bounding_box().min.Z
            assert drop == pytest.approx(stroke, abs=0.01), key
