from dataclasses import replace

import pytest

from vander.checks import check_part, hole_diameters
from vander.parts import load_part

model = load_part("hole-gauge")


def test_has_one_hole_per_nominal_diameter():
    params = model.Params()
    expected = [round(params.smallest + i * params.step, 3) for i in range(params.count)]
    assert hole_diameters(model.build()) == expected
    assert expected[0] == 3.0 and expected[-1] == 4.8


def test_passes_part_checks():
    report = check_part(model.build())
    assert report.ok, report.problems


def test_web_between_holes_is_at_least_two_perimeters():
    params = model.Params()
    largest = params.smallest + (params.count - 1) * params.step
    assert params.pitch - largest >= 0.8


@pytest.mark.parametrize("factor", [0.9, 1.1])
@pytest.mark.parametrize("field", ["thickness", "margin", "pitch"])
def test_survives_plus_minus_ten_percent(field, factor):
    # Perturbation audit: nudging a dimension must not break the part.
    params = model.Params()
    nudged = replace(params, **{field: getattr(params, field) * factor})
    assert check_part(model.build(nudged)).ok
