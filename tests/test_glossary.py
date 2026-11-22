"""Code names use GLOSSARY.md's terms, never the words it lists under _Avoid_."""

import ast
import io
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).parent.parent

# _Avoid_ words spec #10 itself uses in another sense: the Latch's hook arm, the collar's
# ring wall, the brass base, joints between bodies.
ALLOWED = {"arm", "ring", "base", "joint"}
# Pipeline modules name rendering and files, not the domain.
# _Avoid_ words prose uses in another sense: the kernel's modelling tolerances, the hole-gauge
# part's name, the pod's glass tank.
PROSE_ALLOWED = {"tolerances", "gauge", "tank"}
NOT_DOMAIN = {"checks.py", "export.py", "cli.py", "nudge.py", "parts.py", "font.py"}


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


def prose(path: Path) -> str:
    """A part's print.md whole, or a module's docstrings and comments."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        return text
    chunks = [tok.string for tok in tokenize.generate_tokens(io.StringIO(text).readline)
              if tok.type == tokenize.COMMENT]
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            chunks.append(ast.get_docstring(node) or "")
    return "\n".join(chunks)


def test_no_prose_uses_an_avoided_glossary_word():
    terms = {t for t in avoided_terms() if " ".join(t) not in PROSE_ALLOWED}
    found = []
    src = [p for p in ROOT.glob("src/printlab/*.py") if p.name not in NOT_DOMAIN]
    for path in sorted([*src, *ROOT.glob("parts/*/*.py"), *ROOT.glob("parts/*/print.md")]):
        parts = [w.lower() for w in re.findall(r"[A-Za-z]+", prose(path))]
        for term in terms:
            n = len(term)
            if any(tuple(parts[i : i + n]) == term for i in range(len(parts) - n + 1)):
                found.append(f"{path.relative_to(ROOT)}: {' '.join(term)}")
    assert not found, sorted(set(found))
