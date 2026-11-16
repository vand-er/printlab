import math
from itertools import combinations

import pytest
import trimesh
from build123d import Axis, Box, GeomType, Pos, Vector

from printlab import nudge
from printlab.checks import check_fit, check_part, hole_diameters
from printlab.parts import load_part

model = load_part("clamp")

BODIES = ("cradle", "battery-door", "cart-body", "cart-door", "lever", "link")
# Moving pairs and their clearance; every other pair must not overlap.
FIT_PAIRS = (
    ("cradle", "battery-door"),
    ("cradle", "cart-body"),
    ("cart-body", "cart-door"),
    ("cradle", "lever"),
    ("lever", "link"),
    ("cart-body", "link"),
)


@pytest.fixture(scope="module")
def closed():
    return model.build()


@pytest.fixture(scope="module")
def opened():
    return model.build(pose="open")


@pytest.fixture(scope="module")
def centre():
    return model.build(pose="centre")


def test_every_body_is_one_valid_solid_that_fits_the_printer(closed):
    assert set(closed) == set(BODIES)
    for name, body in closed.items():
        report = check_part(body)
        assert report.ok, (name, report.problems)


def test_starts_at_the_middle_sizes(closed):
    params = model.Params()
    # Spec #10: 12.8 mm Battery bore, 12.2 mm Cart bore, 0.6 mm Stroke; plus the 0.2 offset.
    assert (params.battery_nominal_bore, params.cart_nominal_bore) == (12.8, 12.2)
    assert params.stroke == 0.6
    assert 13.0 in hole_diameters(closed["battery-door"])
    assert 13.0 in hole_diameters(closed["cradle"])
    assert 12.4 in hole_diameters(closed["cart-body"])
    assert 12.4 in hole_diameters(closed["cart-door"])


def bore_axes(body, diameter):
    """(x, y, direction) of each bore face of the given diameter."""
    axes = set()
    for face in body.faces().filter_by(GeomType.CYLINDER):
        if face.is_circular_concave and abs(2 * face.radius - diameter) < 1e-3:
            axis = face.axis_of_rotation
            d = axis.direction
            axes.add((round(axis.position.X, 4), round(axis.position.Y, 4), abs(round(d.Z, 4))))
    return axes


def test_cart_and_battery_bores_are_coaxial(closed):
    battery = bore_axes(closed["cradle"], 13.0) | bore_axes(closed["battery-door"], 13.0)
    cart = bore_axes(closed["cart-body"], 12.4) | bore_axes(closed["cart-door"], 12.4)
    assert battery and cart
    assert battery | cart == {(0.0, 0.0, 1.0)}


def check_clamp(bodies, params, pairs=FIT_PAIRS):
    problems = []
    for a, b in pairs:
        problems += [(a, b, p) for p in check_fit(bodies[a], bodies[b], params.gap).problems]
    for a, b in combinations(BODIES, 2):
        if (a, b) not in pairs and (bodies[a] & bodies[b]).solids():
            problems.append((a, b, "overlap"))
    return problems


@pytest.mark.parametrize("pose", ["closed", "open"])
def test_every_moving_pair_fits_in_both_poses(pose, closed, opened):
    bodies = {"closed": closed, "open": opened}[pose]
    assert check_clamp(bodies, model.Params()) == []


KEEP_OUT = 13.5  # mm below the Seat, spec #10: the fire button's top edge less a margin


@pytest.mark.parametrize("pose", ["closed", "open", "centre"])
def test_no_material_more_than_keep_out_below_the_seat(pose, closed, opened, centre):
    params = model.Params()
    bodies = {"closed": closed, "open": opened, "centre": centre}[pose]
    # With the Lever open the lip rests on the Cart's ledge, brass_height above the Seat.
    seat = opened["cart-body"].bounding_box().max.Z - params.lip_thickness - params.brass_height
    lowest = min(b.bounding_box().min.Z for b in bodies.values())
    assert lowest >= seat - KEEP_OUT - 1e-6


def test_cart_collar_drops_by_the_stroke_and_dips_at_centre_within_its_cap(closed, opened, centre):
    params = model.Params()
    assert params.centre_drop_cap == pytest.approx(0.1)
    for part in ("cart-body", "cart-door"):
        drop = opened[part].bounding_box().min.Z - closed[part].bounding_box().min.Z
        assert drop == pytest.approx(0.6, abs=0.01), part
    extra = closed["cart-body"].bounding_box().min.Z - centre["cart-body"].bounding_box().min.Z
    assert 0 < extra <= params.centre_drop_cap
    for a, b in combinations(BODIES, 2):
        assert not (centre[a] & centre[b]).solids(), (a, b, "centre")


