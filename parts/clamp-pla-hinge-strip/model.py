"""Clamp PLA hinge strip: the gap strip's Battery collar samples with PLA hinge pins.

Clear PETG fused every PETG-to-PETG hinge on the gap strip, so here PLA, which doesn't bond
to PETG, keeps the hinge apart: each hinge's pin is a PLA body, captured in the stub's knuckles,
with flat PLA washers between the knuckles. Each sample stands its PLA a different
`pla_clearance` off the PETG; Door and stub stay `petg_gap` apart everywhere else. Print PETG
with the `pla-` bodies (hinges and labels) in white PLA, from the second STL.

The builders live in `printlab.collar` and `printlab.strip`; the frame is the Test plate's.
"""

from dataclasses import dataclass, replace

from build123d import Part, Pos

from printlab.checks import RATTLE_DELTA
from printlab.collar import PlaPin, Pose, bore, door, pla_hinge, pose_door
from printlab.strip import StripParams, label, sample_x, strip

GRAM_BUDGET = 3.0  # g; the CLI warns above this
SEPARATE_STL = {"pla": "pla-"}  # hinges and labels print in white PLA, from their own STL


@dataclass(frozen=True)
class Params(StripParams):
    pla_clearances: tuple[float, ...] = (0.02, 0.1, 0.2)  # mm, one sample each; 0.02 still splits
    petg_gap: float = 0.8  # mm, Door to stub in PETG; 0.6 fused in clear PETG
    pin_cap: float = 0.6  # mm of PETG under and over each pin; only closes it in, carries no load
    collar_height: float = 6.0  # mm; three knuckles and two washers above the 4.5 mm Latch
    keeper_depth: float = 1.3  # mm; petg_gap plus the gap strip's 0.5 mm hook engagement
    layer_height: float = 0.1  # mm, the user's everclear preset


def key(c: float) -> str:
    return f"{c:.2f}".replace(".", "-")


def sample(p: Params, c: float) -> Params:
    """The Params of one sample: PETG gaps at `petg_gap`, its PLA at clearance c."""
    return replace(p, gap=p.petg_gap, pla_pin=PlaPin(clearance=c, cap=p.pin_cap))


def fit_pairs(p: Params) -> list[tuple[str, str, float]]:
    """(body, Door, clearance) for each Door: on the stub at `petg_gap`, on its PLA hinge at its
    clearance."""
    return [pair for c in p.pla_clearances for pair in (
        ("strip", f"door-{key(c)}", p.petg_gap), (f"pla-hinge-{key(c)}", f"door-{key(c)}", c)
    )]


def _text(c: float) -> str:
    return f"{c:.2f}"


def notes(bodies: dict[str, Part], params: Params = Params()) -> list[str]:
    """How many layers carry PLA: each costs two filament swaps. A layer carries a body when its
    mid-height lies within the body's height; every PLA body runs unbroken up its height."""
    lh = params.layer_height
    spans = [(b.bounding_box().min.Z, b.bounding_box().max.Z) for n, b in bodies.items()
             if n.startswith(SEPARATE_STL["pla"])]
    total = round(max(b.bounding_box().max.Z for b in bodies.values()) / lh)
    pla = sum(any(lo < (i + 0.5) * lh < hi for lo, hi in spans) for i in range(total))
    # The Latch: each Door pulled open (+Y at the Latch) past the PETG gap; how deep its hook
    # stands behind the keeper.
    pull = Pos(0, params.petg_gap + RATTLE_DELTA, 0)
    hold = min(
        max((s.bounding_box().size.X for s in (pull * b & bodies["strip"]).solids()), default=0.0)
        for n, b in bodies.items() if n.startswith("door-")
    )
    return [
        f"PLA in {pla} of {total} layers: {2 * pla} filament swaps",
        f"Latch hook holds {hold:.2f} mm behind the keeper past the {params.petg_gap:g} mm PETG gap"
        f" (keeper_depth {params.keeper_depth:g} mm)",
    ]


def build(params: Params = Params(), pose: Pose | str = Pose.CLOSED) -> dict[str, Part]:
    """Named bodies: the strip of stubs, and per sample a Door (closed or open), a PLA hinge
    and a PLA label."""
    cs = params.pla_clearances
    samples = [sample(params, c) for c in cs]
    bodies = {"strip": strip(params, samples, [_text(c) for c in cs])}
    bore_d = bore(params, params.nominal_bore)
    h = params.collar_height
    for i, (c, s) in enumerate(zip(cs, samples)):
        x = sample_x(params, i, len(cs))
        bodies[f"door-{key(c)}"] = Pos(x, 0, 0) * pose_door(s, door(s, bore_d, h), bore_d, pose)
        bodies[f"pla-hinge-{key(c)}"] = Pos(x, 0, 0) * pla_hinge(s, bore_d, h)
        bodies[f"pla-label-{key(c)}"] = label(params, _text(c), x)
    return bodies
