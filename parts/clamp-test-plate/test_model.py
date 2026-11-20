import itertools
import math

import pytest
from build123d import Align, Axis, Box, Pos, Vector

from printlab import nudge
from printlab.checks import check_fit, check_part, hole_diameters
from printlab.export import PETG_DENSITY
from printlab.parts import load_part

model = load_part("clamp-test-plate")


def test_each_sample_bore_is_its_nominal_plus_the_fdm_offset():
    bodies = model.build()
    # Nominal 12.6, 12.8, 13.0 mm plus the 0.2 mm default offset (spec #10).
    expected = {"door-12-6": 12.8, "door-12-8": 13.0, "door-13-0": 13.2}
    for door, bore in expected.items():
        assert bore in hole_diameters(bodies[door])
    assert {12.8, 13.0, 13.2} <= set(hole_diameters(bodies["plate"]))


# --- Collar hinges on Pins (#21) ---

DOORS = ("door-12-6", "door-12-8", "door-13-0")


def test_each_stub_holds_a_press_fit_pin_hole_and_each_door_a_clearance_hole():
    params = model.Params()
    bodies = model.build(params)
    assert params.pin_press_hole_vertical in hole_diameters(bodies["plate"])
    for name in DOORS:
        assert params.pin_clearance_hole in hole_diameters(bodies[name])
    for name in CART_NAMES:
        assert params.pin_press_hole_vertical in hole_diameters(bodies[f"cart-body-{name}"])
        assert params.pin_clearance_hole in hole_diameters(bodies[f"cart-door-{name}"])


APART = 1.0  # mm; two 0.5 mm lines, so nothing on the bed can fuse to its neighbour


def test_prints_each_door_apart_from_its_stub_without_pins():
    bodies = model.build()
    assert set(bodies) == set(model.build(pose="print"))
    assert not [name for name in bodies if name.startswith("pin-")]
    for a, b in itertools.combinations(bodies, 2):
        if a == "plate" and b.startswith("cart-body-"):
            continue  # each Cart collar body slides on its rib, a gap off
        assert bodies[a].distance_to(bodies[b]) > APART, (a, b)


PIN_CLEARANCE = 0.2  # mm a side: a 1.75 mm Pin in the 2.15 mm clearance hole


def hinges(bodies):
    """(fixed half, Door, Pin) of every collar sample, assembled."""
    return [(bodies["plate"], bodies[d], bodies[d.replace("door-", "pin-")]) for d in DOORS] + [
        (bodies[f"cart-body-{n}"], bodies[f"cart-door-{n}"], bodies[f"pin-cart-{n}"])
        for n in CART_NAMES
    ]


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_each_door_turns_on_a_pin_held_in_its_stub(pose):
    bodies = model.build(pose=pose)
    found = hinges(bodies)
    assert len(found) == 6
    for stub, door, pin in found:
        report = check_fit(pin, door, PIN_CLEARANCE)
        assert report.ok, (pose, report.problems)
        assert not (pin & stub).solids()
        assert not (door & stub).solids()
        # Cut flush: the Pin runs the hinge's whole height and no further.
        assert pin.bounding_box().size.Z == pytest.approx(door.bounding_box().size.Z, abs=1e-6)


def test_each_door_opens_about_its_pin():
    params = model.Params()
    closed, opened = model.build(params, "closed"), model.build(params, "open")
    for (_, shut, pin), (_, swung, pin_open) in zip(hinges(closed), hinges(opened)):
        centre = pin.bounding_box().center()
        assert (pin_open.bounding_box().center() - centre).length < 1e-6  # the Pin stays put
        turned = shut.rotate(Axis(centre, (0, 0, 1)), params.open_angle)
        assert (turned - swung).volume < 1e-3 and (swung - turned).volume < 1e-3


PROBE = 0.002  # mm, side of the thin column that reads the knuckles' ends
PROBE_RADIUS = 1.8  # mm off the Pin's axis: in the knuckle wall, past the lead-ins


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_knuckles_stack_the_shared_spacing_apart_along_each_pin(pose):
    params = model.Params()
    assert params.knuckle_spacing == 0.2  # spec #18
    for stub, door, pin in hinges(model.build(params, pose)):
        c = pin.bounding_box().center()
        probe = Pos(c.X - PROBE_RADIUS, c.Y, c.Z) * Box(PROBE, PROBE, 2 * pin.bounding_box().size.Z)
        spans = sorted(
            (s.bounding_box().min.Z, s.bounding_box().max.Z)
            for part in (stub, door)
            for s in (part & probe).solids()
        )
        assert len(spans) == 3, spans  # stub, Door, stub
        for (_, top), (bottom, _) in zip(spans, spans[1:]):
            assert bottom - top == pytest.approx(0.2, abs=2 * PROBE)


