"""Sample strips: Battery collar samples in a row on a PETG strip, each labelled in white PLA.

Shared by the gap strip and the PLA hinge strip. Each sample is a Cradle stub on the strip with
a print-in-place Door; `samples` are the per-sample Params, left to right. The labels are buried
in the strip's bottom, a `label_clearance` clear so the slicer splits them off.
"""

from dataclasses import dataclass

from build123d import Part, Pos, Rectangle, Sketch, Text, extrude

from printlab.collar import CollarParams, bore, bore_cut, box, cradle_stub, door, hinge_axis_x, outer_radius


@dataclass(frozen=True)
class StripParams(CollarParams):
    nominal_bore: float = 8.0  # mm; small, since only the hinge and Latch are under test
    collar_height: float = 5.0  # mm; just above the 4.5 mm Latch, three knuckles still print
    pitch: float = 24.0  # mm between sample centres; a Latch clears the next hinge
    plate_width: float = 4.5  # mm, strip joining the stubs; carries the labels
    plate_height: float = 1.0  # mm; carries no load
    label_size: float = 3.5  # mm font size of the labels
    label_depth: float = 0.3  # mm; white PLA labels on the bed, under clear PETG (they don't bond)
    underline: float = 0.5  # mm wide bar joining a label's glyphs into one body
    underline_overlap: float = 0.3  # mm the bar runs up into the glyphs
    label_clearance: float = 0.02  # mm around each label; under a line width, so it doesn't print


def sample_x(p: StripParams, i: int, count: int) -> float:
    """x of sample i of `count`, centred on the origin."""
    return (i - (count - 1) / 2) * p.pitch


def _strip_y(p: StripParams) -> tuple[float, float]:
    """(back, front) y of the strip: its front edge inside the ring wall."""
    front = -(bore(p, p.nominal_bore) / 2 + p.wall / 2)
    return front - p.plate_width, front


def _outline(p: StripParams, text: str, x: float) -> Sketch:
    """The text, underlined, behind the ring; the underline joins the glyphs into one piece."""
    y = -(outer_radius(p, bore(p, p.nominal_bore)) + p.label_size / 2)
    glyphs = Text(text, p.label_size)
    g = glyphs.bounding_box()
    top = g.min.Y + p.underline_overlap
    bar = Pos((g.min.X + g.max.X) / 2, top - p.underline / 2) * Rectangle(g.size.X, p.underline)
    return Pos(x, y) * (glyphs + bar)


def label(p: StripParams, text: str, x: float) -> Part:
    """White PLA on the bed, read through the PETG above it."""
    return extrude(_outline(p, text, x), p.label_depth)


def _label_pocket(p: StripParams, text: str, x: float) -> Part:
    """The label's room in the strip, about a clearance wider and taller, so the slicer splits it
    off. The label shifted each way, since a 2D offset fails on the font's curves."""
    c = p.label_clearance
    tall = extrude(_outline(p, text, x), p.label_depth + c)
    pocket = tall
    for dx, dy in ((c, 0), (-c, 0), (0, c), (0, -c), (c, c), (c, -c), (-c, c), (-c, -c)):
        pocket = pocket + Pos(dx, dy, 0) * tall
    return pocket


def strip(p: StripParams, samples: list[CollarParams], texts: list[str]) -> Part:
    """The strip of Cradle stubs, one per sample, with a pocket for each sample's label."""
    bore_d = bore(p, p.nominal_bore)
    back, front = _strip_y(p)
    n = len(samples)
    x0 = sample_x(p, 0, n) + hinge_axis_x(samples[0], bore_d)
    x1 = sample_x(p, n - 1, n) + outer_radius(p, bore_d)
    body = box(x0, x1, back, front, p.plate_height)
    for i, (s, text) in enumerate(zip(samples, texts)):
        x = sample_x(p, i, n)
        # The strip runs under the Latch between samples: it keeps a gap clear of the Door.
        reach = door(s, bore_d, p.collar_height).bounding_box()
        r_o = outer_radius(p, bore_d)
        body = body - box(
            x + r_o, x + reach.max.X + s.gap, reach.min.Y - s.gap, front + 1, p.plate_height + 1, -1
        )
        body = body + Pos(x, 0, 0) * cradle_stub(s, bore_d, p.collar_height)
        body = body - _label_pocket(p, text, x)
        body = body - Pos(x, 0, 0) * bore_cut(bore_d, p.collar_height)
    return body
