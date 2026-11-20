"""Clamp lever strip: three small Clamps, one per Stroke, to pick the Stroke on the real Cart.

Each Clamp is a Cradle carrying a Battery collar, a sliding Cart collar stacked on it and
an over-centre Lever. The Lever pivots on the back of the Cradle (opposite the fire
button); a Link from its crank Pin to a Pin on the Cart collar pulls the collar down by
the Stroke as the Lever goes over centre. The stop is the Lever lying flat on the Cradle.

Every joint that turns is assembled on a Pin (ADR 0003): the collar hinges and the three
linkage joints, each linkage Pin with a Pin cap on its outer end. The `print` pose (the
default, and what is exported) lays the bodies apart on the bed without Pins: the Cradle
upright, Battery axis vertical (Z), the Cart collar's body on its rib, the Doors beside
their stubs, and the Lever, Link and caps flat behind. `closed` and `open` are the
assembled Clamps, each Pin a `pin-…` body.

The Clamp builders, frame and shared sizes (`ClampParams`) live in `printlab.clamp`,
shared with the full Clamp; this part adds the strip and a Stroke label on a tag off each
Cradle's back.
"""

from dataclasses import dataclass

from build123d import Part, Pos, Text, extrude

from printlab import clamp as clamps
from printlab.checks import FitPair
from printlab.clamp import (  # noqa: F401  cap_radius and knuckle_radius, for the tests
    ClampParams,
    cap_radius,
    cradle_back_y,
    knuckle_radius,
    locked_bodies,
    pose_bodies,
)
from printlab.collar import EMBED, Pose, box, carriage_half_width

GRAM_BUDGET = 20.0  # g; the CLI warns above this


@dataclass(frozen=True)
class Params(ClampParams):
    # The strip
    strokes: tuple[float, ...] = (0.3, 0.6, 0.9)  # mm, one Clamp per Stroke
    pitch: float = 30.0  # mm between Clamp centres; room for open Doors
    # Labels
    label_size: float = 3.5  # mm font size of the Stroke labels
    label_relief: float = 0.4  # mm
    tag_length: float = 10.0  # mm, label tag along X, off the Cradle back's -X side
    tag_depth: float = 5.0  # mm, along Y
    tag_thickness: float = 1.0  # mm


def label_tag(p: Params, stroke: float) -> Part:
    """The tag off the Cradle back's -X side, labelled with the Stroke."""
    _, front = cradle_back_y(p)
    hw = carriage_half_width(p)
    tag = box(-hw - p.tag_length, -hw + EMBED, front - p.tag_depth, front, p.tag_thickness)
    text = Text(f"{stroke:.1f}", p.label_size)
    label = Pos(-hw - p.tag_length / 2, front - p.tag_depth / 2, p.tag_thickness) * extrude(
        text, p.label_relief
    )
    return tag + label


def clamp(p: Params, stroke: float, pose: Pose | str = Pose.PRINT) -> dict[str, Part]:
    """One labelled Clamp's bodies in its own frame, in `pose` (see `Pose`)."""
    bodies = locked_bodies(p, stroke)
    bodies["cradle"] = bodies["cradle"] + label_tag(p, stroke)
    return pose_bodies(p, stroke, bodies, pose)


def label_name(stroke: float) -> str:
    return f"{stroke:.1f}".replace(".", "-")


def clamp_x(p: Params, i: int) -> float:
    return (i - (len(p.strokes) - 1) / 2) * p.pitch


def build(params: Params = Params(), pose: Pose | str = Pose.PRINT) -> dict[str, Part]:
    """Named bodies of all three Clamps, side by side along X."""
    bodies = {}
    for i, stroke in enumerate(params.strokes):
        place = Pos(clamp_x(params, i), 0, 0)
        for name, part in clamp(params, stroke, pose).items():
            bodies[f"{name}-{label_name(stroke)}"] = place * part
    return bodies


def fit_pairs(p: Params, pose: Pose | str) -> tuple[FitPair, ...]:
    """Each Clamp's fit pairs in `pose` (`printlab.clamp.fit_pairs`), for the nudge audit."""
    return tuple(
        (f"{a}-{s}", f"{b}-{s}", *rest)
        for s in (label_name(stroke) for stroke in p.strokes)
        for a, b, *rest in clamps.fit_pairs(p, pose)
    )
