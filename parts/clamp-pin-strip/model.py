"""Clamp Pin strip: chooses the Pin's press-fit and clearance holes by hand (ADR 0003).

Three rows of three holes, each row its own PETG body: vertical press fit, vertical
clearance, and horizontal press fit (along Y, with a 45° pointed roof so it needs no
support). Every hole is as deep as the Clamp's tallest knuckle stack, runs right through
so a Pin can be pushed back out, and has a 45° lead-in at its mouth: the top of a vertical
hole, the back (+Y) end of a horizontal one. Each hole is labelled with its size in white
PLA, buried in its row's front strip as on the gap strip.

Rows run along X, front to back: vertical, clearance, horizontal. Everything stands on z = 0.
"""

import math
from dataclasses import dataclass

from build123d import (
    Align,
    CenterArc,
    Cylinder,
    Face,
    Line,
    Part,
    Plane,
    Polygon,
    Pos,
    Wire,
    extrude,
    loft,
)

from printlab.collar import box
from printlab.strip import LabelParams, label_at, label_pocket

# g; the CLI warns above this. Ticket #20 hoped for about 1.5 g, but nine holes 12 mm deep in
# 1.2 mm walls come to nearly 2 g.
GRAM_BUDGET = 2.0
SEPARATE_STL = {"labels": "label-"}  # the labels print in white PLA, from their own STL

ROWS = ("vertical", "clearance", "horizontal")
ROOF = 45.0  # degrees from vertical: the horizontal holes' pointed roof
LEAD_IN = 45.0  # degrees: every lead-in chamfer
FUSE = 0.01  # mm two solids overlap so they fuse into one


@dataclass(frozen=True)
class Params(LabelParams):
    vertical_holes: tuple[float, ...] = (1.75, 1.85, 1.95)  # mm, press fit, printed vertical
    clearance_holes: tuple[float, ...] = (2.05, 2.15, 2.25)  # mm, turns freely, printed vertical
    horizontal_holes: tuple[float, ...] = (1.75, 1.85, 1.95)  # mm, press fit, along the bed
    knuckle_stack: float = 12.0  # mm, the Clamp's tallest: the Battery collar hinge
    pitch: float = 7.0  # mm between holes along a row; a label fits between
    row_spacing: float = 2.0  # mm, clear between one row's holes and the next row's strip
    plate_width: float = 3.0  # mm, each row's front strip; carries its labels
    label_size: float = 3.0  # mm font size of the labels


def sizes(p: Params, row: str) -> tuple[float, ...]:
    return getattr(p, f"{row}_holes")


def label_name(row: str, size: float) -> str:
    return f"label-{row}-{size:.2f}".replace(".", "-")


def _text(size: float) -> str:
    return f"{size:.2f}"


def _hole_x(p: Params, i: int, count: int) -> float:
    return (i - (count - 1) / 2) * p.pitch


def _outer_radius(p: Params, size: float) -> float:
    return size / 2 + p.knuckle_wall


def _row_depth(p: Params, row: str) -> float:
    """Along Y, from the strip's front to the back of the row's holes."""
    if row == "horizontal":
        return p.plate_width + p.knuckle_stack
    return p.plate_width + 2 * max(_outer_radius(p, d) for d in sizes(p, row))


def _row_front(p: Params, row: str) -> float:
    y = 0.0
    for r in ROWS[: ROWS.index(row)]:
        y += _row_depth(p, r) + p.row_spacing
    return y


def _teardrop(r: float) -> Face:
    """A circle of radius r in the XY plane, centred on the origin, with a pointed roof on +Y."""
    a = math.radians(ROOF)
    left, right = (-r * math.sin(a), r * math.cos(a)), (r * math.sin(a), r * math.cos(a))
    apex = (0, r / math.cos(a))
    arc = CenterArc((0, 0), r, 90 + ROOF, 360 - 2 * ROOF)
    return Face(Wire([arc, Line(right, apex), Line(apex, left)]))


