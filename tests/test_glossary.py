"""Code names use GLOSSARY.md's terms, never the words it lists under _Avoid_."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

# _Avoid_ words spec #10 itself uses in another sense: the Latch's hook arm, the collar's
# ring wall, the brass base, joints between bodies.
ALLOWED = {"arm", "ring", "base", "joint"}
# Pipeline modules name rendering and files, not the domain.
NOT_DOMAIN = {"checks.py", "export.py", "cli.py", "nudge.py", "parts.py"}


def avoided_terms() -> set[tuple[str, ...]]:
    terms = set()
    for line in (ROOT / "GLOSSARY.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("_Avoid_:"):
            for term in line.removeprefix("_Avoid_:").split(","):
                words = tuple(term.lower().split())
                if words and " ".join(words) not in ALLOWED:
                    terms.add(words)
    return terms


def words(identifier: str) -> list[str]:
    """snake_case and CamelCase parts, lower-cased."""
    return [w.lower() for w in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", identifier)]


def identifiers(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.keyword) and node.arg:
            names.add(node.arg)
    return names


def test_no_identifier_uses_an_avoided_glossary_word():
    terms = avoided_terms()
    found = []
    src = [p for p in ROOT.glob("src/printlab/*.py") if p.name not in NOT_DOMAIN]
    for path in sorted([*src, *ROOT.glob("parts/*/*.py")]):
        for name in identifiers(path):
            parts = words(name)
            for term in terms:
                n = len(term)
                if any(tuple(parts[i : i + n]) == term for i in range(len(parts) - n + 1)):
                    found.append(f"{path.relative_to(ROOT)}: {name} ({' '.join(term)})")
    assert not found, sorted(found)
