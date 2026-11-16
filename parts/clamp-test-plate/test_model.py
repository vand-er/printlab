import pytest
from build123d import Align, Axis, Box, Pos

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
    assert params.knuckle_wall >= MIN_WALL
    assert params.pin_diameter >= 2 * MIN_WALL


def fit_pairs():
    """Every pair that moves against another: each Door and Cart collar body on the plate,
    each Cart Door on its body."""
    params = model.Params()
    doors = [f"door-{model.label_name(n)}" for n in params.nominal_bores]
    carts = [model.label_name(n) for n in params.cart_nominal_bores]
    return tuple(
        [("plate", d) for d in doors]
        + [("plate", f"cart-body-{c}") for c in carts]
        + [(f"cart-body-{c}", f"cart-door-{c}") for c in carts]
    )


@pytest.fixture(scope="module")
def nudges():
    """Every numeric field nudged ±10 %, run once across worker processes."""
    return nudge.audit("clamp-test-plate", fit_pairs(), (("closed", "bottom"), ("open", "top")))


@pytest.mark.slow
@pytest.mark.parametrize("factor", nudge.FACTORS)
@pytest.mark.parametrize("field", nudge.numeric_fields(model.Params))
def test_survives_plus_minus_ten_percent(field, factor, nudges):
    # Perturbation audit: nudging any dimension must not break a body or a fit.
    assert nudges[(field, factor)] == []


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_each_door_fits_the_plate_without_overlap_or_rattle(pose):
    params = model.Params()
    bodies = model.build(params, pose)
    doors = [name for name in bodies if name.startswith("door-")]
    assert len(doors) == 3
    for name in doors:
        report = check_fit(bodies["plate"], bodies[name], params.gap)
        assert report.ok, (name, pose, report.problems)


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
def test_each_cart_door_fits_its_body_without_overlap_or_rattle(pose, slide):
    params = model.Params()
    bodies = model.build(params, pose, slide)
    for body, door in cart_pairs(bodies):
        report = check_fit(body, door, params.gap)
        assert report.ok, (pose, slide, report.problems)
        assert not (bodies["plate"] & door).solids()


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
