"""Slice a part with the Bambu Studio command line, from Bambu's own profiles (ADR 0004).

`slice_part(settings)` resolves the X1C machine settings and the process preset, takes the user's
filament preset unchanged, slices the part's STL in a temp folder that is always deleted, checks the
sliced output against Bambu's originals, and returns a `SliceReport`. Nothing sliced is kept unless
`keep` names where the checked sliced file goes.
"""

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import trimesh
from build123d import Part

from printlab import islands, profiles
from printlab.islands import Island
from printlab.slice_settings import SliceSettings

BAMBU_STUDIO_ENV = "PRINTLAB_BAMBU_STUDIO"
BAMBU_STUDIO_DEFAULT = Path(r"G:\bambu studio\bambu-studio.exe")
MACHINE = "Bambu Lab X1 Carbon 0.4 nozzle"
PRESETS_DIR = Path(__file__).resolve().parents[2] / "presets"
TIMEOUT_S = 600
# The command line's own G-code key set (BambuStudio.cpp, gcodes_key_set, v02.09.01.70).
GCODE_KEYS = (
    "filament_end_gcode", "filament_start_gcode", "change_filament_gcode", "layer_change_gcode",
    "machine_end_gcode", "machine_pause_gcode", "machine_start_gcode", "template_custom_gcode",
    "printing_by_object_gcode", "before_layer_change_gcode", "time_lapse_gcode", "wrapping_detection_gcode",
)  # fmt: skip
FILAMENT_GCODE_KEYS = {"filament_start_gcode", "filament_end_gcode"}
BED_KEYS = ("printable_area", "bed_exclude_area")
# AMS drying settings, one value per AMS model, which the output trims to one; they never reach the G-code.
AMS_DRYING = "filament_dev_"
# Grams from the plate metadata must match its filament length at the preset's density, within rounding.
GRAMS_TOLERANCE = 0.02
GRAMS_TOLERANCE_REL = 0.01
# Support extrusions closer than this grid pitch belong to one support region.
SUPPORT_CELL_MM = 2.0
PRESET_LABELS = {"type", "name", "inherits", "from", "print_settings_id", "version"}


class SliceError(Exception):
    """Slicing could not run, or its output failed a check; nothing sliced is kept."""


@dataclass(frozen=True)
class SupportRegion:
    """Where generated supports land: extents in the part's own x and y, and in height above the bed."""

    x: tuple[float, float]
    y: tuple[float, float]
    z: tuple[float, float]


@dataclass(frozen=True)
class SliceReport:
    grams: float
    seconds: float
    supports: tuple[SupportRegion, ...]
    islands: tuple[Island, ...] = ()
    # The sliced config's first-layer settings, by key; two slices compare only when these are equal.
    first_layer: Mapping[str, str | tuple[str, ...]] = field(default_factory=dict)


def bambu_studio() -> Path:
    path = Path(os.environ.get(BAMBU_STUDIO_ENV) or BAMBU_STUDIO_DEFAULT)
    if not path.is_file():
        raise SliceError(f"Bambu Studio not found at {path} (set {BAMBU_STUDIO_ENV} to its bambu-studio.exe)")
    return path


def filament_preset(name: str) -> Path:
    """The user's own Bambu Studio filament preset file, by name."""
    user = profiles.SYSTEM.parents[1] / "user"
    found = [*user.glob(f"*/filament/base/{name}.json"), *user.glob(f"*/filament/{name}.json")]
    if len(found) != 1:
        where = "not found" if not found else f"found {len(found)} times"
        raise SliceError(f"filament preset {name!r} {where} under {user}")
    return found[0]