def test_each_latch_hook_holds_half_a_millimetre_behind_its_keeper():
    params = model.Params()
    bodies = model.build(params, "closed")
    half = params.pitch / 2  # reaches across this sample only
    corner = (Align.MIN, Align.MAX, Align.MIN)
    for i, name in enumerate(DOORS):
        x = model.sample_x(params, i)
        # Below the split, on the Latch side: the Door's hook, and the stub's keeper.
        hook = bodies[name] & Pos(x, 0, 0) * Box(half, half, half, align=corner)
        depth = params.keeper_ramp + params.keeper_flat
        keeper = bodies["plate"] & Pos(x, -params.gap, 0) * Box(half, depth, half, align=corner)
        hold = keeper.bounding_box().max.X - hook.bounding_box().min.X
        assert hold == pytest.approx(0.5, abs=1e-6), name


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


def test_prints_without_supports():
    limit = -math.sin(math.radians(OVERHANG)) - 1e-3
    for name, body in model.build().items():
        for face in body.faces():
            if face.bounding_box().min.Z < 1e-3:
                continue  # on the bed
            # Read the normal across the face, not only at its centre: a round hole turns.
            for u, v in itertools.product(range(SAMPLES), repeat=2):
                at = (u / (SAMPLES - 1), v / (SAMPLES - 1))
                point = face.position_at(*at)
                if face.distance_to(point) > 1e-6:
                    continue  # off a trimmed face, such as inside a half ring
                if face.normal_at(*at).Z < limit:
                    assert is_ledge(body, point), (name, point, face.normal_at(*at))


def test_prints_closed_standing_on_the_bed():
    params = model.Params()
    for name, body in model.build(params).items():
        box = body.bounding_box()
        assert box.min.Z == pytest.approx(0, abs=1e-6), name
        # Nothing stands above the collar but the plate's labels, which sit low.
        assert box.max.Z <= params.collar_height + 1e-6, name


def test_every_body_is_one_valid_solid_that_fits_the_printer():
    for name, body in model.build().items():
        report = check_part(body)
        assert report.ok, (name, report.problems)


def test_each_latch_arm_is_a_horizontal_beam_bending_in_the_layer_plane():
    bodies = model.build()
    doors = [body for name, body in bodies.items() if name.startswith("door-")]
    arms = model.latch_arms()
    assert len(arms) == len(doors) == 3
    for arm in arms:
        # The arm belongs to a Door.
        assert any(abs((door & arm).volume - arm.volume) < 1e-6 for door in doors)
        size = arm.bounding_box().size
        thickness, length = sorted((size.X, size.Y))
        # Long along a horizontal axis, thin along the other horizontal axis, tall in Z:
        # it can only bend about Z, so it deflects within the XY (layer) plane.
        assert length > 3 * thickness
        assert size.Z > 2 * thickness


def test_plate_is_within_its_gram_budget():
    volume = sum(body.volume for body in model.build().values())
    assert model.GRAM_BUDGET == 8.0  # spec #10: the Test plate is about 8 g
    assert volume / 1000 * PETG_DENSITY <= model.GRAM_BUDGET


MIN_WALL = 1.2  # mm, CLAUDE.md design rule for load-bearing walls


def test_no_load_bearing_wall_is_under_the_minimum():
    params = model.Params()
    bodies = model.build(params)
    for i, name in enumerate(n for n in bodies if n.startswith("door-")):
        # The collar ring, probed through the middle of each Door (+Y of its bore).
        probe = Pos(model.sample_x(params, i), 0, 0) * Box(
            0.01, 40, 1, align=(Align.CENTER, Align.MIN, Align.CENTER)
        )
        ring = (bodies[name] & Pos(0, 0, params.collar_height / 2) * probe).bounding_box()
        assert ring.size.Y >= MIN_WALL
    for arm in model.latch_arms(params):
        assert min(arm.bounding_box().size.X, arm.bounding_box().size.Y) >= MIN_WALL
    # Round each Pin hole, the press fit's and the clearance's (spec #18).
    for hole in (params.pin_press_hole_vertical, params.pin_clearance_hole):
        assert model.knuckle_radius(params) - hole / 2 >= MIN_WALL


POSES = (("print", "bottom"), ("closed", "bottom"), ("open", "top"))  # as printed first


def test_passes_the_audits_checks_unnudged():
    pairs = model.fit_pairs(model.Params())
    # Each Pin turns in its Door at the Pin clearance, in both assembled poses.
    for name in [*DOORS, *(f"cart-door-{n}" for n in CART_NAMES)]:
        pin = name.replace("cart-door-", "pin-cart-").replace("door-", "pin-")
        assert (pin, name, pytest.approx(PIN_CLEARANCE)) in pairs
    assert nudge.problems("clamp-test-plate", "gap", 1.0, "fit_pairs", POSES) == []


@pytest.fixture(scope="module")
def nudges():
    """Every numeric field nudged ±10 %, run once across worker processes. Pairs come from
    the model's fit_pairs, since nudging a bore renames its bodies."""
    return nudge.audit("clamp-test-plate", "fit_pairs", POSES)


