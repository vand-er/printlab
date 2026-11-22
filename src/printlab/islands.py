"""First-layer islands: the separate regions the slicer extrudes in each of the first layers, brim included.

Each layer's extruded paths are rasterised at their line width onto a grid; connected regions become
islands, and a brim joins the island it surrounds. An island is named by the body whose bed footprint
(its outline seen from above) contains the island's centroid, else by the nearest one.
"""

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from build123d import Part
from scipy import ndimage

FIRST_LAYERS = 3  # how many layers from the bed up are reported
GRID_MM = 0.05  # pitch of the grid the paths are rasterised onto
ARC_STEP_MM = 0.2  # arcs are followed in chords this long
FOOTPRINT_TOLERANCE_MM = 0.05  # tessellation tolerance of a body's footprint
SLIVER_MM2 = 1e-9  # triangles seen edge-on from above, left out of a footprint

# The sliced config's first-layer settings; a plate's own bed temperature key, by plate type.
FIRST_LAYER_KEYS = (
    "initial_layer_print_height", "initial_layer_line_width", "initial_layer_infill_line_width",
    "initial_layer_speed", "initial_layer_infill_speed", "curr_bed_type", "nozzle_temperature_initial_layer",
)  # fmt: skip
BED_TEMP_KEYS = {
    "Cool Plate": "cool_plate_temp_initial_layer", "Engineering Plate": "eng_plate_temp_initial_layer",
    "High Temp Plate": "hot_plate_temp_initial_layer",
    "Textured PEI Plate": "textured_plate_temp_initial_layer",
    "Supertack Plate": "supertack_plate_temp_initial_layer",
}  # fmt: skip

CHANGE_LAYER = "; CHANGE_LAYER"
FEATURE = "; FEATURE: "
LINE_WIDTH = "; LINE_WIDTH: "
SKIPPED = ("Custom",)  # start, end and timelapse G-code, not part of any island
BRIM = "Brim"
MOVE = re.compile(r"^G([0-3]) ")
WORD = re.compile(r"([XYZEIJ])(-?[\d.]+)")


@dataclass(frozen=True)
class Island:
    """One separate extruded region of a first layer, in the part's own x and y."""

    layer: int  # 1 is on the bed
    area: float  # mm²
    centroid: tuple[float, float]
    body: str


@dataclass(frozen=True)
class Footprint:
    """A body's outline seen from above, as triangles in the part's own x and y."""

    triangles: np.ndarray  # (n, 3, 2)
    bottom: float  # lowest z, so a body on the bed wins over one above it

    def distance(self, point: tuple[float, float]) -> float:
        """0 inside the outline, else how far outside it."""
        p = np.asarray(point)
        a, b, c = (self.triangles[:, i] for i in range(3))
        inside = (_cross(a, b, p) >= 0) == (_cross(b, c, p) >= 0)
        inside &= (_cross(b, c, p) >= 0) == (_cross(c, a, p) >= 0)
        if inside.any():
            return 0.0
        return float(min(_segment_distance(p, u, v).min() for u, v in ((a, b), (b, c), (c, a))))


def footprint(body: Part) -> Footprint:
    vertices, faces = body.tessellate(tolerance=FOOTPRINT_TOLERANCE_MM)
    points = np.array([(v.X, v.Y) for v in vertices])
    triangles = points[np.array(faces)]
    area = _cross(triangles[:, 0], triangles[:, 1], triangles[:, 2])
    return Footprint(triangles[np.abs(area) > SLIVER_MM2], body.bounding_box().min.Z)


def first_layer_settings(config: Mapping) -> dict[str, str | tuple[str, ...]]:
    """The first-layer settings of a sliced config, by key; an unknown plate keeps every plate's bed key."""
    plate = config.get("curr_bed_type")
    beds = [BED_TEMP_KEYS[plate]] if plate in BED_TEMP_KEYS else list(BED_TEMP_KEYS.values())
    return {
        key: tuple(config[key]) if isinstance(config[key], list) else config[key]
        for key in (*FIRST_LAYER_KEYS, *beds)
        if key in config
    }


def first_layer_islands(
    gcode: str, offset: tuple[float, float], footprints: Mapping[str, Footprint]
) -> tuple[Island, ...]:
    """Islands of the first `FIRST_LAYERS` layers; `offset` takes a bed position to the part's own."""
    found = []
    for layer, paths in enumerate(_layer_paths(gcode, FIRST_LAYERS), 1):
        for area, (x, y) in _regions(paths):
            centroid = (x + offset[0], y + offset[1])
            found.append(Island(layer, area, centroid, _body(centroid, footprints)))
    return tuple(sorted(found, key=lambda i: (i.layer, i.body, -i.area)))


