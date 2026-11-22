"""Read a sliced plate's G-code as its extruding moves, with the layer and feature each belongs to."""

import re
from collections.abc import Iterator
from dataclasses import dataclass

CHANGE_LAYER = "; CHANGE_LAYER"
FEATURE = "; FEATURE: "
LINE_WIDTH = "; LINE_WIDTH: "
MOVE = re.compile(r"^G([0-3]) ")
WORD = re.compile(r"([XYZEIJ])(-?[\d.]+)")


@dataclass(frozen=True)
class Extrusion:
    """One extruding move, in bed coordinates."""

    layer: int  # 1 is on the bed; 0 is before the first layer change
    feature: str  # the slicer's feature marker, such as "Outer wall", "Brim" or "Support"
    width: float  # line width, mm
    start: tuple[float, float]
    end: tuple[float, float]
    z: float
    kind: str  # "0" or "1" for a line, "2" for a clockwise arc, "3" for an anticlockwise one
    centre: tuple[float, float]  # an arc's I and J, from start; (0, 0) for a line


def extrusions(gcode: str) -> Iterator[Extrusion]:
    layer, feature, width = 0, "", 0.0
    x = y = z = 0.0
    for line in gcode.splitlines():
        if line.startswith(CHANGE_LAYER):
            layer += 1
        elif line.startswith(FEATURE):
            feature = line.removeprefix(FEATURE).strip()
        elif line.startswith(LINE_WIDTH):
            width = float(line.removeprefix(LINE_WIDTH))
        elif move := MOVE.match(line):
            words = {k: float(v) for k, v in WORD.findall(line.split(";")[0])}
            end, z = (words.get("X", x), words.get("Y", y)), words.get("Z", z)
            if words.get("E", 0) > 0:
                centre = (words.get("I", 0.0), words.get("J", 0.0))
                yield Extrusion(layer, feature, width, (x, y), end, z, move[1], centre)
            x, y = end
