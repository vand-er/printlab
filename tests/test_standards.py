"""Mechanical coding standards, checked over every part's source."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
# Every module that builds geometry; the pipeline modules carry no dimensions.
NOT_GEOMETRY = {"__init__.py", "checks.py", "export.py", "cli.py", "nudge.py", "parts.py"}
PARTS = sorted(ROOT.glob("parts/*/model.py")) + sorted(
    p for p in ROOT.glob("src/printlab/*.py") if p.name not in NOT_GEOMETRY
)

# Literals that are geometry, not dimensions: halving, thirds, flips and whole turns.
ALLOWED = {0, 1, 2, 3, 4, 0.5, 90, 180, 360}


@pytest.mark.parametrize("path", PARTS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_no_magic_numbers_in_model_functions(path):
    # Every dimension is a named parameter: in Params, or a named module constant.
    tree = ast.parse(path.read_text(encoding="utf-8"))
    magic = [
        f"line {node.lineno}: {node.value}"
        for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef)
        for node in ast.walk(fn)
        if isinstance(node, ast.Constant)
        and type(node.value) in (int, float)
        and node.value not in ALLOWED
    ]
    assert not magic, magic
