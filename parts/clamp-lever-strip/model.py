"""Clamp lever strip: three small Clamps, one per Stroke, to pick the Stroke on the real Cart.

Each Clamp is a Cradle carrying a Battery collar, a sliding Cart collar stacked on it and
an over-centre Lever. The Lever pivots on the back of the Cradle (opposite the fire
button); a Link from its crank pin to a pin on the Cart collar pulls the collar down by
the Stroke as the Lever goes over centre. The stop is the Lever lying flat on the Cradle.
Everything prints closed and in place, Battery axis vertical (Z), Lever locked.

The Clamp builders and frame live in `printlab.clamp`, shared with the full Clamp; this
part adds the strip and a Stroke label on a tag off each Cradle's spine.
"""

from dataclasses import dataclass

from build123d import Part, Pos, Text, extrude

from printlab.clamp import locked_bodies, pose_bodies, spine_y
from printlab.collar import box, carriage_half_width

GRAM_BUDGET = 20.0  # g; the CLI warns above this


@dataclass(frozen=True)
class Params:
    # The strip
    strokes: tuple[float, ...] = (0.3, 0.6, 0.9)  # mm, one Clamp per Stroke
    pitch: float = 30.0  # mm between Clamp centres; room for open Doors
    # Bores: the Test plate's middle sizes until it picks them
    battery_nominal_bore: float = 12.8  # mm, labelled size
    cart_nominal_bore: float = 12.2  # mm, labelled size
    fdm_offset: float = 0.2  # mm added to each bore; FDM holes print undersize
    # Collars (as the Test plate)
    battery_collar_height: float = 12.0  # mm; its Latch runs full height to carry the Cart Latch
    wall: float = 1.3  # mm, collar ring wall (load-bearing)
    gap: float = 0.3  # mm, print-in-place clearance everywhere
    open_angle: float = 90.0  # degrees each Door swings in the open pose
    pin_diameter: float = 2.4  # mm, every pin: hinges and the Lever's three (load-bearing)
    knuckle_wall: float = 1.2  # mm, ring around each pin (load-bearing)
    knuckle_cone: float = 45.0  # degrees from vertical
    knuckle_facets: int = 16
    latch_height: float = 4.5  # mm, Cart collar Latch arm height
    arm_thickness: float = 1.4  # mm, radial; the arm bends in the XY plane
    arm_length: float = 8.0  # mm
    arm_root: float = 2.0  # mm
    catch_depth: float = 0.8  # mm
    catch_ramp: float = 2.5  # mm
    catch_flat: float = 1.0  # mm
    hook_length: float = 1.5  # mm
    hook_land: float = 0.5  # mm
    tab_width: float = 1.5  # mm
    tab_reach: float = 2.5  # mm
    # Cart collar. Cart sizes are estimates; the brass height is a ruler reading.
    brass_height: float = 10.0  # mm, Seat to ledge
    brass_margin: float = 1.0  # mm the collar stops short of the brass height
    glass_diameter: float = 11.9  # mm
    lip_clearance: float = 0.1  # mm per side
    lip_thickness: float = 0.8  # mm; the lip rests on the ledge with the Lever open
    travel: float = 2.0  # mm the collar may slide on its rib; the Stroke uses part of it
    rib_width: float = 2.0  # mm
    rib_head_width: float = 5.0  # mm
    rib_head_depth: float = 1.2  # mm
    rib_reach: float = 1.0  # mm of neck between the spine and the carriage
    carriage_wall: float = 1.2  # mm (load-bearing)
    # Cradle
    spine_depth: float = 2.0  # mm, the spine behind the collars (load-bearing)
    # Lever (over-centre toggle)
    toggle_x: float = 5.2  # mm, x of the Lever's outer face; the Link runs just outside
    pivot_offset: float = 3.4  # mm from the Cradle's back face to the pivot axis
    crank_radius: float = 3.0  # mm, pivot to crank pin
    link_length: float = 13.0  # mm, crank pin to Link pin
    overtravel: float = 8.0  # degrees the crank sits past centre when locked
    centre_drop_cap: float = 0.1  # mm, most the collar may drop past the Stroke at centre
    link_pin_height: float = 2.5  # mm, Link pin above the Cart collar's underside
    lever_width: float = 3.0  # mm, along X
    link_width: float = 2.0  # mm, along X
    lug_width: float = 2.0  # mm, along X: the Cradle lug carrying the pivot pin
    head_width: float = 1.2  # mm, along X: pin heads that keep the Link on
    head_size: float = 2.4  # mm, half-diagonal of each diamond pin head
    # Labels
    label_size: float = 3.5  # mm font size of the Stroke labels
    label_relief: float = 0.4  # mm
    tag_length: float = 10.0  # mm, label tag along X, off the spine's -X side
    tag_depth: float = 5.0  # mm, along Y
    tag_thickness: float = 1.0  # mm


def label_tag(p: Params, stroke: float) -> Part:
    """The tag off the spine's -X side, labelled with the Stroke."""
    _, front = spine_y(p)
    hw = carriage_half_width(p)
    tag = box(-hw - p.tag_length, -hw + 0.5, front - p.tag_depth, front, p.tag_thickness)
    text = Text(f"{stroke:.1f}", p.label_size)
    label = Pos(-hw - p.tag_length / 2, front - p.tag_depth / 2, p.tag_thickness) * extrude(
        text, p.label_relief
    )
    return tag + label


def clamp(p: Params, stroke: float, pose: str = "closed") -> dict[str, Part]:
    """One labelled Clamp's bodies in its own frame, in `pose` (see `pose_bodies`)."""
    bodies = locked_bodies(p, stroke)
    bodies["cradle"] = bodies["cradle"] + label_tag(p, stroke)
    return pose_bodies(p, stroke, bodies, pose)


def label_name(stroke: float) -> str:
    return f"{stroke:.1f}".replace(".", "-")


def clamp_x(p: Params, i: int) -> float:
    return (i - (len(p.strokes) - 1) / 2) * p.pitch


def build(params: Params = Params(), pose: str = "closed") -> dict[str, Part]:
    """Named bodies of all three Clamps, side by side along X."""
    bodies = {}
    for i, stroke in enumerate(params.strokes):
        place = Pos(clamp_x(params, i), 0, 0)
        for name, part in clamp(params, stroke, pose).items():
            bodies[f"{name}-{label_name(stroke)}"] = place * part
    return bodies
