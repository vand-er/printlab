import matplotlib.colors
import matplotlib.image
import numpy as np
import trimesh
from build123d import Box, Cylinder, Pos, import_step

from printlab.export import export_part


def test_export_writes_verified_step_stl_and_preview(tmp_path):
    part = Box(30, 20, 5) - Cylinder(2, 5)

    result = export_part(part, "demo", tmp_path)

    assert result.step.exists() and result.stl.exists() and result.preview.exists()
    mesh = trimesh.load(result.stl)
    assert mesh.is_watertight
    assert abs(mesh.volume - part.volume) / part.volume < 0.01
    # The STEP is re-imported and checked, not trusted.
    assert abs(result.step_volume - part.volume) / part.volume < 1e-4


def two_bodies():
    # A pin inside a ring with a gap, like a print-in-place hinge.
    ring = Cylinder(10, 5) - Cylinder(6, 5)
    pin = Cylinder(5, 5)
    return {"ring": ring, "pin": pin}


def test_two_bodies_export_to_one_watertight_stl_and_round_tripping_step(tmp_path):
    result = export_part(two_bodies(), "hinge", tmp_path)

    mesh = trimesh.load(result.stl)
    assert mesh.is_watertight
    assert len(mesh.split(only_watertight=True)) == 2
    solids = import_step(str(result.step)).solids()
    # Ring: pi*(100-36)*5, pin: pi*25*5
    assert sorted(round(s.volume, 1) for s in solids) == [392.7, 1005.3]


def test_preview_section_handles_a_body_the_cut_splits_in_two(tmp_path):
    # A U open towards +Y: the section plane at mid-Y leaves two separate prongs.
    u_shape = Box(30, 20, 5) - Pos(0, 5, 0) * Box(10, 10, 5)
    result = export_part({"u": u_shape, "pin": Pos(0, 5, 0) * Cylinder(2, 5)}, "u", tmp_path)

    assert result.preview.exists()


def test_export_estimates_grams_of_petg(tmp_path):
    result = export_part(Box(10, 10, 10), "cube", tmp_path)

    assert round(result.grams, 3) == 1.27  # 1 cm³ at 1.27 g/cm³


def pixels_near(png, hex_colour, hue_tolerance=0.02):
    """How many saturated pixels in the PNG share the colour's hue (shading keeps hue)."""
    rgba = matplotlib.image.imread(png)
    hsv = matplotlib.colors.rgb_to_hsv(rgba[..., :3])
    hue = matplotlib.colors.rgb_to_hsv(matplotlib.colors.to_rgb(hex_colour))[0]
    near = np.abs((hsv[..., 0] - hue + 0.5) % 1 - 0.5) < hue_tolerance
    return int((near & (hsv[..., 1] > 0.3) & (hsv[..., 2] > 0.2)).sum())


def test_two_bodies_preview_and_glb_show_each_body_in_its_own_colour(tmp_path):
    result = export_part(two_bodies(), "hinge", tmp_path)

    assert set(result.colours) == {"ring", "pin"}
    assert result.colours["ring"] != result.colours["pin"]
    for colour in result.colours.values():
        # Far more than a legend swatch: the body itself is drawn in this colour.
        assert pixels_near(result.preview, colour) > 5000

    scene = trimesh.load(result.glb)
    colour_of = {}
    for geometry_name, geometry in scene.geometry.items():
        body = geometry_name.split("_")[0]
        colour_of.setdefault(body, set()).add(tuple(geometry.visual.material.baseColorFactor))
    assert set(colour_of) == {"ring", "pin"}
    assert all(len(c) == 1 for c in colour_of.values())
    assert colour_of["ring"] != colour_of["pin"]