def _layer_paths(gcode: str, layers: int) -> list[list[tuple[float, float, float, float, float, bool]]]:
    """Each layer's extruded segments: x0, y0, x1, y1, line width, and whether it is brim."""
    out: list[list] = []
    x = y = 0.0
    width, feature = 0.0, ""
    for line in gcode.splitlines():
        if line.startswith(CHANGE_LAYER):
            if len(out) == layers:
                break
            out.append([])
        elif line.startswith(FEATURE):
            feature = line.removeprefix(FEATURE).strip()
        elif line.startswith(LINE_WIDTH):
            width = float(line.removeprefix(LINE_WIDTH))
        elif move := MOVE.match(line):
            words = {k: float(v) for k, v in WORD.findall(line.split(";")[0])}
            end = (words.get("X", x), words.get("Y", y))
            if out and words.get("E", 0) > 0 and feature not in SKIPPED:
                points = [(x, y), *_arc((x, y), end, words, move[1])] if move[1] in "23" else [(x, y), end]
                out[-1] += [(*u, *v, width, feature == BRIM) for u, v in zip(points, points[1:]) if u != v]
            x, y = end
    return out


def _arc(start, end, words, kind) -> list[tuple[float, float]]:
    """Points along a G2 (clockwise) or G3 arc from start to end, centred at start + (I, J)."""
    cx, cy = start[0] + words.get("I", 0), start[1] + words.get("J", 0)
    r = math.hypot(start[0] - cx, start[1] - cy)
    a0 = math.atan2(start[1] - cy, start[0] - cx)
    a1 = math.atan2(end[1] - cy, end[0] - cx)
    # An arc that ends where it starts is a full circle.
    sweep = ((a1 - a0) % math.tau or math.tau) if kind == "3" else -((a0 - a1) % math.tau or math.tau)
    steps = max(1, math.ceil(abs(sweep) * r / ARC_STEP_MM))
    points = [(cx + r * math.cos(a0 + sweep * k / steps), cy + r * math.sin(a0 + sweep * k / steps))
              for k in range(1, steps)]  # fmt: skip
    return [*points, end]


def _regions(paths) -> list[tuple[float, tuple[float, float]]]:
    """Area and centroid, on the bed, of each connected region the paths cover."""
    if not paths:
        return []
    segments = np.array([p[:-1] for p in paths])  # x0, y0, x1, y1, width
    reach = segments[:, 4].max()
    low = segments[:, :4].reshape(-1, 2).min(axis=0) - reach
    high = segments[:, :4].reshape(-1, 2).max(axis=0) + reach
    shape = tuple(np.ceil((high - low) / GRID_MM).astype(int) + 1)
    covered = np.zeros(shape, bool)
    brim = np.zeros(shape, bool)
    for (*_, width, is_brim), s in zip(paths, segments):
        cells, hit = _stamp(s[:2] - low, s[2:4] - low, width, shape)
        covered[cells] |= hit
        if is_brim:
            brim[cells] |= hit
    labels, count = ndimage.label(covered)
    # A brim joins every region inside it.
    merged = np.arange(count + 1)
    boxes = ndimage.find_objects(labels)
    for label in np.unique(labels[brim]):
        box = boxes[label - 1]
        inside = ndimage.binary_fill_holes(labels[box] == label)
        for other in np.unique(labels[box][inside]):
            if other:
                merged[merged == merged[other]] = merged[label]
    labels = merged[labels]
    regions = []
    for label in np.unique(labels[labels > 0]):
        ix, iy = np.nonzero(labels == label)
        centroid = (float(ix.mean() * GRID_MM + low[0]), float(iy.mean() * GRID_MM + low[1]))
        regions.append((len(ix) * GRID_MM**2, centroid))
    return regions


def _stamp(u, v, width, shape):
    """The grid cells within half the line width of the segment u to v (grid-relative mm)."""
    r = width / 2
    lo = np.maximum(np.floor((np.minimum(u, v) - r) / GRID_MM).astype(int), 0)
    hi = np.minimum(np.ceil((np.maximum(u, v) + r) / GRID_MM).astype(int) + 1, shape)
    gx, gy = np.meshgrid(np.arange(lo[0], hi[0]) * GRID_MM, np.arange(lo[1], hi[1]) * GRID_MM, indexing="ij")
    grid = np.stack([gx, gy], axis=-1)
    hit = _segment_distance(grid, u, v) <= r
    return (slice(lo[0], hi[0]), slice(lo[1], hi[1])), hit


def _segment_distance(p, u, v):
    """Distance from each point p to the segment u-v (u, v broadcast against p)."""
    d = v - u
    length = (d * d).sum(axis=-1)
    t = np.minimum(np.maximum(((p - u) * d).sum(axis=-1) / np.where(length > 0, length, 1), 0), 1)
    return np.linalg.norm(p - (u + t[..., None] * d), axis=-1)


def _cross(a, b, p):
    """Which side of the line a to b each point p lies on: > 0 to the left."""
    (ax, ay), (bx, by), (px, py) = (np.moveaxis(q, -1, 0) for q in (a, b, p))
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


def _body(point: tuple[float, float], footprints: Mapping[str, Footprint]) -> str:
    """The body whose footprint holds the point, lowest first, else the nearest one."""
    if not footprints:
        return ""
    return min(footprints, key=lambda name: (footprints[name].distance(point), footprints[name].bottom))
