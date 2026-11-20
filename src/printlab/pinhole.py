"""Pin hole outlines shared by the Pin strip and the Clamp: a roofed hole and its lead-in."""

import math

from build123d import CenterArc, Face, Line, Part, Pos, Wire, loft

ROOF = 45.0  # degrees from vertical: a horizontal hole's pointed roof
LEAD_IN = 45.0  # degrees: every lead-in chamfer
FUSE = 0.01  # mm a cut starts outside the face it opens, so it leaves no skin


def teardrop(r: float) -> Face:
    """A circle of radius r in the XY plane, centred on the origin, with a pointed roof on +Y."""
    a = math.radians(ROOF)
    left, right = (-r * math.sin(a), r * math.cos(a)), (r * math.sin(a), r * math.cos(a))
    apex = (0, r / math.cos(a))
    arc = CenterArc((0, 0), r, 90 + ROOF, 360 - 2 * ROOF)
    return Face(Wire([arc, Line(right, apex), Line(apex, left)]))


def roof_height(r: float) -> float:
    """How far a roofed hole's apex stands above its centre."""
    return r / math.cos(math.radians(ROOF))


def lead_in(r: float, depth: float, roofed: bool) -> Part:
    """The mouth's cut, in a frame whose +Z points into the hole: r + depth at z = 0,
    r at z = depth, 45° between."""
    grow = depth * math.tan(math.radians(LEAD_IN))
    if roofed:
        mouth, inner = teardrop(r + grow), teardrop(r)
    else:
        mouth, inner = Face(Wire.make_circle(r + grow)), Face(Wire.make_circle(r))
    return loft([Pos(0, 0, -FUSE) * mouth, Pos(0, 0, depth) * inner])
