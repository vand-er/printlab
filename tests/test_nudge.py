"""The nudge audit's fit checks within one pose."""

from build123d import Box, Pos

from printlab import nudge

CLEARANCE = 0.3  # mm


def test_a_pair_naming_a_body_absent_from_the_pose_is_skipped():
    # A `print` pose has no Pins, so a pair with a Pin is not checked there.
    bodies = {"door": Box(5, 5, 5)}
    assert nudge.fit_problems(bodies, (("pin-hinge", "door"),), CLEARANCE, "print") == []


def test_a_pair_present_in_the_pose_is_still_checked():
    # Overlapping bodies, so a checked pair must report a problem.
    bodies = {"door": Box(5, 5, 5), "pin-hinge": Pos(1, 0, 0) * Box(5, 5, 5)}
    pairs = (("pin-hinge", "door"), ("pin-other", "door", CLEARANCE))
    found = nudge.fit_problems(bodies, pairs, CLEARANCE, "closed")
    assert found and all(f.startswith("closed pin-hinge/door: ") for f in found), found
