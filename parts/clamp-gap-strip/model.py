"""Clamp gap strip: the Test plate's Battery collar sample at four print-in-place gaps.

Each sample is a Cradle stub with a print-in-place hinged collar Door, shut by a hook-snap
Latch with a thumb tab, labelled with its gap. Every gap in a sample (knuckles, split
faces, Latch, knuckle ends) is that sample's `gap`. It prints closed, axis vertical (Z).
Pick the smallest gap whose hinge turns and whose Latch snaps.

The builders live in `printlab.collar` and `printlab.strip`; the frame is the Test plate's.
"""

from dataclasses import dataclass, replace

from build123d import Part, Pos

from printlab.collar import Pose, bore, door, pose_door
from printlab.strip import StripParams, label, sample_x, strip

GRAM_BUDGET = 3.0  # g; the CLI warns above this
SEPARATE_STL = {"labels": "label-"}  # the labels print in white PLA, from their own STL


@dataclass(frozen=True)
class Params(StripParams):
    gaps: tuple[float, ...] = (0.3, 0.4, 0.5, 0.6)  # mm, one sample each


def door_name(gap: float) -> str:
    return f"door-{gap:.2f}".replace(".", "-")


def door_gaps(p: Params) -> dict[str, float]:
    """{Door body name: its sample's gap}."""
    return {door_name(g): g for g in p.gaps}


def sample(p: Params, gap: float) -> Params:
    """The Params of one sample: every gap is its own."""
    return replace(p, gap=gap)


def label_name(gap: float) -> str:
    return door_name(gap).replace("door-", "label-")


def _text(gap: float) -> str:
    return f"{gap:.1f}"


def build(params: Params = Params(), pose: Pose | str = Pose.CLOSED) -> dict[str, Part]:
    """Named bodies: the strip of stubs, and one Door per gap, closed or open."""
    samples = [sample(params, g) for g in params.gaps]
    bodies = {"strip": strip(params, samples, [_text(g) for g in params.gaps])}
    bore_d = bore(params, params.nominal_bore)
    n = len(params.gaps)
    for i, (gap, s) in enumerate(zip(params.gaps, samples)):
        x = sample_x(params, i, n)
        closed = door(s, bore_d, params.collar_height)
        bodies[door_name(gap)] = Pos(x, 0, 0) * pose_door(s, closed, bore_d, pose)
        bodies[label_name(gap)] = label(params, _text(gap), x)
    return bodies
