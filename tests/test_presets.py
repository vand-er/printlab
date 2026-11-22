"""ADR 0002: process presets override only settings that Bambu's system profiles define."""

import json
import os
from pathlib import Path

import pytest

PRESETS = sorted((Path(__file__).parents[1] / "presets").glob("*.json"))
SYSTEM = Path(os.environ.get("APPDATA", "")) / "BambuStudio" / "system" / "BBL" / "process"
META = {"type", "name", "inherits", "from", "print_settings_id", "version"}


def _inherited(name: str) -> dict:
    """Merged settings of a system profile and everything it inherits."""
    data = json.loads((SYSTEM / f"{name}.json").read_text(encoding="utf-8"))
    parent = _inherited(data["inherits"]) if "inherits" in data else {}
    return {**parent, **data}


def _forbidden(preset: dict) -> list[str]:
    """ADR 0004: keys that could run scripts or change G-code."""
    return [k for k in preset if k in {"post_process", "filename_format"} or k.endswith("_gcode")]


@pytest.mark.parametrize("path", PRESETS, ids=lambda p: p.stem)
def test_preset_cannot_run_scripts_or_change_gcode(path):
    assert not _forbidden(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "key, value",
    [
        ("post_process", ["python evil.py"]),
        ("filename_format", "{input_filename_base}.gcode"),
        ("layer_change_gcode", "M117 hi"),
    ],
)
def test_forbidden_key_fails_the_preset_check(key, value):
    preset = {"type": "process", "name": "bad", "inherits": "0.20mm Standard @BBL X1C", key: value}
    assert _forbidden(preset) == [key]


@pytest.mark.skipif(not SYSTEM.is_dir(), reason="Bambu Studio system profiles not installed")
@pytest.mark.parametrize("path", PRESETS, ids=lambda p: p.stem)
def test_preset_overrides_only_known_settings(path):
    preset = json.loads(path.read_text(encoding="utf-8"))
    assert preset["type"] == "process", "only process presets are allowed"
    base = _inherited(preset["inherits"])
    for key, value in preset.items():
        if key in META:
            continue
        assert key in base, f"{key} is not a Bambu process setting"
        assert type(value) is type(base[key]), f"{key} has the wrong value type"
