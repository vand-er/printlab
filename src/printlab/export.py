"""Export a part to STEP, STL and a PNG preview, verifying each file."""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import trimesh  # noqa: E402
from build123d import Part, export_step, export_stl, import_step  # noqa: E402


class ExportError(Exception):
    pass


@dataclass
class ExportResult:
    step: Path
    stl: Path
    preview: Path
    step_volume: float


def export_part(part: Part, name: str, out_dir: Path) -> ExportResult:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    step, stl, preview = (out_dir / f"{name}.{ext}" for ext in ("step", "stl", "png"))

    export_step(part, str(step))
    # Re-import and check what was written, not the shape held in memory.
    reimported = import_step(str(step))
    if len(reimported.solids()) != 1 or abs(reimported.volume - part.volume) > 1e-4 * part.volume:
        raise ExportError(f"{step} does not round-trip to the same single solid")

    export_stl(part, str(stl), tolerance=0.01, angular_tolerance=0.1)
    mesh = trimesh.load(stl)
    if not mesh.is_watertight:
        raise ExportError(f"{stl} is not watertight")

    _render_preview(mesh, preview, title=name)
    return ExportResult(step=step, stl=stl, preview=preview, step_volume=reimported.volume)


def _render_preview(mesh: trimesh.Trimesh, path: Path, title: str) -> None:
    """Three views (iso, top, front) so a human can sanity-check the shape."""
    views = [("iso", 30, -60), ("top", 90, -90), ("front", 0, -90)]
    fig = plt.figure(figsize=(12, 4), dpi=150)
    for i, (label, elev, azim) in enumerate(views, start=1):
        ax = fig.add_subplot(1, 3, i, projection="3d")
        ax.plot_trisurf(
            *mesh.vertices.T, triangles=mesh.faces, color="#8fb3d9", edgecolor="none", shade=True
        )
        ax.view_init(elev=elev, azim=azim)
        ax.set_box_aspect(tuple(float(e) for e in mesh.extents))
        ax.set_title(label)
        ax.set_axis_off()
    x, y, z = mesh.extents
    fig.suptitle(f"{title}  —  {x:.1f} × {y:.1f} × {z:.1f} mm")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
