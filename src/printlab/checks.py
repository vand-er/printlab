"""Deterministic geometry checks every part must pass before it is exported."""

from dataclasses import dataclass, field

from build123d import GeomType, Part

# Bambu Lab X1C build volume in mm (X, Y, Z). Bambu Studio caps Z at about 250.
X1C_BUILD_VOLUME = (256.0, 256.0, 250.0)


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


def hole_diameters(part: Part, decimals: int = 3) -> list[float]:
    """Distinct diameters of the round holes in a part, smallest first."""
    holes = {
        round(2 * face.radius, decimals)
        for face in part.faces().filter_by(GeomType.CYLINDER)
        if face.is_circular_concave
    }
    return sorted(holes)
