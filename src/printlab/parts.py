"""Find and load parts from parts/<name>/model.py."""

import importlib.util
from pathlib import Path
from types import ModuleType

PARTS_DIR = Path(__file__).resolve().parents[2] / "parts"


def part_names() -> list[str]:
    return sorted(p.parent.name for p in PARTS_DIR.glob("*/model.py"))


def load_part(name: str) -> ModuleType:
    path = PARTS_DIR / name / "model.py"
    if not path.exists():
        raise FileNotFoundError(f"no part named {name!r} (looked for {path})")
    spec = importlib.util.spec_from_file_location(f"parts.{name}.model", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
