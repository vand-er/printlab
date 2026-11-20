"""Pin hole outlines shared by the collars, the Pin strip and the Clamp: a roofed hole and its
lead-in. Each builder reads its angles from the part's `Params` (a `CollarParams`)."""

import math

from build123d import CenterArc, Face, Line, Part, Pos, Wire, loft

# Pure modelling tolerances, not part sizes.
FUSE = 0.01  # mm two solids overlap so they fuse into one, or a cut starts outside its face
THROUGH = 1.0  # mm a through cut runs past each face it opens, so it leaves no skin


def teardrop(p, r: float) -> Face:
    """A circle of radius r in the XY plane, centred on the origin, with a pointed roof on +Y."""
    roof = p.pin_roof_angle
    a = math.radians(roof)
    left, right = (-r * math.sin(a), r * math.cos(a)), (r * math.sin(a), r * math.cos(a))
    apex = (0, roof_height(p, r))
    arc = CenterArc((0, 0), r, 90 + roof, 360 - 2 * roof)
    return Face(Wire([arc, Line(right, apex), Line(apex, left)]))


def roof_height(p, r: float) -> float:
    """How far a roofed hole's apex stands above its centre."""
    return r / math.cos(math.radians(p.pin_roof_angle))


def lead_in(p, r: float, roofed: bool = False, drop: float = 0.0) -> Part:
    """The cut that widens a Pin hole of radius r by `pin_lead_in` at its mouth, at
    `pin_lead_in_angle` from the hole's axis, in a frame whose +Z points into the hole with the
    mouth at z = 0. On a mouth face falling `drop` mm per mm outward (a knuckle's spike top)
    it runs deeper, so that face still opens `pin_lead_in` wide, and starts further out, so the
    ridges between a faceted spike's faces, proud of the mouth, open too."""
    slope = math.tan(math.radians(p.pin_lead_in_angle))  # mm wider per mm out of the hole
    depth = p.pin_lead_in * (1 / slope + drop)
    outside = FUSE + p.pin_lead_in * drop
    wide = r + (depth + outside) * slope

    def outline(radius: float) -> Face:
        return teardrop(p, radius) if roofed else Face(Wire.make_circle(radius))

    return loft([Pos(0, 0, -outside) * outline(wide), Pos(0, 0, depth) * outline(r)])