def _lead_in(r: float, depth: float, roofed: bool) -> Part:
    """The mouth's cut, in a frame whose +Z points into the hole: r + depth at z = 0,
    r at z = depth, 45° between."""
    grow = depth * math.tan(math.radians(LEAD_IN))
    if roofed:
        mouth, inner = _teardrop(r + grow), _teardrop(r)
    else:
        mouth, inner = Face(Wire.make_circle(r + grow)), Face(Wire.make_circle(r))
    return loft([Pos(0, 0, -FUSE) * mouth, Pos(0, 0, depth) * inner])


def _vertical(p: Params, size: float, x: float, y: float) -> Part:
    """A tube on the bed, its hole right through, the lead-in at the top."""
    h = p.knuckle_stack
    up = (Align.CENTER, Align.CENTER, Align.MIN)
    tube = Cylinder(_outer_radius(p, size), h, align=up)
    tube -= Pos(0, 0, -1) * Cylinder(size / 2, h + 2, align=up)
    tube -= Plane.XY.offset(h).rotated((180, 0, 0)) * _lead_in(size / 2, p.pin_lead_in, False)
    return Pos(x, y, 0) * tube


def _horizontal(p: Params, size: float, x: float, y: float) -> Part:
    """A bar along Y from y, a roofed hole right through it, the lead-in at the back."""
    r, w, length = size / 2, p.knuckle_wall, p.knuckle_stack
    width = size + 2 * w
    centre_z = w + r
    # Outside: square sides, then the hole's roof a wall out, so the wall holds all round.
    a = math.radians(ROOF)
    ridge = centre_z + (r + w) / math.cos(a)
    eave = ridge - width / 2 / math.tan(a)
    xz = Plane.XZ  # local x = X, local y = Z, normal -Y
    outline = Polygon((-width / 2, 0), (width / 2, 0), (width / 2, eave), (0, ridge),
                      (-width / 2, eave), align=None)
    bar = extrude(xz * outline, -length)  # along +Y from y = 0
    # x_dir -X, so the teardrop's +Y (its roof) lands on +Z.
    hole_plane = Plane(origin=(0, -1, centre_z), x_dir=(-1, 0, 0), z_dir=(0, 1, 0))
    bar -= extrude(hole_plane * _teardrop(r), length + 2)
    mouth = Plane(origin=(0, length, centre_z), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
    bar -= mouth * _lead_in(r, p.pin_lead_in, True)
    return Pos(x, y, 0) * bar


def _row(p: Params, row: str) -> Part:
    """The row's front strip, carrying its labels, with its holes standing behind it."""
    y0 = _row_front(p, row)
    holes = sizes(p, row)
    n = len(holes)
    half = (n - 1) / 2 * p.pitch + p.pitch / 2
    back = y0 + p.plate_width
    body = box(-half, half, y0, back, p.plate_height)
    for i, size in enumerate(holes):
        x = _hole_x(p, i, n)
        # Each hole stands a wall's half into the strip, so they fuse but the hole stays clear.
        if row == "horizontal":
            body += _horizontal(p, size, x, back - p.knuckle_wall / 2)
        else:
            body += _vertical(p, size, x, back + _outer_radius(p, size) - p.knuckle_wall / 2)
        body -= label_pocket(p, _text(size), x, y0 + p.plate_width / 2)
    return body


def build(params: Params = Params()) -> dict[str, Part]:
    """Named bodies: one PETG body per row, and one white PLA label per hole."""
    bodies = {}
    for row in ROWS:
        bodies[row] = _row(params, row)
        holes = sizes(params, row)
        for i, size in enumerate(holes):
            x = _hole_x(params, i, len(holes))
            bodies[label_name(row, size)] = label_at(
                params, _text(size), x, _row_front(params, row) + params.plate_width / 2
            )
    return bodies
