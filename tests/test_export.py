import trimesh
from build123d import Box, Cylinder

from vander.export import export_part


def test_export_writes_verified_step_stl_and_preview(tmp_path):
    part = Box(30, 20, 5) - Cylinder(2, 5)

    result = export_part(part, "demo", tmp_path)

    assert result.step.exists() and result.stl.exists() and result.preview.exists()
    mesh = trimesh.load(result.stl)
    assert mesh.is_watertight
    assert abs(mesh.volume - part.volume) / part.volume < 0.01
    # The STEP is re-imported and checked, not trusted.
    assert abs(result.step_volume - part.volume) / part.volume < 1e-4
