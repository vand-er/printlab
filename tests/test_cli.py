from types import SimpleNamespace

import pytest
from build123d import Box

from printlab import cli


@pytest.fixture
def cube_part(tmp_path, monkeypatch):
    """A fake part 'cube': 1 cm³, about 1.27 g of PETG."""

    def use(**module_attrs):
        part = SimpleNamespace(build=lambda: Box(10, 10, 10), **module_attrs)
        monkeypatch.setattr(cli, "PARTS_DIR", tmp_path / "parts")
        monkeypatch.setattr(cli, "part_names", lambda: ["cube"])
        monkeypatch.setattr(cli, "load_part", lambda name: part)

    return use


def test_build_warns_when_a_part_is_over_its_gram_budget(cube_part, capsys):
    cube_part(GRAM_BUDGET=1.0)

    assert cli.main(["build", "cube"]) == 0
    assert "WARN cube: about 1.3 g is over the 1 g budget" in capsys.readouterr().err


def test_build_prints_a_part_s_notes_on_its_bodies(cube_part, capsys):
    cube_part(notes=lambda bodies: [f"{len(bodies)} body"])

    assert cli.main(["build", "cube"]) == 0
    assert "   1 body\n" in capsys.readouterr().out


def test_build_is_quiet_within_budget_or_without_one(cube_part, capsys):
    cube_part(GRAM_BUDGET=2.0)
    assert cli.main(["build", "cube"]) == 0
    cube_part()
    assert cli.main(["build", "cube"]) == 0
    assert "WARN" not in capsys.readouterr().err
