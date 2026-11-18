import math
from dataclasses import fields

import pytest
from build123d import Pos

from printlab import nudge
from printlab.checks import check_fit, check_part
from printlab.collar import CollarParams
from printlab.export import PETG_DENSITY
from printlab.parts import load_part

model = load_part("clamp-pla-hinge-strip")

# Ticket #17: one sample per PLA clearance; its PLA hinge body (pin and washers) and its Door.
CLEARANCES = {"0-02": 0.02, "0-10": 0.1, "0-20": 0.2}
PETG_GAP = 0.8  # ticket #17: Door to stub in PETG; 0.6 fused


def petg(bodies):
    return {n: b for n, b in bodies.items() if not n.startswith("pla-")}


def test_each_sample_has_one_pla_hinge_body_of_one_solid():
    bodies = model.build()
    hinges = {n for n in bodies if n.startswith("pla-hinge-")}
    assert hinges == {f"pla-hinge-{k}" for k in CLEARANCES}
    for name in hinges:
        report = check_part(bodies[name])
        assert report.ok, (name, report.problems)


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_pla_hinge_stands_its_clearance_from_every_petg_body(pose):
    bodies = model.build(pose=pose)
    for key, c in CLEARANCES.items():
        hinge = bodies[f"pla-hinge-{key}"]
        assert round(hinge.distance_to(bodies["strip"]), 3) == c, key
        assert round(hinge.distance_to(bodies[f"door-{key}"]), 3) == c, key
        nearest = min(hinge.distance_to(b) for b in petg(bodies).values())
        assert round(nearest, 3) == c, key


CAPTURE_SHIFT = 1.0  # mm; ticket #17: a 1 mm move of the PLA body in any axis direction hits the stub


@pytest.mark.parametrize("axis", [(1, 0, 0), (0, 1, 0), (0, 0, 1)], ids="XYZ")
def test_pla_hinge_is_captured_by_the_stub(axis):
    bodies = model.build()
    for key in CLEARANCES:
        hinge = bodies[f"pla-hinge-{key}"]
        for sign in (1, -1):
            moved = Pos(*(sign * CAPTURE_SHIFT * a for a in axis)) * hinge
            assert (moved & bodies["strip"]).solids(), (key, axis, sign)


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_door_turns_about_the_pla_pin(pose):
    bodies = model.build(pose=pose)
    for key, c in CLEARANCES.items():
        door = bodies[f"door-{key}"]
        report = check_fit(bodies[f"pla-hinge-{key}"], door, c)
        assert report.ok, (key, pose, "pla", report.problems)
        report = check_fit(bodies["strip"], door, PETG_GAP)
        assert report.ok, (key, pose, "stub", report.problems)


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_door_stands_petg_gap_from_the_stub(pose):
    bodies = model.build(pose=pose)
    for key in CLEARANCES:
        gap = bodies["strip"].distance_to(bodies[f"door-{key}"])
        assert gap >= PETG_GAP - 1e-4, (key, pose, gap)


HOOK_ENGAGEMENT = 0.5  # mm; the gap strip's hook behind its keeper: keeper_depth 0.8 less gap 0.3


def test_latch_holds_closed_across_the_petg_gap():
    # Pull each Door open (+Y at the Latch) past the PETG gap: its hook must catch the keeper
    # as deep as the gap strip's did, measured across the overlap.
    bodies = model.build()
    for key in CLEARANCES:
        pulled = Pos(0, PETG_GAP + 0.05, 0) * bodies[f"door-{key}"]
        caught = (pulled & bodies["strip"]).solids()
        assert caught, key
        depth = max(s.bounding_box().size.X for s in caught)
        assert depth >= HOOK_ENGAGEMENT - 1e-4, (key, depth)


def test_open_doors_clear_each_other():
    found = {n: b for n, b in model.build(pose="open").items() if n.startswith("door-")}
    names = sorted(found)
    for a, b in zip(names, names[1:]):
        assert not (found[a] & found[b]).solids(), (a, b)


def test_every_body_is_one_valid_solid_that_fits_the_printer():
    for name, body in model.build().items():
        report = check_part(body)
        assert report.ok, (name, report.problems)


OVERHANG = 45.0  # degrees from vertical a face may lean before it needs support
REST = max(CLEARANCES.values()) + 1e-4  # mm; a face this close over another body rests on it


def test_prints_without_supports():
    # Every body stands on the bed or on another body; no face overhangs past 45°.
    limit = -math.sin(math.radians(OVERHANG)) - 1e-3
    bodies = model.build()
    for name, body in bodies.items():
        others = [b for n, b in bodies.items() if n != name]
        bottom = body.bounding_box().min.Z
        assert bottom == pytest.approx(0, abs=1e-6) or any(
            body.distance_to(o) < REST for o in others
        ), name
        for face in body.faces():
            if face.bounding_box().min.Z < 1e-3:
                continue  # on the bed
            normal = face.normal_at(face.center())
            if normal.Z >= limit:
                continue
            assert any(face.distance_to(o) < REST for o in others), (name, face.center(), normal)


def test_pla_bodies_go_to_their_own_stl():
    # ticket #17: every PLA body (pins, washers, labels) in a second STL, marked by `pla-`.
    assert model.SEPARATE_STL == {"pla": "pla-"}
    names = set(model.build())
    assert {n for n in names if n.startswith("pla-label-")} == {f"pla-label-{k}" for k in CLEARANCES}


def test_notes_count_the_layers_that_carry_pla():
    # ticket #17: each PLA layer costs two filament swaps. At 0.1 mm layers: the 0.3 mm labels
    # take layers 1-3; the 0.02 sample's pin runs from 0.6 + 0.02 to 6 - 0.6 - 0.02 mm,
    # layers 7-54. 3 + 48 = 51 layers, 102 swaps.
    assert "PLA in 51 of 60 layers: 102 filament swaps" in model.notes(model.build())


def test_strip_is_within_its_gram_budget():
    assert model.GRAM_BUDGET == 3.0  # ticket #17: warn above 3 g
    volume = sum(body.volume for body in model.build().values())
    assert volume / 1000 * PETG_DENSITY <= model.GRAM_BUDGET


def test_fit_pairs_name_each_door_with_its_stub_and_pla_hinge():
    pairs = set(model.fit_pairs(model.Params()))
    assert pairs == {("strip", f"door-{k}", PETG_GAP) for k in CLEARANCES} | {
        (f"pla-hinge-{k}", f"door-{k}", c) for k, c in CLEARANCES.items()
    }


@pytest.mark.slow
def test_survives_plus_minus_ten_percent():
    # Perturbation audit over this part's own fields (the collar's are the gap strip's).
    own = {f.name for f in fields(model.Params)} - {f.name for f in fields(CollarParams)}
    found = nudge.audit("clamp-pla-hinge-strip", "fit_pairs", ("closed", "open"), only=own)
    assert {f for f, _ in found} == own & set(nudge.numeric_fields(model.Params))
    broken = {job: p for job, p in found.items() if p}
    assert not broken, broken
