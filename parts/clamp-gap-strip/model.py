"""Clamp gap strip: the Test plate's Battery collar sample at four print-in-place gaps.

Each sample is a Cradle stub with a print-in-place hinged collar Door, shut by a hook-snap
Latch with a thumb tab, labelled with its gap. Every gap in a sample (knuckles, split
faces, Latch, knuckle ends) is that sample's `gap`. It prints closed, axis vertical (Z).
Pick the smallest gap whose hinge turns and whose Latch snaps.

The builders live in `printlab.collar`; the frame is the Test plate's.
"""

from dataclasses import dataclass, replace

from build123d import Part, Pos, Rectangle, Sketch, Text, extrude

from printlab.collar import (
    CollarParams,
    Pose,
    bore,
    bore_cut,
    box,
    cradle_stub,
    door,
    hinge_axis_x,
    outer_radius,
    pose_door,
)

GRAM_BUDGET = 3.0  # g; the CLI warns above this
SEPARATE_STL = {"labels": "label-"}  # the labels print in white PLA, from their own STL


@dataclass(frozen=True)
class Params(CollarParams):
    gaps: tuple[float, ...] = (0.3, 0.4, 0.5, 0.6)  # mm, one sample each
    nominal_bore: float = 8.0  # mm; small, since only the hinge and Latch are under test
    collar_height: float = 5.0  # mm; just above the 4.5 mm Latch, three knuckles still print
    pitch: float = 24.0  # mm between sample centres; a Latch clears the next hinge
    plate_width: float = 4.5  # mm, strip joining the stubs; carries the labels
    plate_height: float = 1.0  # mm; carries no load
    label_size: float = 3.5  # mm font size of the gap labels
    label_depth: float = 0.3  # mm; white PLA labels on the bed, under clear PETG (they don't bond)
    underline: float = 0.5  # mm wide bar joining a label's glyphs into one body
    underline_overlap: float = 0.3  # mm the bar runs up into the glyphs
    label_clearance: float = 0.02  # mm around each label; under a line width, so it doesn't print


def door_name(gap: float) -> str:
    return f"door-{gap:.2f}".replace(".", "-")


def door_gaps(p: Params) -> dict[str, float]:
    """{Door body name: its sample's gap}."""
    return {door_name(g): g for g in p.gaps}


def sample(p: Params, gap: float) -> Params:
    """The Params of one sample: every gap is its own."""
    return replace(p, gap=gap)


def sample_x(p: Params, i: int) -> float:
    return (i - (len(p.gaps) - 1) / 2) * p.pitch


def _strip_y(p: Params) -> tuple[float, float]:
    """(back, front) y of the strip: its front edge inside the ring wall."""
    front = -(bore(p, p.nominal_bore) / 2 + p.wall / 2)
    return front - p.plate_width, front


def label_name(gap: float) -> str:
    return door_name(gap).replace("door-", "label-")


def _outline(p: Params, gap: float, x: float) -> Sketch:
    """The gap, underlined, behind the ring; the underline joins the glyphs into one piece."""
    y = -(outer_radius(p, bore(p, p.nominal_bore)) + p.label_size / 2)
    glyphs = Text(f"{gap:.1f}", p.label_size)
    g = glyphs.bounding_box()
    top = g.min.Y + p.underline_overlap
    bar = Pos((g.min.X + g.max.X) / 2, top - p.underline / 2) * Rectangle(g.size.X, p.underline)
    return Pos(x, y) * (glyphs + bar)


def _label(p: Params, gap: float, x: float) -> Part:
    """White PLA on the bed, read through the PETG above it."""
    return extrude(_outline(p, gap, x), p.label_depth)


def _label_pocket(p: Params, gap: float, x: float) -> Part:
    """The label's room in the strip, about a clearance wider and taller, so the slicer splits it
    off. The label shifted each way, since a 2D offset fails on the font's curves."""
    c = p.label_clearance
    tall = extrude(_outline(p, gap, x), p.label_depth + c)
    pocket = tall
    for dx, dy in ((c, 0), (-c, 0), (0, c), (0, -c), (c, c), (c, -c), (-c, c), (-c, -c)):
        pocket = pocket + Pos(dx, dy, 0) * tall
    return pocket


def _strip(p: Params) -> Part:
    bore_d = bore(p, p.nominal_bore)
    back, front = _strip_y(p)
    last = len(p.gaps) - 1
    x0 = sample_x(p, 0) + hinge_axis_x(sample(p, p.gaps[0]), bore_d)
    x1 = sample_x(p, last) + outer_radius(p, bore_d)
    strip = box(x0, x1, back, front, p.plate_height)
    for i, gap in enumerate(p.gaps):
        x = sample_x(p, i)
        # The strip runs under the Latch between samples: it keeps a gap clear of the Door.
        reach = door(sample(p, gap), bore_d, p.collar_height).bounding_box()
        r_o = outer_radius(p, bore_d)
        strip = strip - box(
            x + r_o, x + reach.max.X + gap, reach.min.Y - gap, front + 1, p.plate_height + 1, -1
        )
        strip = strip + Pos(x, 0, 0) * cradle_stub(sample(p, gap), bore_d, p.collar_height)
        strip = strip - _label_pocket(p, gap, x)
        strip = strip - Pos(x, 0, 0) * bore_cut(bore_d, p.collar_height)
    return strip


def build(params: Params = Params(), pose: Pose | str = Pose.CLOSED) -> dict[str, Part]:
    """Named bodies: the strip of stubs, and one Door per gap, closed or open."""
    bodies = {"strip": _strip(params)}
    bore_d = bore(params, params.nominal_bore)
    for i, gap in enumerate(params.gaps):
        s = sample(params, gap)
        closed = door(s, bore_d, params.collar_height)
        bodies[door_name(gap)] = Pos(sample_x(params, i), 0, 0) * pose_door(s, closed, bore_d, pose)
        bodies[label_name(gap)] = _label(params, gap, sample_x(params, i))
    return bodies