def slice_part(
    settings: SliceSettings, keep: Path | None = None, bodies: Mapping[str, Part] = {}
) -> SliceReport:
    """Slice and check the part; with `keep`, copy the sliced file there once every check has passed.

    `bodies` are the bodies in the STL, by name; first-layer islands are named after them.
    """
    exe = bambu_studio()
    filament_path = filament_preset(settings.filament)
    try:
        machine = profiles.resolve("machine", MACHINE)
        process = _process(settings.process)
    except profiles.ProfileError as problem:
        raise SliceError(str(problem)) from problem
    raw_filament = profiles.filament(filament_path)
    filament = json.loads(raw_filament.decode("utf-8-sig"))
    if not settings.stl.is_file():
        raise SliceError(f"no STL to slice at {settings.stl}")
    with tempfile.TemporaryDirectory(prefix="printlab-slice-") as tmp:
        sliced, result = _run(exe, Path(tmp), machine, process, _labelled(raw_filament), settings)
        with zipfile.ZipFile(sliced) as archive:
            config = json.loads(archive.read("Metadata/project_settings.config"))
            _check_config(config, filament, settings)
            grams, seconds = _plate_numbers(archive.read("Metadata/slice_info.config"), filament)
            gcode = archive.read("Metadata/plate_1.gcode").decode("utf-8")
        offset = _bed_offset(result, settings.stl, config)
        footprints = {name: islands.footprint(body) for name, body in bodies.items()}
        report = SliceReport(
            grams, seconds, _supports(gcode, offset),
            islands.first_layer_islands(gcode, offset, footprints), islands.first_layer_settings(config),
        )  # fmt: skip
        if keep is not None:
            shutil.copyfile(sliced, keep)
    return report


def _process(name: str) -> dict:
    """A Bambu system process profile, or a preset in presets/ laid over the system one it inherits."""
    path = PRESETS_DIR / f"{name}.json"
    if not path.is_file():
        return profiles.resolve("process", name)
    preset = json.loads(path.read_text(encoding="utf-8"))
    if forbidden := [k for k in preset if k in {"post_process", "filename_format"} or k.endswith("_gcode")]:
        raise SliceError(f"preset {path.name} sets {', '.join(forbidden)}, which no preset may set")
    settings = profiles.resolve("process", preset["inherits"])
    settings.update({k: v for k, v in preset.items() if k not in PRESET_LABELS})
    settings.update({"name": name, "inherits": preset["inherits"], "from": "User", "print_settings_id": name})
    return settings


def _labelled(raw: bytes) -> bytes:
    """The filament preset's bytes with a `type` label added, which the command line needs to parse it.

    Bambu Studio stores user presets without one (the folder says what they are); every setting stays
    byte for byte as the user saved it.
    """
    if "type" in json.loads(raw.decode("utf-8-sig")):
        return raw
    brace = raw.index(b"{") + 1
    return raw[:brace] + b'\n    "type": "filament",' + raw[brace:]


def _run(exe, tmp, machine, process, filament, settings) -> tuple[Path, dict]:
    files = {"machine.json": json.dumps(machine, indent=4), "process.json": json.dumps(process, indent=4)}
    for name, text in files.items():
        (tmp / name).write_text(text, encoding="utf-8")
    (tmp / "filament.json").write_bytes(filament)
    out = tmp / "out"
    out.mkdir()
    sliced = out / "part.gcode.3mf"
    command = [
        str(exe),
        "--orient", "0",
        "--arrange", "1",
        "--load-settings", f"{tmp / 'machine.json'};{tmp / 'process.json'}",
        "--load-filaments", str(tmp / "filament.json"),
        "--curr-bed-type", settings.plate,
        "--slice", "0",
        "--export-3mf", sliced.name,
        "--outputdir", str(out),
        str(settings.stl),
    ]  # fmt: skip
    try:
        run = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_S, cwd=tmp)
    except subprocess.TimeoutExpired as problem:
        raise SliceError(f"Bambu Studio did not finish within {TIMEOUT_S} s") from problem
    result_path = out / "result.json"
    if not result_path.is_file():
        raise SliceError(f"Bambu Studio exited with {run.returncode} and wrote no result.json")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("return_code") != 0:
        raise SliceError(f"Bambu Studio failed ({result.get('return_code')}): {result.get('error_string')}")
    if warnings := [
        p["warning_message"] for p in result.get("sliced_plates", []) if p.get("warning_message")
    ]:
        raise SliceError(f"Bambu Studio warned: {'; '.join(warnings)}")
    if run.returncode != 0 or not sliced.is_file():
        raise SliceError(f"Bambu Studio exited with {run.returncode} and no sliced file")
    return sliced, result


def _bambu_original(name: str, key: str):
    """A machine setting as Bambu's own files give it: the profile, then its includes (last wins),
    then its parent. Looked up key by key, apart from the resolver, so a resolver bug shows up."""
    data = json.loads((profiles.SYSTEM / "machine" / f"{name}.json").read_text(encoding="utf-8"))
    if key in data:
        return data[key]
    for include in reversed(data.get("include", [])):
        included = json.loads((profiles.SYSTEM / "machine" / f"{include}.json").read_text(encoding="utf-8"))
        if key in included:
            return included[key]
    return _bambu_original(data["inherits"], key) if data.get("inherits") else None


