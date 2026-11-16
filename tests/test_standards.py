"""Mechanical coding standards, checked over every part's source."""

import ast
from pathlib import Path

import pytest

PARTS = sorted(Path(__file__).parent.parent.glob("parts/*/model.py"))

# Literals that are geometry, not dimensions: halving, thirds, flips and whole turns.
ALLOWED = {0, 1, 2, 3, 0.5, 90, 180, 360}


@pytest.mark.parametrize("path", PARTS, ids=lambda p: p.parent.name)
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