def pin_centre(body, radius):
    """(y, z) of the one round pin along X on a body, read from its circular edges."""
    found = set()
    for edge in body.edges().filter_by(GeomType.CIRCLE):
        if abs(edge.radius - radius) < 1e-6 and abs(abs(edge.normal().X) - 1) < 1e-6:
            found.add((round(edge.arc_center.Y, 4), round(edge.arc_center.Z, 4)))
    (centre,) = found
    return centre


def test_locked_lever_is_past_centre_and_lies_flat_on_its_stop(closed):
    params = model.Params()
    r = params.pin_diameter / 2
    pivot = pin_centre(closed["cradle"], r)
    crank = pin_centre(closed["lever"], r)
    link_pin = pin_centre(closed["cart-body"], r)
    u = (pivot[0] - crank[0], pivot[1] - crank[1])
    v = (link_pin[0] - pivot[0], link_pin[1] - pivot[1])
    past = math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1]))
    assert abs(past) == pytest.approx(8.0, abs=1.0)
    # The Link's pull turns the Lever further; 3° that way it runs into the Cradle: its stop.
    torque = (crank[0] - pivot[0]) * (link_pin[1] - pivot[1]) - (crank[1] - pivot[1]) * (
        link_pin[0] - pivot[0]
    )
    pushed = closed["lever"].rotate(Axis((0, *pivot), (1, 0, 0)), math.copysign(3, torque))
    assert (closed["cradle"] & pushed).solids()
    # Lying flat: the Lever and Link stand no higher than the Cradle.
    top = closed["cradle"].bounding_box().max.Z
    assert max(closed[b].bounding_box().max.Z for b in ("lever", "link")) <= top


SHARP = 115.0  # degrees; a convex edge whose faces meet at less than this is sharp


def exposed_run(edge, others, reach):
    """The longest stretch of `edge` farther than `reach` from every other body, judged on
    points every SAMPLE mm, so an edge that only ends at a joint still counts as exposed."""
    near = [o for o in others if edge.distance_to(o) <= reach]
    if not near:
        return edge.length
    n = max(2, math.ceil(edge.length / SAMPLE) + 1)
    run = best = 0
    for i in range(n):
        q = edge.position_at(i / (n - 1))
        run = run + 1 if all(o.distance_to(q) > reach for o in near) else 0
        best = max(best, run)
    return max(0, best - 1) * edge.length / (n - 1)


SAMPLE = 0.1  # mm between points judged along an edge


def sharp_outside_edges(bodies, name, params):
    """Sharp convex edges of one body that face the outside: not a joint or parting line
    (within the gap of another body), not in a bore, with an exposed stretch longer than
    the run-out left where two edge breaks meet."""
    body = bodies[name]
    solid = body.solids()[0]
    faces_of = {}
    for face in body.faces():
        for edge in face.edges():
            faces_of.setdefault(edge, []).append(face)
    others = [b for n, b in bodies.items() if n != name]
    in_bore = max(params.battery_nominal_bore, params.cart_nominal_bore) / 2 + params.fdm_offset
    found = []
    for edge, faces in faces_of.items():
        if len(faces) != 2 or edge.length <= 2 * params.edge_break:
            continue
        q = edge.position_at(0.5)
        if math.hypot(q.X, q.Y) < in_bore:
            continue
        n1, n2 = faces[0].normal_at(q), faces[1].normal_at(q)
        between = 180 - math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2)))))
        if between >= SHARP or solid.is_inside(q + (n1 - n2) * 0.01):  # blunt or concave
            continue
        if exposed_run(edge, others, params.gap + params.joint_margin) <= 2 * params.edge_break:
            continue
        found.append((name, round(edge.length, 2), round(q.X, 2), round(q.Y, 2), round(q.Z, 2)))
    return found


def test_no_outside_edge_is_left_sharp(closed):
    params = model.Params()
    assert params.edge_break >= 0.3  # mm, a named size, big enough to feel in a pocket
    sharp = [e for name in BODIES for e in sharp_outside_edges(closed, name, params)]
    assert sharp == []


OVERHANG = 0.75  # -normal.Z beyond which a face needs support: about 49° from vertical


def mesh(body):
    vertices, triangles = body.tessellate(tolerance=0.02, angular_tolerance=0.1)
    return trimesh.Trimesh([(v.X, v.Y, v.Z) for v in vertices], triangles)