@pytest.mark.slow
@pytest.mark.parametrize("factor", nudge.FACTORS)
@pytest.mark.parametrize("field", nudge.numeric_fields(model.Params))
def test_survives_plus_minus_ten_percent(field, factor, nudges):
    # Perturbation audit: nudging any dimension must not break a body or a fit.
    assert nudges[(field, factor)] == []


# --- Cart collar samples (#12) ---

CART_NAMES = ("12-0", "12-2", "12-4")


def cart_pairs(bodies):
    """(sliding body, Door) of each Cart collar sample."""
    return [(bodies[f"cart-body-{n}"], bodies[f"cart-door-{n}"]) for n in CART_NAMES]


def test_each_cart_collar_bore_is_its_nominal_plus_the_fdm_offset():
    bodies = model.build()
    # Nominal 12.0, 12.2, 12.4 mm plus the 0.2 mm default offset (spec #10).
    for name, bore in zip(CART_NAMES, (12.2, 12.4, 12.6)):
        assert bore in hole_diameters(bodies[f"cart-body-{name}"])
        assert bore in hole_diameters(bodies[f"cart-door-{name}"])


def test_cart_collar_grips_brass_only():
    params = model.Params()
    # Spec #10: brass about 10 mm tall less a 1 mm margin, so about 9 mm.
    assert params.brass_height - params.brass_margin == pytest.approx(9.0)
    for body, door in cart_pairs(model.build(params)):
        for part in (body, door):
            box = part.bounding_box()
            assert box.min.Z == pytest.approx(0, abs=1e-6)
            assert box.size.Z == pytest.approx(9.0, abs=1e-6)


def test_cart_lip_clears_the_glass_and_is_smaller_than_the_bore():
    params = model.Params()
    lip = round(params.glass_diameter + 2 * params.lip_clearance, 3)
    pairs = cart_pairs(model.build(params))
    for nominal, pair in zip(params.cart_nominal_bores, pairs):
        assert params.glass_diameter < lip < model.bore(params, nominal)
        for part in pair:
            assert lip in hole_diameters(part)


@pytest.mark.parametrize("slide", ["bottom", "top"])
def test_each_cart_collar_slides_on_its_stub_without_overlap_or_rattle(slide):
    params = model.Params()
    bodies = model.build(params, slide=slide)
    for body, door in cart_pairs(bodies):
        report = check_fit(bodies["plate"], body, params.gap)
        assert report.ok, (slide, report.problems)
        assert not (bodies["plate"] & door).solids()


def test_cart_collar_slides_its_named_slide_and_stops_there():
    params = model.Params()
    bottom = model.build(params, slide="bottom")
    top = model.build(params, slide="top")
    assert params.slide == pytest.approx(2.0)  # spec #10: about 2 mm
    for name in CART_NAMES:
        for part in ("body", "door"):
            key = f"cart-{part}-{name}"
            rise = top[key].bounding_box().min.Z - bottom[key].bounding_box().min.Z
            assert rise == pytest.approx(2.0, abs=1e-6)
        # Pushed any further up, the body hits the stub's stop. The stop faces are at 45°,
        # so `gap` normal to them is gap·√2 vertically.
        past = Pos(0, 0, params.gap * 2**0.5 + 0.05) * top[f"cart-body-{name}"]
        assert (top["plate"] & past).solids()


def test_cart_rib_stops_the_collar_turning():
    params = model.Params()
    bodies = model.build(params)
    for i, (body, _) in enumerate(cart_pairs(bodies)):
        x, y = model.cart_centre(params, i)
        axis = Axis((x, y, 0), (0, 0, 1))
        for angle in (-3, 3):
            assert (bodies["plate"] & body.rotate(axis, angle)).solids(), angle


@pytest.mark.parametrize("pose", ["closed", "open"])
@pytest.mark.parametrize("slide", ["bottom", "top"])
def test_each_cart_door_turns_on_its_pin_anywhere_on_the_slide(pose, slide):
    bodies = model.build(pose=pose, slide=slide)
    for name, (body, door) in zip(CART_NAMES, cart_pairs(bodies)):
        pin = bodies[f"pin-cart-{name}"]
        report = check_fit(pin, door, PIN_CLEARANCE)
        assert report.ok, (pose, slide, report.problems)
        for part in (body, door, pin):
            assert not (bodies["plate"] & part).solids()
        assert not (body & door).solids() and not (body & pin).solids()


def test_each_cart_latch_arm_bends_in_the_layer_plane():
    doors = [door for _, door in cart_pairs(model.build())]
    arms = model.cart_latch_arms()
    assert len(arms) == 3
    for arm in arms:
        assert any(abs((door & arm).volume - arm.volume) < 1e-6 for door in doors)
        size = arm.bounding_box().size
        thickness, length = sorted((size.X, size.Y))
        assert length > 3 * thickness
        assert size.Z > 2 * thickness
        assert thickness >= MIN_WALL
