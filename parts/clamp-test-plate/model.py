"""Clamp test plate: Battery and Cart collar samples at three bores each.

Each Battery sample is a short Cradle stub with a print-in-place hinged collar Door, shut by
a hook-snap Latch with a thumb tab, and labelled with its nominal bore. It prints
closed, Battery axis vertical (Z). Pick the bore that grips the Battery.

Each Cart sample is a Cart collar: a sliding body (the stub's half ring, hinge and catch,
plus a carriage) and a Door, gripping the brass base by friction. The carriage slides
`travel` up a T-headed rib on the plate, which stops it turning; the carriage roof
landing on the rib's top is the upper stop. A lip on top registers on the Cart's ledge.
It prints at the bottom of its travel. Pick the bore that grips the brass.

Sample frame (closed pose): bore centred on the Z axis, Door on +Y, Cradle stub on
-Y, hinge on -X, Latch on +X. The Door opens anticlockwise (seen from above) about
the hinge axis. Cart samples use the same frame, turned 180° so the carriage faces
the spine.

The hinge, Latch and collar builders live in `printlab.collar`, shared with the Lever
strip and the Clamp.
"""

from dataclasses import dataclass

from build123d import Part, Pos, Rot, Text, extrude

from printlab.collar import (
    bore,
    bore_cut,
    box,
    cart_body,
    cart_collar_height,
    cart_door,
    cart_rib,
    carriage_back_y,
    cradle_stub,
    door,
    hinge_axis_x,
    latch_arm,
    outer_radius,
    pose_door,
    travel_z,
)

GRAM_BUDGET = 8.0  # g; the CLI warns above this


@dataclass(frozen=True)
class Params:
    # Samples
    nominal_bores: tuple[float, ...] = (12.6, 12.8, 13.0)  # mm, labelled sizes
    fdm_offset: float = 0.2  # mm added to each bore; FDM holes print undersize
    pitch: float = 32.0  # mm between sample centres; room for an open Door
    # Collar
    collar_height: float = 9.0  # mm, Battery sample; below the 12 mm collar to save filament
    wall: float = 1.3  # mm, collar ring wall (load-bearing)
    gap: float = 0.3  # mm, print-in-place clearance between Door and stub
    open_angle: float = 90.0  # degrees the Door swings in the open pose
    # Hinge: three knuckles, stub-Door-stub, with an integral pin on the stub
    pin_diameter: float = 2.4  # mm (load-bearing)
    knuckle_wall: float = 1.2  # mm, Door knuckle ring around the pin (load-bearing)
    knuckle_cone: float = 45.0  # degrees from vertical; spiked knuckle ends print unsupported
    knuckle_facets: int = 16  # facets around each knuckle spike
    # Latch: horizontal hook arm on the Door, catch on the stub
    latch_height: float = 4.5  # mm, arm height from the bed
    arm_thickness: float = 1.4  # mm, radial; the arm bends in the XY plane
    arm_length: float = 8.0  # mm, free beam from root to hook; about 2.6 % strain to snap
    arm_root: float = 2.0  # mm, root block joining the arm to the Door
    catch_depth: float = 0.8  # mm the hook engages behind the catch
    catch_ramp: float = 2.5  # mm lead-in ramp the hook rides over
    catch_flat: float = 1.0  # mm flat top of the catch
    hook_length: float = 1.5  # mm along the arm
    hook_land: float = 0.5  # mm flat at the hook's tip; the rest is lead-in chamfer
    tab_width: float = 1.5  # mm thumb tab along the arm
    tab_reach: float = 2.5  # mm the thumb tab stands out from the arm
    # Cart collar samples. Cart sizes are estimates; the brass height is a ruler reading.
    cart_nominal_bores: tuple[float, ...] = (12.0, 12.2, 12.4)  # mm, labelled sizes
    brass_height: float = 10.0  # mm, Seat to ledge
    brass_margin: float = 1.0  # mm the collar stops short of the brass height
    glass_diameter: float = 11.9  # mm, glass tank above the ledge
    lip_clearance: float = 0.1  # mm per side between the lip and the glass
    lip_thickness: float = 0.8  # mm, lip at the collar top, inside the collar height
    travel: float = 2.0  # mm the collar slides on its rib
    rib_width: float = 2.0  # mm, the rib's neck
    rib_head_width: float = 5.0  # mm, the rib's T head inside the carriage
    rib_head_depth: float = 1.2  # mm
    rib_reach: float = 1.0  # mm of neck between the spine and the carriage
    carriage_wall: float = 1.2  # mm, carriage walls and roof (load-bearing)
    # Plate
    spine_width: float = 3.5  # mm, strip joining the stubs and ribs
    spine_height: float = 1.0  # mm; carries no load
    label_size: float = 3.5  # mm font size of the bore labels
    label_relief: float = 0.4  # mm the labels stand up from the spine


