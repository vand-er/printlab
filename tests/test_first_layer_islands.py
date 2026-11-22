"""--slice-check reports the first-layer islands the real slicer extrudes, each named by its body."""

import json
import re
from types import SimpleNamespace

import pytest
from build123d import Box, Pos

from printlab import cli, islands, profiles, slicing

FILAMENT = "Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle"
SLICE_BLOCK = """
```slice
process: {process}
filament: {filament}
plate: Textured PEI Plate
stl: out/{name}.stl
```
"""
ISLAND = re.compile(r"^ +layer (\d+) island \d+: (.+), ([\d.]+) mm² at x (-?[\d.]+), y (-?[\d.]+)$")


def _bambu_ready() -> bool:
    try:
        slicing.bambu_studio()
        slicing.filament_preset(FILAMENT)
    except slicing.SliceError:
        return False
    return profiles.SYSTEM.is_dir()


# Every test here runs the real slicer: slow, and skipped where Bambu Studio is not set up.
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not _bambu_ready(), reason="Bambu Studio, its profiles or the preset absent"),
]


@pytest.fixture
def part(tmp_path, monkeypatch):
    """A fake part 'boxes' whose build() returns the given named bodies."""

    def use(bodies, process="0.20mm Standard @BBL X1C"):
        folder = tmp_path / "parts" / "boxes"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "print.md").write_text(
            SLICE_BLOCK.format(process=process, filament=FILAMENT, name="boxes"), encoding="utf-8"
        )
        monkeypatch.setattr(cli, "PARTS_DIR", tmp_path / "parts")
        monkeypatch.setattr(cli, "part_names", lambda: ["boxes"])
        monkeypatch.setattr(cli, "load_part", lambda _: SimpleNamespace(build=lambda: bodies))

    return use


@pytest.fixture
def brim_on(tmp_path, monkeypatch):
    """A process preset in presets/ that puts a 5 mm brim round every body, 1 mm clear of it."""
    presets = tmp_path / "presets"
    presets.mkdir()
    preset = {"type": "process", "name": "brim on", "inherits": "0.20mm Standard @BBL X1C",
              "brim_type": "outer_only", "brim_width": "5", "brim_object_gap": "1"}  # fmt: skip
    (presets / "brim on.json").write_text(json.dumps(preset), encoding="utf-8")
    monkeypatch.setattr(slicing, "PRESETS_DIR", presets)
    return "brim on"


def _islands(out: str) -> list[tuple[int, str, float, float, float]]:
    found = [ISLAND.match(line) for line in out.splitlines()]
    return [(int(m[1]), m[2], float(m[3]), float(m[4]), float(m[5])) for m in found if m]


def _box(x: float, y: float, z: float, at: tuple[float, float]):
    return Pos(at[0], at[1], z / 2) * Box(x, y, z)


def test_two_boxes_give_two_islands_of_their_footprints_named_by_body(part, capsys):
    part({"Big": _box(20, 20, 4, (0, 0)), "Long": _box(30, 15, 4, (40, 5))})

    assert cli.main(["build", "boxes", "--slice-check"]) == 0
    first = [i for i in _islands(capsys.readouterr().out) if i[0] == 1]
    assert sorted(i[1] for i in first) == ["Big", "Long"]
    for _, body, area, x, y in first:
        footprint, centre = {"Big": (400, (0, 0)), "Long": (450, (40, 5))}[body]
        assert area == pytest.approx(footprint, rel=0.05), body
        assert (x, y) == pytest.approx(centre, abs=0.5), body


def test_a_box_with_brim_is_one_island_that_includes_the_brim(part, brim_on, capsys):
    part({"Big": _box(20, 20, 4, (0, 0))}, process=brim_on)

    assert cli.main(["build", "boxes", "--slice-check"]) == 0
    first = [i for i in _islands(capsys.readouterr().out) if i[0] == 1]
    assert [i[1] for i in first] == ["Big"]
    # The box is 400 mm²; a 5 mm brim 1 mm out adds about (20 + 2 * 6)² - (20 + 2 * 1)² = 540 mm² more.
    assert first[0][2] > 400 + 0.8 * 540


@pytest.fixture
def two_parts(tmp_path, monkeypatch):
    """Fake parts by name, each a dict of named bodies, sliced the same way."""

    def use(parts):
        for name in parts:
            folder = tmp_path / "parts" / name
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "print.md").write_text(
                SLICE_BLOCK.format(process="0.20mm Standard @BBL X1C", filament=FILAMENT, name=name),
                encoding="utf-8",
            )
        monkeypatch.setattr(cli, "PARTS_DIR", tmp_path / "parts")
        monkeypatch.setattr(cli, "part_names", lambda: sorted(parts))
        monkeypatch.setattr(cli, "load_part", lambda name: SimpleNamespace(build=lambda: parts[name]))

    return use


def test_a_part_smaller_than_its_reference_print_warns_naming_its_body(two_parts, capsys):
    two_parts({"big": {"Big": _box(20, 20, 4, (0, 0))}, "small": {"Small": _box(8, 8, 4, (0, 0))}})
    assert cli.main(["build", "big"]) == 0  # the reference print's STL

    assert cli.main(["build", "small", "--slice-check", "--reference", "big"]) == 0
    err = capsys.readouterr().err
    warning = re.search(r"^WARN small: layer 1 Small: ([\d.]+) mm², below big's ([\d.]+) mm²$", err, re.M)
    assert warning, err
    assert float(warning[1]) == pytest.approx(64, rel=0.1)
    assert float(warning[2]) == pytest.approx(400, rel=0.05)


@pytest.mark.parametrize("first_layers", [1, 2])
def test_first_layers_sets_how_many_layers_are_reported(part, monkeypatch, capsys, first_layers):
    monkeypatch.setattr(islands, "FIRST_LAYERS", first_layers)
    part({"Big": _box(20, 20, 4, (0, 0))})

    assert cli.main(["build", "boxes", "--slice-check"]) == 0
    assert sorted({i[0] for i in _islands(capsys.readouterr().out)}) == list(range(1, first_layers + 1))
