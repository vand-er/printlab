import math
from dataclasses import fields
from functools import cache

import pytest
from build123d import Align, Cylinder, GeomType, Plane, Pos

from printlab import nudge
from printlab.checks import check_part, hole_diameters
from printlab.clamp import ClampParams
from printlab.collar import CollarParams
from printlab.export import PETG_DENSITY
from printlab.parts import load_part

model = load_part("clamp-pin-strip")

# Ticket #20: three rows of three holes, one PETG body each.
ROWS = {
    "vertical": [1.75, 1.85, 1.95],  # press fit, printed vertical
    "clearance": [2.05, 2.15, 2.25],  # the Pin turns freely, printed vertical
    "horizontal": [1.75, 1.85, 1.95],  # press fit, printed along the bed
}
LEAD_IN = 0.3  # mm, ticket #20


@cache
def bodies():
    return model.build()


def holes(body):
    """{diameter: the hole's round face}, one per hole."""
    return {
        round(2 * f.radius, 3): f
        for f in body.faces().filter_by(GeomType.CYLINDER)
        if f.is_circular_concave
    }


def probe(axis, radius, start, length):
    """A round probe on the hole's axis, from `start` mm along it for `length` mm."""
    plane = Plane(origin=axis.position, z_dir=axis.direction).offset(start)
    return plane * Cylinder(radius, length, align=(Align.CENTER, Align.CENTER, Align.MIN))


def touches(a, b):
    return a.distance_to(b) < 1e-6


@pytest.mark.parametrize("row", ROWS)
def test_each_row_carries_its_three_hole_sizes(row):
    assert hole_diameters(bodies()[row]) == ROWS[row]


def test_holes_are_as_deep_as_the_clamps_tallest_knuckle_stack():
    # The Battery collar is the Clamp's tallest collar, and its hinge's knuckles run full height.
    assert model.Params().knuckle_stack == ClampParams().battery_collar_height


def mouth(row, body, axis):
    """How far along the hole's axis its mouth lies: the top, or the back of a horizontal hole."""
    end = body.bounding_box().max
    point = end.Y if row == "horizontal" else end.Z
    origin = axis.position.Y if row == "horizontal" else axis.position.Z
    sign = axis.direction.Y if row == "horizontal" else axis.direction.Z
    return (point - origin) * sign


@pytest.mark.parametrize("row", ROWS)
def test_each_hole_runs_right_through_one_knuckle_stack(row):
    stack = model.Params().knuckle_stack
    body = bodies()[row]
    for d, face in holes(body).items():
        axis = face.axis_of_rotation
        top = mouth(row, body, axis)
        # Clear right through, so a Pin can be pushed back out.
        assert not touches(body, probe(axis, d / 2 - 0.02, top - stack - 1, stack + 2)), d
        # The round face runs the stack, less the lead-in at its mouth.
        box = face.bounding_box()
        extent = box.size.Y if row == "horizontal" else box.size.Z
        assert extent + LEAD_IN == pytest.approx(stack, abs=1e-3), d


@pytest.mark.parametrize("row", ROWS)
def test_each_hole_has_a_lead_in_at_its_mouth(row):
    body = bodies()[row]
    for d, face in holes(body).items():
        axis = face.axis_of_rotation
        m = mouth(row, body, axis)
        start = m - 0.01 if m > 0 else m  # the first 0.01 mm inside the mouth
        # Just inside the mouth the hole is a lead-in wider; a little wider still is wall.
        assert not touches(body, probe(axis, d / 2 + LEAD_IN - 0.03, start, 0.01)), d
        assert touches(body, probe(axis, d / 2 + LEAD_IN + 0.03, start, 0.01)), d


def test_every_body_is_one_valid_solid_that_fits_the_printer():
    for name, body in bodies().items():
        report = check_part(body)
        assert report.ok, (name, report.problems)


def labels():
    return {name: body for name, body in bodies().items() if name.startswith("label-")}


def test_each_hole_has_a_label_body_for_a_second_filament():
    expected = {
        f"label-{row}-{d:.2f}".replace(".", "-") for row, sizes in ROWS.items() for d in sizes
    }
    assert set(labels()) == expected


LABEL_CLEARANCE = 0.02  # mm; far under a 0.5 mm line, so it doesn't print


def test_labels_are_buried_in_their_rows_bottom():
    # PLA does not bond to PETG: each label sits on the bed under clear PETG, which locks it in.
    for name, label in labels().items():
        strip = bodies()[name.split("-")[1]]
        box = label.bounding_box()
        assert box.min.Z == pytest.approx(0, abs=1e-6), name
        clear = strip.distance_to(label)
        assert LABEL_CLEARANCE / 2 < clear <= LABEL_CLEARANCE + 1e-4, (name, clear)
        raised = Pos(0, 0, box.max.Z + LABEL_CLEARANCE) * label  # its footprint, just above
        assert (raised & strip).volume == pytest.approx(raised.volume, rel=1e-3), name


OVERHANG = 45.0  # degrees from vertical a face may lean before it needs support
SAMPLES = 5  # points per face edge-to-edge where the overhang is read


def test_prints_without_supports():
    limit = -math.sin(math.radians(OVERHANG)) - 1e-3
    found = bodies()
    for name, body in found.items():
        others = [b for n, b in found.items() if n != name]
        assert body.bounding_box().min.Z == pytest.approx(0, abs=1e-6), name
        for face in body.faces():
            if face.bounding_box().min.Z < 1e-3:
                continue  # on the bed
            # Rests on another body (a strip over a label): the label pocket is the label
            # shifted each way, so its corners stand up to clearance·√2 off.
            if any(face.distance_to(o) < LABEL_CLEARANCE * math.sqrt(2) + 1e-4 for o in others):
                continue
            # Read the normal across the face, not only at its centre: a round hole turns.
            for u in range(SAMPLES):
                for v in range(SAMPLES):
                    normal = face.normal_at(u / (SAMPLES - 1), v / (SAMPLES - 1))
                    assert normal.Z >= limit, (name, face.center(), normal)


def test_strip_is_within_its_gram_budget():
    # Ticket #20 hoped for about 1.5 g; 1.2 mm walls round nine 12 mm holes need nearly 2.
    assert model.GRAM_BUDGET == 2.0
    volume = sum(body.volume for body in bodies().values())
    assert volume / 1000 * PETG_DENSITY <= model.GRAM_BUDGET


@pytest.mark.slow
def test_survives_plus_minus_ten_percent():
    # Perturbation audit over this part's own fields, and the collar's that its holes read.
    collar = {f.name for f in fields(CollarParams)}
    audited = {f.name for f in fields(model.Params)} - collar | {"knuckle_wall", "pin_lead_in"}
    found = nudge.audit("clamp-pin-strip", (), ((),), only=audited)
    assert {f for f, _ in found} == audited & set(nudge.numeric_fields(model.Params))
    broken = {job: p for job, p in found.items() if p}
    assert not broken, broken


def test_every_part_reads_the_pins_provisional_sizes():
    # Ticket #20: the middle sizes, until the Pin strip is printed and judged.
    p = CollarParams()
    assert p.pin_stock_diameter == 1.75  # a PETG filament offcut
    assert p.pin_press_hole_vertical == 1.85
    assert p.pin_press_hole_horizontal == 1.85
    assert p.pin_clearance_hole == 2.15
    assert p.pin_lead_in == 0.3
    assert p.knuckle_spacing == 0.2