def label_name(nominal: float) -> str:
    return f"{nominal:.1f}".replace(".", "-")


def sample_x(p: Params, i: int) -> float:
    return (i - (len(p.nominal_bores) - 1) / 2) * p.pitch


def _spine_y(p: Params) -> tuple[float, float]:
    """(back, front) y of the spine: its front edge lies inside the thinnest Battery ring's wall."""
    front = -(min(bore(p, n) for n in p.nominal_bores) / 2 + p.wall / 2)
    return front - p.spine_width, front


def cart_centre(p: Params, i: int) -> tuple[float, float]:
    """(x, y) of Cart sample i's bore: between the Battery samples, behind the spine."""
    back, _ = _spine_y(p)
    bore_d = bore(p, p.cart_nominal_bores[i])
    return sample_x(p, i) + p.pitch / 2, back + carriage_back_y(p, bore_d) - p.rib_reach


def _cart_place(p: Params, i: int):
    x, y = cart_centre(p, i)
    return Pos(x, y, 0) * Rot(0, 0, 180)


def _label(p: Params, nominal: float, x: float) -> Part:
    back, front = _spine_y(p)
    text = Text(f"{nominal:.1f}", p.label_size)
    return Pos(x, (back + front) / 2, p.spine_height) * extrude(text, p.label_relief)


def _plate(p: Params) -> Part:
    bores = [bore(p, n) for n in p.nominal_bores]
    back, front = _spine_y(p)
    x0 = sample_x(p, 0) + hinge_axis_x(p, bores[0])
    x1 = max(
        sample_x(p, len(bores) - 1) + outer_radius(p, bores[-1]),
        cart_centre(p, len(p.cart_nominal_bores) - 1)[0] + p.rib_head_width / 2,
    )
    plate = box(x0, x1, back, front, p.spine_height)
    for i, (nominal, bore_d) in enumerate(zip(p.nominal_bores, bores)):
        x = sample_x(p, i)
        plate = plate + Pos(x, 0, 0) * cradle_stub(p, bore_d, p.collar_height)
        plate = plate + _label(p, nominal, x)
        plate = plate - Pos(x, 0, 0) * bore_cut(bore_d, p.collar_height)
    height = cart_collar_height(p)
    for i, nominal in enumerate(p.cart_nominal_bores):
        plate = plate + _cart_place(p, i) * cart_rib(p, bore(p, nominal), height)
        plate = plate + _label(p, nominal, cart_centre(p, i)[0])
    return plate


def build(
    params: Params = Params(), pose: str = "closed", travel: str | float = "bottom"
) -> dict[str, Part]:
    """Named bodies. `pose` opens or closes every Door; `travel` places every Cart collar."""
    bodies = {"plate": _plate(params)}
    for i, nominal in enumerate(params.nominal_bores):
        bore_d = bore(params, nominal)
        closed = door(params, bore_d, params.collar_height)
        bodies[f"door-{label_name(nominal)}"] = Pos(sample_x(params, i), 0, 0) * pose_door(
            params, closed, bore_d, pose
        )
    height = cart_collar_height(params)
    lift = Pos(0, 0, travel_z(params, travel))
    for i, nominal in enumerate(params.cart_nominal_bores):
        bore_d = bore(params, nominal)
        place = lift * _cart_place(params, i)
        name = label_name(nominal)
        bodies[f"cart-body-{name}"] = place * cart_body(params, bore_d, height)
        closed = cart_door(params, bore_d, height)
        bodies[f"cart-door-{name}"] = place * pose_door(params, closed, bore_d, pose)
    return bodies


def cart_latch_arms(params: Params = Params()) -> list[Part]:
    """Each Cart sample's Latch arm, placed as printed (closed pose, bottom of travel)."""
    return [
        _cart_place(params, i) * latch_arm(params, bore(params, n))
        for i, n in enumerate(params.cart_nominal_bores)
    ]


def latch_arms(params: Params = Params()) -> list[Part]:
    """Each sample's Latch arm, placed as printed (closed pose)."""
    return [
        Pos(sample_x(params, i), 0, 0) * latch_arm(params, bore(params, n))
        for i, n in enumerate(params.nominal_bores)
    ]
