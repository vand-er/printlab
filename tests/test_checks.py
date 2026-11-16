from build123d import Box, Cylinder, Pos

from printlab.checks import X1C_BUILD_VOLUME, check_part, hole_diameters


def plate_with_holes(*diameters):
    plate = Box(60, 20, 5)
    for i, d in enumerate(diameters):
        plate -= Pos(-20 + i * 10, 0, 0) * Cylinder(d / 2, 5)
    return plate


def test_hole_diameters_reports_through_holes_only():
    plate = plate_with_holes(3.4, 4.2)
    # The outer round of a cylinder (a peg) is convex and must not count as a hole.
    peg = Pos(25, 0, 5) * Cylinder(2, 5)
    assert hole_diameters(plate + peg) == [3.4, 4.2]


def test_clean_part_passes():
    report = check_part(plate_with_holes(3.4))
    assert report.ok, report.problems


def test_two_separate_solids_fail():
    floating = Box(10, 10, 10) + Pos(50, 0, 0) * Box(10, 10, 10)
    report = check_part(floating)
    assert not report.ok
    assert any("solid" in p for p in report.problems)


def test_overlapping_solids_count_as_one_after_fusing():
    # build123d fuses overlapping booleans, so this is one solid, not two.
    report = check_part(Box(10, 10, 10) + Pos(5, 0, 0) * Box(10, 10, 10))
    assert report.ok, report.problems


def test_part_too_big_for_x1c_fails():
    too_long = Box(X1C_BUILD_VOLUME[0] + 10, 20, 5)
    report = check_part(too_long)
    assert not report.ok
    assert any("build volume" in p for p in report.problems)


def test_part_that_fits_only_when_rotated_still_fails():
    # Orientation is the designer's decision, so check the part as modelled.
    tall = Box(10, 10, X1C_BUILD_VOLUME[2] + 1)
    assert not check_part(tall).ok
