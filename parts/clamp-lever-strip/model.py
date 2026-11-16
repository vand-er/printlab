"""Clamp lever strip: three small Clamps, one per Stroke, to pick the Stroke on the real Cart.

Each Clamp is a Cradle carrying a Battery collar, a sliding Cart collar stacked on it and
an over-centre Lever. The Lever pivots on the back of the Cradle (opposite the fire
button); a Link from its crank pin to a pin on the Cart collar pulls the collar down by
the Stroke as the Lever goes over centre. The stop is the Lever lying flat on the Cradle.
Everything prints closed and in place, Battery axis vertical (Z), Lever locked.

The Clamp builders, frame and shared sizes (`ClampParams`) live in `printlab.clamp`,
shared with the full Clamp; this part adds the strip and a Stroke label on a tag off each
Cradle's back.
"""

from dataclasses import dataclass

from build123d import Part, Pos, Text, extrude

from printlab.clamp import ClampParams, cradle_back_y, locked_bodies, pose_bodies
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


def clamp(p: Params, stroke: float, pose: Pose | str = Pose.CLOSED) -> dict[str, Part]:
    """One labelled Clamp's bodies in its own frame, in `pose` (see `Pose`)."""
    bodies = locked_bodies(p, stroke)
    bodies["cradle"] = bodies["cradle"] + label_tag(p, stroke)
    return pose_bodies(p, stroke, bodies, pose)


def label_name(stroke: float) -> str:
    return f"{stroke:.1f}".replace(".", "-")


def clamp_x(p: Params, i: int) -> float:
    return (i - (len(p.strokes) - 1) / 2) * p.pitch


def build(params: Params = Params(), pose: Pose | str = Pose.CLOSED) -> dict[str, Part]:
    """Named bodies of all three Clamps, side by side along X."""
    bodies = {}
    for i, stroke in enumerate(params.strokes):
        place = Pos(clamp_x(params, i), 0, 0)
        for name, part in clamp(params, stroke, pose).items():
            bodies[f"{name}-{label_name(stroke)}"] = place * part
    return bodies
