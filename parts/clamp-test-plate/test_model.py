from dataclasses import fields, replace

import pytest
from build123d import Align, Box, Pos

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


def nudged(params, field, factor):
    value = getattr(params, field)
    if isinstance(value, tuple):
        value = tuple(v * factor for v in value)
    elif isinstance(value, int):
        value = round(value * factor)
    else:
        value = value * factor
    return replace(params, **{field: value})


@pytest.mark.parametrize("factor", [0.9, 1.1])
@pytest.mark.parametrize("field", [f.name for f in fields(model.Params)])
def test_survives_plus_minus_ten_percent(field, factor):
    # Perturbation audit: nudging any dimension must not break a body or a fit.
    params = nudged(model.Params(), field, factor)
    for pose in ("closed", "open"):
        bodies = model.build(params, pose)
        for name, body in bodies.items():
            assert check_part(body).ok, (name, pose)
            if name.startswith("door-"):
                report = check_fit(bodies["plate"], body, params.gap)
                assert report.ok, (name, pose, report.problems)


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_each_door_fits_the_plate_without_overlap_or_rattle(pose):
    params = model.Params()
    bodies = model.build(params, pose)
    doors = [name for name in bodies if name.startswith("door-")]
    assert len(doors) == 3
    for name in doors:
        report = check_fit(bodies["plate"], bodies[name], params.gap)
        assert report.ok, (name, pose, report.problems)
