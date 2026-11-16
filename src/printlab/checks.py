"""Deterministic geometry checks every part must pass before it is exported."""

from dataclasses import dataclass, field

from build123d import GeomType, Part, Pos

# Bambu Lab X1C build volume in mm (X, Y, Z). Bambu Studio caps Z at about 250.
X1C_BUILD_VOLUME = (256.0, 256.0, 250.0)

# Numerical slack in mm, so a gap modelled exactly at its clearance passes.
FIT_TOLERANCE = 1e-6

# How far past its clearance a fit may be loose, in mm, before it rattles.
RATTLE_DELTA = 0.05


@dataclass
class Report:
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def check_part(part: Part) -> Report:
    """Check the part as modelled: one valid solid that fits the X1C."""
    report = Report()

    solids = part.solids()
    if len(solids) != 1:
        report.problems.append(f"expected exactly 1 solid, found {len(solids)}")
    if not part.is_valid:
        report.problems.append("geometry is not a valid solid (BRep check failed)")

    size = part.bounding_box().size
    for axis, extent, limit in zip("XYZ", (size.X, size.Y, size.Z), X1C_BUILD_VOLUME):
        if extent > limit:
            report.problems.append(
                f"{axis} extent {extent:.1f} mm exceeds X1C build volume ({limit:.0f} mm)"
            )

    return report


def check_fit(a: Part, b: Part, clearance: float) -> Report:
    """Check how two parts meet, as modelled: no overlap, a gap of at least
    `clearance`, and no rattle (b shifted toward a by clearance + RATTLE_DELTA
    must collide)."""
    report = Report()

    overlap_volume = sum(s.volume for s in (a & b).solids())
    if overlap_volume > 0:
        report.problems.append(f"parts overlap by {overlap_volume:.3f} mm³")
        return report

    gap, point_a, point_b = a.distance_to_with_closest_points(b)
    if gap < clearance - FIT_TOLERANCE:
        report.problems.append(f"gap {gap:.3f} mm is under the {clearance:.3f} mm clearance")
        return report

    # Rattle test: shift b by clearance + delta toward a; a snug fit must collide.
    toward_a = (point_a - point_b).normalized()
    shifted = Pos(toward_a * (clearance + RATTLE_DELTA)) * b
    if not (a & shifted).solids():
        report.problems.append(
            f"rattle: gap {gap:.3f} mm is looser than the {clearance:.3f} mm clearance"
            f" + {RATTLE_DELTA} mm"
        )

    return report


def hole_diameters(part: Part, decimals: int = 3) -> list[float]:
    """Distinct diameters of the round holes in a part, smallest first."""
    holes = {
        round(2 * face.radius, decimals)
        for face in part.faces().filter_by(GeomType.CYLINDER)
        if face.is_circular_concave
    }
    return sorted(holes)
