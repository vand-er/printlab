"""The nudge audit's fit checks within one pose, and which fields it nudges."""

from dataclasses import dataclass
from typing import ClassVar

from build123d import Box, Pos

from printlab import nudge

CLEARANCE = 0.3  # mm


def test_fields_a_params_type_fixes_are_not_nudged():
    # A Pin hole picked from a printed strip is proven; nudging it 10 % tests a fit nobody prints.
    @dataclass(frozen=True)
    class Params:
        FIXED: ClassVar[frozenset[str]] = frozenset({"hole"})
        hole: float = 1.85
        wall: float = 1.2

    assert nudge.numeric_fields(Params) == ["wall"]


def test_a_pair_naming_a_body_absent_from_the_pose_is_skipped():
    # A `print` pose has no Pins, so a pair with a Pin is not checked there.
    bodies = {"door": Box(5, 5, 5)}
    assert nudge.fit_problems(bodies, (("pin-hinge", "door"),), CLEARANCE, "print") == []


def test_a_pair_with_no_clearance_is_only_checked_for_overlap():
    # A Door located by its Pin sits closer than the gap at its knuckles; it only mustn't overlap.
    near = {"door": Box(5, 5, 5), "plate": Pos(5.1, 0, 0) * Box(5, 5, 5)}
    assert nudge.fit_problems(near, (("plate", "door", None),), CLEARANCE, "closed") == []
    into = {"door": Box(5, 5, 5), "plate": Pos(4, 0, 0) * Box(5, 5, 5)}
    found = nudge.fit_problems(into, (("plate", "door", None),), CLEARANCE, "closed")
    assert found and found[0].startswith("closed plate/door: "), found


def test_a_pair_present_in_the_pose_is_still_checked():
    # Overlapping bodies, so a checked pair must report a problem.
    bodies = {"door": Box(5, 5, 5), "pin-hinge": Pos(1, 0, 0) * Box(5, 5, 5)}
    pairs = (("pin-hinge", "door"), ("pin-other", "door", CLEARANCE))
    found = nudge.fit_problems(bodies, pairs, CLEARANCE, "closed")
    assert found and all(f.startswith("closed pin-hinge/door: ") for f in found), found
