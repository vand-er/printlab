import math
from dataclasses import fields

import pytest

from printlab import nudge
from printlab.checks import check_fit, check_part
from printlab.collar import CollarParams
from printlab.export import PETG_DENSITY
from printlab.parts import load_part

model = load_part("clamp-gap-strip")

# Ticket #16: one sample per print-in-place gap, named after it.
DOORS = {"door-0-30": 0.3, "door-0-40": 0.4, "door-0-50": 0.5, "door-0-60": 0.6}


def doors(bodies):
    return {name: body for name, body in bodies.items() if name.startswith("door-")}


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_strip_carries_exactly_the_four_gaps_read_from_the_geometry(pose):
    bodies = model.build(pose=pose)
    # The narrowest gap between each Door and the strip is the gap the sample prints at.
    measured = {name: round(bodies["strip"].distance_to(door), 3) for name, door in doors(bodies).items()}
    assert measured == DOORS


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_each_door_fits_its_stub_at_its_own_gap(pose):
    bodies = model.build(pose=pose)
    assert set(doors(bodies)) == set(DOORS)
    for name, gap in DOORS.items():
        report = check_fit(bodies["strip"], bodies[name], gap)
        assert report.ok, (name, pose, report.problems)


def test_open_doors_clear_each_other():
    found = doors(model.build(pose="open"))
    names = sorted(found)
    for a, b in zip(names, names[1:]):
        assert not (found[a] & found[b]).solids(), (a, b)


def test_every_body_is_one_valid_solid_that_fits_the_printer():
    for name, body in model.build().items():
        report = check_part(body)
        assert report.ok, (name, report.problems)


OVERHANG = 45.0  # degrees from vertical a face may lean before it needs support


def test_prints_without_supports():
    limit = -math.sin(math.radians(OVERHANG)) - 1e-3
    for name, body in model.build().items():
        assert body.bounding_box().min.Z == pytest.approx(0, abs=1e-6), name
        for face in body.faces():
            if face.bounding_box().min.Z < 1e-3:
                continue  # on the bed
            normal = face.normal_at(face.center())
            assert normal.Z >= limit, (name, face.center(), normal)


def test_strip_is_within_its_gram_budget():
    assert model.GRAM_BUDGET == 3.0  # ticket #16: warn above 3 g
    volume = sum(body.volume for body in model.build().values())
    assert volume / 1000 * PETG_DENSITY <= model.GRAM_BUDGET


OWN_FIELDS = [
    f for f in nudge.numeric_fields(model.Params) if f not in {c.name for c in fields(CollarParams)}
]


@pytest.mark.slow
@pytest.mark.parametrize("factor", nudge.FACTORS)
@pytest.mark.parametrize("field", OWN_FIELDS)
def test_survives_plus_minus_ten_percent(field, factor):
    # Perturbation audit over this part's own fields; each Door is checked at its own gap.
    params = nudge.nudged(model.Params(), field, factor)
    for pose in ("closed", "open"):
        bodies = model.build(params, pose)
        if pose == "closed":
            for name, body in bodies.items():
                assert check_part(body).ok, (name, check_part(body).problems)
        for name, gap in model.door_gaps(params).items():
            report = check_fit(bodies["strip"], bodies[name], gap)
            assert report.ok, (pose, name, report.problems)