def test_prints_without_supports_battery_axis_vertical(closed):
    """Every downward face is on the bed or rests, across the gap, on another body."""
    params = model.Params()
    unsupported = []
    for name, body in closed.items():
        m = mesh(body)
        down = m.triangles_center[(m.face_normals[:, 2] < -OVERHANG) & (m.area_faces > 1e-4)]
        others = [o for n, o in closed.items() if n != name]
        for x, y, z in {tuple(round(float(v), 2) for v in c) for c in down}:
            if z < 1e-3:  # on the bed
                continue
            if min(o.distance_to(Vector(x, y, z)) for o in others) <= params.gap + 0.06:
                continue  # rests on another body across the gap
            if is_ledge(body, x, y, z):
                continue
            unsupported.append((name, x, y, z))
    assert sorted(unsupported) == []


LEDGE = 0.5  # mm; a ledge no wider than one 0.5 mm line prints without support


def is_ledge(body, x, y, z):
    """Whether the body's own wall stands under (x, y, z) within one line width."""
    solid = body.solids()[0]
    return any(
        solid.is_inside(Vector(x + r * math.cos(a), y + r * math.sin(a), z - 0.1))
        for r in (LEDGE / 2, LEDGE)
        for a in (i * math.pi / 4 for i in range(8))
    )


@pytest.fixture(scope="module")
def nudges():
    """Every numeric field of the full Clamp's Params nudged ±10 %, edge breaks and all,
    run once across worker processes: {(field, factor): problems}."""
    return nudge.audit("clamp", FIT_PAIRS, ("closed", "open"))


@pytest.mark.parametrize("factor", nudge.FACTORS)
@pytest.mark.parametrize("field", nudge.numeric_fields(model.Params))
def test_survives_plus_minus_ten_percent(field, factor, nudges):
    assert nudges[(field, factor)] == []


def test_slim_outline_fits_its_footprint_limit(closed):
    params = model.Params()
    lo = [min(getattr(b.bounding_box().min, a) for b in closed.values()) for a in "XY"]
    hi = [max(getattr(b.bounding_box().max, a) for b in closed.values()) for a in "XY"]
    width, depth = hi[0] - lo[0], hi[1] - lo[1]
    limit_x, limit_y = params.footprint_limit
    assert width <= limit_x and depth <= limit_y
    # The limit is a pocket size, not a loose bound: within 1 mm of the outline.
    assert limit_x - width < 1 and limit_y - depth < 1


def test_cradle_above_the_battery_collar_is_only_as_wide_as_the_rib_head(closed):
    """Above the Battery collar the Cradle carries only the rib; the rest is trimmed."""
    params = model.Params()
    top = closed["cradle"].bounding_box().max.Z
    z = (params.battery_collar_height + top) / 2
    slab = Pos(0, 0, z) * Box(100, 100, 0.1)
    assert (closed["cradle"] & slab).bounding_box().size.X <= params.rib_head_width + 1e-6


MIN_WALL = 1.2  # mm, CLAUDE.md design rule for load-bearing walls


def test_each_latch_arm_is_a_horizontal_beam_bending_in_the_layer_plane(closed):
    params = model.Params()
    arms = model.latch_arms(params)
    assert set(arms) == {"battery-door", "cart-door"}
    # Spec #10: the 12 mm Battery collar's Latch runs its full height.
    assert arms["battery-door"].bounding_box().size.Z == pytest.approx(12.0)
    for door, arm in arms.items():
        # The arm belongs to its Door; the edge breaks shave only its corners.
        assert (closed[door] & arm).volume > 0.95 * arm.volume, door
        size = arm.bounding_box().size
        thickness, length = sorted((size.X, size.Y))
        # Long along a horizontal axis, thin along the other, tall in Z: it can only bend
        # about Z, so it deflects within the XY (layer) plane.
        assert length > 3 * thickness, door
        assert size.Z > 2 * thickness, door
        assert thickness >= MIN_WALL, door


def test_no_load_bearing_wall_is_under_the_minimum(closed):
    params = model.Params()
    for b in ("lever", "link"):
        size = closed[b].bounding_box().size
        assert size.X >= MIN_WALL and size.Y >= MIN_WALL, b
    for field in ("wall", "knuckle_wall", "carriage_wall", "cradle_back_depth", "lug_width"):
        assert getattr(params, field) >= MIN_WALL, field
    assert params.pin_diameter >= 2 * MIN_WALL
