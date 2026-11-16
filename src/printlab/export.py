"""Export a part, or several named bodies, to STEP, STL, GLB and a PNG preview, verifying each file."""

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from build123d import (  # noqa: E402
    Color,
    Compound,
    Keep,
    Part,
    Plane,
    export_gltf,
    export_step,
    export_stl,
    import_step,
)
from matplotlib.patches import Patch  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

# What a part's build() may return: one Part, or named bodies printed together.
Parts = Part | Mapping[str, Part]

PALETTE = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf")
PETG_DENSITY = 1.27  # g/cm³


class ExportError(Exception):
    pass


@dataclass
class ExportResult:
    step: Path
    stl: Path
    glb: Path
    preview: Path
    step_volume: float  # mm³, summed over the bodies read back from the STEP
    colours: dict[str, str]  # body name -> hex colour in the preview and GLB

    @property
    def grams(self) -> float:
        """Estimated filament mass in PETG."""
        return self.step_volume / 1000 * PETG_DENSITY


def named_parts(parts: Parts, name: str) -> dict[str, Part]:
    """The bodies to export, by name. A single Part is one body named after the part."""
    return dict(parts) if isinstance(parts, Mapping) else {name: parts}


def export_part(parts: Parts, name: str, out_dir: Path) -> ExportResult:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    step, stl, glb, preview = (out_dir / f"{name}.{ext}" for ext in ("step", "stl", "glb", "png"))

    bodies, colours = {}, {}
    for i, (body_name, body) in enumerate(named_parts(parts, name).items()):
        body = copy.copy(body)  # labels and colours go on a copy, not the caller's part
        colours[body_name] = PALETTE[i % len(PALETTE)]
        body.label, body.color = body_name, Color(colours[body_name])
        bodies[body_name] = body
    assembly = Compound(label=name, children=list(bodies.values()))

    export_step(assembly, str(step))
    # Re-import and check what was written, not the shapes held in memory.
    written = sorted(s.volume for s in import_step(str(step)).solids())
    expected = sorted(b.volume for b in bodies.values())
    if len(written) != len(expected) or any(
        abs(w - e) > 1e-4 * e for w, e in zip(written, expected)
    ):
        raise ExportError(f"{step} does not round-trip to the same {len(expected)} solid(s)")

    export_stl(assembly, str(stl), tolerance=0.01, angular_tolerance=0.1)
    if not trimesh.load(stl).is_watertight:
        raise ExportError(f"{stl} is not watertight")

    export_gltf(assembly, str(glb), binary=True, linear_deflection=0.01)
    _render_preview(bodies, colours, preview, title=name)
    return ExportResult(
        step=step, stl=stl, glb=glb, preview=preview, step_volume=sum(written), colours=colours
    )


def _render_preview(
    bodies: dict[str, Part], colours: dict[str, str], path: Path, title: str
) -> None:
    """Iso, top, front, bottom and a section through the middle, each body in its own colour."""
    assembly_box = Compound(children=list(bodies.values())).bounding_box()
    centre = assembly_box.center()
    # Keep the back half (+Y) so the front view looks onto the cut face.
    cut = Plane(origin=centre, x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    halves = {}
    for body_name, body in bodies.items():
        half = body.split(cut, keep=Keep.TOP)
        if half is not None and half.volume > 0:
            halves[body_name] = half

    views = [
        ("iso", 30, -60, bodies),
        ("top", 90, -90, bodies),
        ("front", 0, -90, bodies),
        ("bottom", -90, -90, bodies),
        (f"section at y = {centre.Y:.1f}", 0, -90, halves),
    ]
    lo = np.array(tuple(assembly_box.min))
    hi = np.array(tuple(assembly_box.max))
    fig = plt.figure(figsize=(20, 4.5), dpi=150)
    for i, (label, elev, azim, shown) in enumerate(views, start=1):
        ax = fig.add_subplot(1, len(views), i, projection="3d")
        triangles, facecolours = _shaded_triangles(shown, colours, elev, azim)
        if len(triangles):
            ax.add_collection3d(Poly3DCollection(
                    triangles, facecolors=facecolours, edgecolors=facecolours, linewidths=0.2
                )
            )
        ax.set_xlim(lo[0], hi[0])
        ax.set_ylim(lo[1], hi[1])
        ax.set_zlim(lo[2], hi[2])
        ax.set_box_aspect(tuple(max(float(e), 1e-3) for e in hi - lo))
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(label)
        ax.set_axis_off()
    x, y, z = hi - lo
    fig.suptitle(f"{title}  —  {x:.1f} × {y:.1f} × {z:.1f} mm")
    fig.legend(
        handles=[Patch(color=colours[n], label=n) for n in bodies],
        loc="lower center",
        ncol=len(bodies),
        frameon=False,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.93))
    fig.savefig(path)
    plt.close(fig)


def _shaded_triangles(
    bodies: dict[str, Part], colours: dict[str, str], elev: float, azim: float
) -> tuple[np.ndarray, np.ndarray]:
    """Every body's front-facing triangles, flat-shaded; shading keeps hue.

    Faces turned away from the viewer are dropped, because matplotlib sorts by depth per
    triangle and would otherwise paint hidden faces over visible ones.
    """
    viewer = _direction(elev, azim)
    light = _direction(elev + 30, azim - 40)  # off the view axis, so faces differ in shade
    all_triangles, all_colours = [], []
    for body_name, body in bodies.items():
        vertices, faces = body.tessellate(tolerance=0.05, angular_tolerance=0.2)
        points = np.array([tuple(v) for v in vertices])
        triangles = points[np.array(faces)]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
        facing = normals @ viewer > -1e-6
        triangles, normals = triangles[facing], normals[facing]
        brightness = 0.45 + 0.55 * np.clip(normals @ light, 0, 1)
        base = np.array(mcolors.to_rgb(colours[body_name]))
        all_triangles.append(triangles)
        all_colours.append(brightness[:, None] * base)
    if not all_triangles:
        return np.empty((0, 3, 3)), np.empty((0, 3))
    return np.concatenate(all_triangles), np.concatenate(all_colours)


def _direction(elev: float, azim: float) -> np.ndarray:
    """Unit vector towards a matplotlib camera at this elevation and azimuth, in degrees."""
    e, a = np.radians(elev), np.radians(azim)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
