"""Clamp test plate: Battery and Cart collar samples at three bores each.

Each Battery sample is a short Cradle stub with a collar Door hinged on a Pin (ADR 0003),
shut by a hook-snap Latch with a thumb tab, and labelled with its nominal bore. The Pin
presses into the stub's two knuckles and turns in the Door's. Battery axis vertical (Z);
the `print` pose lays each Door beside its stub, without Pins. Pick the bore that grips
the Battery.

Each Cart sample is a Cart collar: a sliding body (the stub's half ring, hinge and keeper,
plus a carriage) and a Door, gripping the brass base by friction. The carriage slides
`slide` up a T-headed rib on the plate, which stops it turning; the carriage roof
landing on the rib's top is the upper stop. A lip on top registers on the Cart's ledge.
It prints at the bottom of its slide. Pick the bore that grips the brass.

Sample frame (closed pose): bore centred on the Z axis, Door on +Y, Cradle stub on
-Y, hinge on -X, Latch on +X. The Door opens anticlockwise (seen from above) about
the hinge axis. Cart samples use the same frame, turned 180° so the carriage faces
the plate.

The hinge, Latch and collar builders and their sizes (`CollarParams`) live in
`printlab.collar`, shared with the Lever strip and the Clamp.
"""

from dataclasses import dataclass

from build123d import Part, Pos, Rot, Text, extrude

from printlab.checks import FitPair
from printlab.collar import (
    CollarParams,
    Hinge,
    Pose,
    Slide,
    bore,
    bore_cut,
    box,
    carriage_back_y,
    cart_body,
    cart_collar_height,
    cart_door,
    cart_rib,
    cradle_stub,
    door,
    door_print_offset,
    hinge_axis_x,
    knuckle_radius,  # noqa: F401  for the tests
    latch_arm,
    outer_radius,
    pin,
    pose_door,
    slide_z,
)

GRAM_BUDGET = 8.0  # g; the CLI warns above this


@dataclass(frozen=True)
class Params(CollarParams):
    hinge: Hinge = Hinge.PIN  # ADR 0003: every print-in-place knuckle fused in PETG
    # Samples
    nominal_bores: tuple[float, ...] = (12.6, 12.8, 13.0)  # mm, labelled sizes
    cart_nominal_bores: tuple[float, ...] = (12.0, 12.2, 12.4)  # mm, labelled sizes
    pitch: float = 32.0  # mm between sample centres; room for an open Door
    print_gap: float = 3.0  # mm clear between each Door and its stub's knuckles on the bed
    collar_height: float = 9.0  # mm, Battery sample; below the 12 mm collar to save filament
    # Plate
    plate_width: float = 3.5  # mm, strip joining the stubs and ribs
    plate_height: float = 1.0  # mm; carries no load
    label_size: float = 3.5  # mm font size of the bore labels
    label_relief: float = 0.4  # mm the labels stand up from the plate


def label_name(nominal: float) -> str:
    return f"{nominal:.1f}".replace(".", "-")


def fit_pairs(p: Params, pose: Pose | str) -> tuple[FitPair, ...]:
    """The bodies that move against each other, the same in every `pose` (a `print` pose has
    no Pins, so their pairs are skipped there), for the nudge audit. Each Pin turns in its
    Door at the Pin clearance; it is a press fit in its stub, and the Pin, not a gap, locates
    the Door on the stub, so those only mustn't overlap (None). Each Cart collar body slides
    on the plate at the gap. Names follow the bores, so a nudge renames them."""
    clearance = (p.pin_clearance_hole - p.pin_stock_diameter) / 2
    battery = [label_name(n) for n in p.nominal_bores]
    carts = [label_name(n) for n in p.cart_nominal_bores]
    hinges = [("plate", f"door-{b}", f"pin-{b}") for b in battery] + [
        (f"cart-body-{c}", f"cart-door-{c}", f"pin-cart-{c}") for c in carts
    ]
    pairs = []
    for stub, door_name, pin_name in hinges:
        pairs += [(pin_name, door_name, clearance), (stub, pin_name, None), (stub, door_name, None)]
    pairs += [("plate", f"cart-body-{c}") for c in carts]
    pairs += [("plate", f"cart-door-{c}", None) for c in carts]
    return tuple(pairs)


def sample_x(p: Params, i: int) -> float:
    return (i - (len(p.nominal_bores) - 1) / 2) * p.pitch


def _plate_y(p: Params) -> tuple[float, float]:
    """(back, front) y of the plate: its front edge lies inside the thinnest Battery ring's wall."""
    front = -(min(bore(p, n) for n in p.nominal_bores) / 2 + p.wall / 2)
    return front - p.plate_width, front


