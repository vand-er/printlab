"""Read the settings the slicer needs from a part's print.md.

The form is one fenced block tagged `slice`, one `key: value` per line:

    ```slice
    process: 0.20mm Standard @BBL X1C
    filament: Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle
    plate: Textured PEI Plate
    stl: out/clamp.stl
    ```

`process` is a Bambu system process name or a file in presets/; `filament` is the user's own
Bambu Studio filament preset; `stl` is the part's PETG STL, relative to the part's folder.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from printlab.parts import PARTS_DIR

KEYS = ("process", "filament", "plate", "stl")
FENCE = re.compile(r"^```slice[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)


class SliceSettingsError(ValueError):
    """A part cannot be sliced: its print.md is missing or lacks a slice setting."""


@dataclass(frozen=True)
class SliceSettings:
    process: str
    filament: str
    plate: str
    stl: Path


def read_slice_settings(part: str, parts_dir: Path = PARTS_DIR) -> SliceSettings:
    folder = parts_dir / part
    path = folder / "print.md"
    if not path.exists():
        raise SliceSettingsError(f"{part}: cannot slice, it has no print.md")
    blocks = FENCE.findall(path.read_text(encoding="utf-8"))
    if not blocks:
        raise SliceSettingsError(f"{part}: cannot slice, print.md has no ```slice block")
    if len(blocks) > 1:
        raise SliceSettingsError(f"{part}: cannot slice, print.md has {len(blocks)} ```slice blocks")
    values: dict[str, str] = {}
    for line in blocks[0].splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or key not in KEYS:
            raise SliceSettingsError(f"{part}: cannot slice, unknown line in ```slice block: {line!r}")
        if key in values:
            raise SliceSettingsError(f"{part}: cannot slice, {key} is given twice")
        values[key] = value
    missing = [k for k in KEYS if not values.get(k)]
    if missing:
        raise SliceSettingsError(f"{part}: cannot slice, its ```slice block lacks {', '.join(missing)}")
    return SliceSettings(values["process"], values["filament"], values["plate"], folder / values["stl"])
