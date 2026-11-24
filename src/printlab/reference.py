"""A part's first layers compared with a reference print's: one that has already printed well.

`compare_first_layers(part, reference)` takes two slice reports and returns one of:
- `Invalid`, when the slices' first-layer settings differ, so the comparison means nothing;
- `Warned`, with one `Smaller` per island below the reference's smallest island in the same layer;
- `Passed`, when every island is at least as large as the reference's smallest in its layer.
A smaller island is a warning, never a blocker: the reference shows what has printed, not a limit.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from printlab.islands import Island
from printlab.slicing import SliceReport


@dataclass(frozen=True)
class Invalid:
    settings: tuple[str, ...]  # the first-layer settings that differ, by key


@dataclass(frozen=True)
class Smaller:
    island: Island
    reference_area: float  # mm², the reference's smallest island in the same layer


@dataclass(frozen=True)
class Warned:
    smaller: tuple[Smaller, ...]  # one per island below the reference's smallest in its layer


@dataclass(frozen=True)
class Passed:
    smallest: Mapping[int, tuple[float, float]]  # by layer: the part's smallest and the reference's, mm²


def compare_first_layers(part: SliceReport, reference: SliceReport) -> Invalid | Warned | Passed:
    settings, reference_settings = part.first_layer, reference.first_layer
    keys = {*settings, *reference_settings}
    if differing := tuple(sorted(k for k in keys if settings.get(k) != reference_settings.get(k))):
        return Invalid(differing)
    floor = _smallest(reference.islands)
    if smaller := tuple(
        Smaller(i, floor[i.layer]) for i in part.islands if i.layer in floor and i.area < floor[i.layer]
    ):
        return Warned(smaller)
    own = _smallest(part.islands)
    return Passed({layer: (own[layer], floor[layer]) for layer in sorted(own) if layer in floor})


def _smallest(islands: tuple[Island, ...]) -> dict[int, float]:
    out: dict[int, float] = {}
    for island in islands:
        out[island.layer] = min(island.area, out.get(island.layer, island.area))
    return out