def cart_centre(p: Params, i: int) -> tuple[float, float]:
    """(x, y) of Cart sample i's bore: between the Battery samples, behind the plate."""
    back, _ = _plate_y(p)
    bore_d = bore(p, p.cart_nominal_bores[i])
    return sample_x(p, i) + p.pitch / 2, back + carriage_back_y(p, bore_d) - p.rib_reach


def _cart_place(p: Params, i: int):
    x, y = cart_centre(p, i)
    return Pos(x, y, 0) * Rot(0, 0, 180)


def _label(p: Params, nominal: float, x: float) -> Part:
    back, front = _plate_y(p)
    text = Text(f"{nominal:.1f}", p.label_size)
    return Pos(x, (back + front) / 2, p.plate_height) * extrude(text, p.label_relief)


def _plate(p: Params) -> Part:
    bores = [bore(p, n) for n in p.nominal_bores]
    back, front = _plate_y(p)
    x0 = sample_x(p, 0) + hinge_axis_x(p, bores[0])
    last_label = _label(p, p.cart_nominal_bores[-1], cart_centre(p, len(p.cart_nominal_bores) - 1)[0])
    x1 = max(
        sample_x(p, len(bores) - 1) + outer_radius(p, bores[-1]),
        cart_centre(p, len(p.cart_nominal_bores) - 1)[0] + p.rib_head_width / 2,
        last_label.bounding_box().max.X,  # the label stands on the plate, not over its end
    )
    plate = box(x0, x1, back, front, p.plate_height)
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


def _print_offset(p: Params, closed: Part) -> Pos:
    """Where the `print` pose lays a Door: `print_gap` clear of its stub's knuckles."""
    return door_print_offset(p, closed, p.print_gap)


def _posed(p: Params, closed: Part, bore_d: float, pose: Pose | str) -> Part:
    """A Door in the sample frame: laid beside its stub to print, else closed or open on its Pin."""
    if Pose(pose) == Pose.PRINT:
        return _print_offset(p, closed) * closed
    return pose_door(p, closed, bore_d, pose)


def build(
    params: Params = Params(),
    pose: Pose | str = Pose.PRINT,
    slide: Slide | str | float = Slide.BOTTOM,
) -> dict[str, Part]:
    """Named bodies. `pose` lays every Door out to print, or closes or opens it on its Pin
    (a `pin-…` body); `slide` places every Cart collar."""
    assembled = Pose(pose) != Pose.PRINT
    bodies = {"plate": _plate(params)}
    for i, nominal in enumerate(params.nominal_bores):
        bore_d = bore(params, nominal)
        closed = door(params, bore_d, params.collar_height)
        place = Pos(sample_x(params, i), 0, 0)
        bodies[f"door-{label_name(nominal)}"] = place * _posed(params, closed, bore_d, pose)
        if assembled:
            bodies[f"pin-{label_name(nominal)}"] = place * pin(params, bore_d, params.collar_height)
    height = cart_collar_height(params)
    lift = Pos(0, 0, slide_z(params, slide))
    for i, nominal in enumerate(params.cart_nominal_bores):
        bore_d = bore(params, nominal)
        place = lift * _cart_place(params, i)
        name = label_name(nominal)
        bodies[f"cart-body-{name}"] = place * cart_body(params, bore_d, height)
        closed = cart_door(params, bore_d, height)
        bodies[f"cart-door-{name}"] = place * _posed(params, closed, bore_d, pose)
        if assembled:
            bodies[f"pin-cart-{name}"] = place * pin(params, bore_d, height)
    return bodies


def cart_latch_arms(params: Params = Params()) -> list[Part]:
    """Each Cart sample's Latch arm, placed as printed (bottom of the slide)."""
    height = cart_collar_height(params)
    arms = []
    for i, n in enumerate(params.cart_nominal_bores):
        bore_d = bore(params, n)
        offset = _print_offset(params, cart_door(params, bore_d, height))
        arms.append(_cart_place(params, i) * offset * latch_arm(params, bore_d))
    return arms


def latch_arms(params: Params = Params()) -> list[Part]:
    """Each sample's Latch arm, placed as printed."""
    arms = []
    for i, n in enumerate(params.nominal_bores):
        bore_d = bore(params, n)
        offset = _print_offset(params, door(params, bore_d, params.collar_height))
        arms.append(Pos(sample_x(params, i), 0, 0) * offset * latch_arm(params, bore_d))
    return arms
