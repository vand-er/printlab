"""A part's first layers compared with a reference print's, on slice reports built in code."""

from printlab.islands import Island
from printlab.reference import Invalid, Passed, Smaller, compare_first_layers
from printlab.slicing import SliceReport

SETTINGS = {
    "initial_layer_print_height": "0.2",
    "initial_layer_line_width": "0.5",
    "initial_layer_speed": ("50",),
    "curr_bed_type": "Textured PEI Plate",
    "textured_plate_temp_initial_layer": ("70",),
    "nozzle_temperature_initial_layer": ("240",),
}


def _report(*islands: Island, **changed) -> SliceReport:
    return SliceReport(1.0, 60.0, (), islands, {**SETTINGS, **changed})


def _island(layer: int, area: float, body: str = "Cradle") -> Island:
    return Island(layer, area, (0.0, 0.0), body)


def test_differing_first_layer_settings_are_invalid_and_listed():
    part = _report(
        _island(1, 50.0),
        initial_layer_print_height="0.25",
        nozzle_temperature_initial_layer=("250",),
    )
    reference = _report(_island(1, 50.0))

    assert compare_first_layers(part, reference) == Invalid(
        ("initial_layer_print_height", "nozzle_temperature_initial_layer")
    )


def test_a_setting_only_one_slice_has_is_invalid():
    part = _report(_island(1, 50.0), initial_layer_infill_speed=("105",))

    assert compare_first_layers(part, _report(_island(1, 50.0))) == Invalid(("initial_layer_infill_speed",))


def test_an_island_smaller_than_the_reference_s_smallest_in_its_layer_warns_with_both_areas():
    part = _report(_island(1, 80.0, "Cradle"), _island(1, 9.8, "cap 3"), _island(2, 9.8, "cap 3"))
    reference = _report(_island(1, 12.1), _island(1, 30.0), _island(2, 5.0))

    assert compare_first_layers(part, reference) == (Smaller(_island(1, 9.8, "cap 3"), 12.1),)


def test_islands_at_least_the_reference_s_smallest_pass():
    part = _report(_island(1, 12.1, "cap 1"), _island(1, 80.0), _island(2, 6.0))
    reference = _report(_island(1, 12.1), _island(1, 30.0), _island(2, 5.0))

    assert compare_first_layers(part, reference) == Passed({1: (12.1, 12.1), 2: (6.0, 5.0)})


def test_a_layer_the_reference_has_no_islands_in_is_not_compared():
    part = _report(_island(1, 20.0), _island(2, 1.0))

    assert compare_first_layers(part, _report(_island(1, 12.1))) == Passed({1: (20.0, 12.1)})
