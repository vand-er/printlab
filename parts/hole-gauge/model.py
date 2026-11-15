"""Hole gauge: a plate of through-holes from 3.0 to 4.8 mm in 0.2 mm steps.

Print it and measure each hole (or test-fit an M3 screw, an M3 heat-set insert,
a 3 mm pin). FDM holes print undersize; the measured offset becomes the hole
compensation for every later part. The notched corner marks the 3.0 mm end.
"""

from dataclasses import dataclass

from build123d import Box, Cylinder, Part, Pos


@dataclass(frozen=True)
class Params:
    smallest: float = 3.0  # mm, first hole diameter
    step: float = 0.2  # mm between successive holes
    count: int = 10
    pitch: float = 7.0  # mm, centre-to-centre spacing
    margin: float = 5.0  # mm, plate edge to nearest hole edge
    thickness: float = 4.0  # mm, enough depth to feel a screw bite
    notch: float = 3.0  # mm, corner cut marking the smallest hole


def build(p: Params = Params()) -> Part:
    largest = p.smallest + (p.count - 1) * p.step
    length = (p.count - 1) * p.pitch + largest + 2 * p.margin
    width = largest + 2 * p.margin

    plate = Box(length, width, p.thickness)
    first_x = -length / 2 + p.margin + largest / 2
    for i in range(p.count):
        diameter = p.smallest + i * p.step
        plate -= Pos(first_x + i * p.pitch, 0, 0) * Cylinder(diameter / 2, p.thickness)

    corner = Pos(-length / 2, width / 2, 0) * Box(p.notch * 2, p.notch * 2, p.thickness)
    return plate - corner
