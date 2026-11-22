"""Bambu's system profiles, resolved as Bambu Studio's preset bundle resolves them (ADR 0004).

Reads only `%APPDATA%\\BambuStudio\\system\\BBL`, never the install folder, and never writes there.
"""

import json
import os
from pathlib import Path
from typing import Literal

SYSTEM = Path(os.environ.get("APPDATA", "")) / "BambuStudio" / "system" / "BBL"

Kind = Literal["machine", "process"]

SETTINGS_ID = {"machine": "printer_settings_id", "process": "print_settings_id"}
# Labels of an include file itself, not settings it adds.
INCLUDE_LABELS = {"type", "name", "from", "inherits", "include", "setting_id", "instantiation"}


class ProfileError(Exception):
    """A Bambu system profile is missing or unreadable."""


def _read(kind: Kind, name: str, root: Path) -> dict:
    path = root / kind / f"{name}.json"
    if not path.is_file():
        raise ProfileError(f"Bambu system profile not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _resolved(kind: Kind, name: str, root: Path) -> dict:
    own = _read(kind, name, root)
    settings = _resolved(kind, own["inherits"], root) if own.get("inherits") else {}
    for include in own.get("include", []):
        settings.update({k: v for k, v in _read(kind, include, root).items() if k not in INCLUDE_LABELS})
    settings.update(own)
    return settings


def resolve(kind: Kind, name: str, root: Path = SYSTEM) -> dict:
    """Complete settings for a named machine or process system profile, ready for the command line.

    The fully resolved `inherits` parent first, then each `include` file, then the profile's own keys.
    """
    settings = _resolved(kind, name, root)
    settings["from"] = "system"
    settings[SETTINGS_ID[kind]] = name
    return settings


def filament(path: Path) -> bytes:
    """The user's filament preset, unchanged."""
    return Path(path).read_bytes()