def _check_config(config: dict, filament: dict, settings: SliceSettings) -> None:
    """The sliced output's resolved config equals Bambu's originals and the user's preset, byte for byte."""
    expected = {}
    for key in GCODE_KEYS:
        original = filament.get(key) if key in FILAMENT_GCODE_KEYS else _bambu_original(MACHINE, key)
        expected[key] = "" if original is None else original
    for key in BED_KEYS:
        expected[key] = _bambu_original(MACHINE, key)
    expected.update({k: v for k, v in filament.items() if "temp" in k and not k.startswith(AMS_DRYING)})
    expected["curr_bed_type"] = settings.plate
    if differing := [key for key, value in expected.items() if config.get(key) != value]:
        raise SliceError(
            f"sliced config differs from Bambu's and the user's presets in {', '.join(differing)}"
        )


def _plate_numbers(slice_info: bytes, filament: dict) -> tuple[float, float]:
    plate = ET.fromstring(slice_info).find("plate")
    meta = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
    grams, seconds = float(meta["weight"]), float(meta["prediction"])
    metres = sum(float(f.get("used_m")) for f in plate.findall("filament"))
    density = float(filament["filament_density"][0])
    radius = float(filament["filament_diameter"][0]) / 2
    expected = metres * math.pi * radius**2 * density  # 1 m of filament per mm² of section is 1 cm³
    if abs(grams - expected) > GRAMS_TOLERANCE + GRAMS_TOLERANCE_REL * expected:
        raise SliceError(f"sliced {grams} g does not match {metres} m of filament at {density} g/cm³")
    return grams, seconds


def _bed_offset(result: dict, stl: Path, config: dict) -> tuple[float, float]:
    """What to add to a G-code position to get the part's own x and y (arrange moves the part).

    The G-code is the plate position less the extruder offset (the X1C's is 0 x 2 mm).
    """
    box = result["sliced_plates"][0]["objects"][0]["bbox"]
    low = trimesh.load(stl, force="mesh").bounds[0]
    ex, ey = (float(v) for v in config["extruder_offset"][0].split("x"))
    return float(low[0]) - box["x"] + ex, float(low[1]) - box["y"] + ey


FEATURE = "; FEATURE: "
MOVE = re.compile(r"^G[0-3] ")
WORD = re.compile(r"([XYZE])(-?[\d.]+)")


def _supports(gcode: str, offset: tuple[float, float]) -> tuple[SupportRegion, ...]:
    """Support regions from the G-code's own feature markers, not from whether supports were enabled."""
    cells: dict[tuple[int, int], list[float]] = {}
    x = y = z = 0.0
    support = False
    for line in gcode.splitlines():
        if line.startswith(FEATURE):
            support = line.removeprefix(FEATURE).startswith("Support")
        elif MOVE.match(line):
            words = dict(WORD.findall(line.split(";")[0]))
            x, y, z = (float(words.get(k, v)) for k, v in zip("XYZ", (x, y, z)))
            if support and float(words.get("E", 0)) > 0:
                cell = (math.floor(x / SUPPORT_CELL_MM), math.floor(y / SUPPORT_CELL_MM))
                cells.setdefault(cell, []).append(z)
    regions = []
    while cells:
        stack, group = [next(iter(cells))], {}
        while stack:
            cell = stack.pop()
            if cell in cells:
                group[cell] = cells.pop(cell)
                stack += [(cell[0] + dx, cell[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        xs, ys = [c[0] for c in group], [c[1] for c in group]
        zs = [h for heights in group.values() for h in heights]
        regions.append(
            SupportRegion(
                (min(xs) * SUPPORT_CELL_MM + offset[0], (max(xs) + 1) * SUPPORT_CELL_MM + offset[0]),
                (min(ys) * SUPPORT_CELL_MM + offset[1], (max(ys) + 1) * SUPPORT_CELL_MM + offset[1]),
                (min(zs), max(zs)),
            )
        )
    return tuple(sorted(regions, key=lambda r: (r.x, r.y)))
