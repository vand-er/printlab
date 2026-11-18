"""CLAUDE.md's Layout block names every module in src/printlab/."""

from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_layout_block_names_every_module():
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    layout = claude.split("## Layout", 1)[1].split("```")[1]
    modules = [p.name for p in ROOT.glob("src/printlab/*.py") if p.name != "__init__.py"]
    missing = [m for m in modules if f"src/printlab/{m}" not in layout]
    assert not missing, missing
