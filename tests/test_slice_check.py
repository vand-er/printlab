"""printlab build <part> --slice-check slices with the real Bambu Studio command line (ADR 0004)."""

import json
import tempfile
from types import SimpleNamespace

import pytest
from build123d import Box, Part, Pos

from printlab import cli, profiles, slicing

SLICE_BLOCK = """
```slice
process: {process}
filament: Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle
plate: Textured PEI Plate
stl: out/{name}.stl
```
"""


@pytest.fixture
def slice_part(tmp_path, monkeypatch):
    """A fake part with a print.md that names how to slice it."""

    def use(build=lambda: Box(10, 10, 10), name="cube", process="0.20mm Standard @BBL X1C"):
        part = SimpleNamespace(build=build)
        parts = tmp_path / "parts"
        (parts / name).mkdir(parents=True, exist_ok=True)
        (parts / name / "print.md").write_text(
            SLICE_BLOCK.format(process=process, name=name), encoding="utf-8"
        )
        monkeypatch.setattr(cli, "PARTS_DIR", parts)
        monkeypatch.setattr(cli, "part_names", lambda: [name])
        monkeypatch.setattr(cli, "load_part", lambda _: part)
        return parts / name

    return use


def _bambu_ready() -> bool:
    try:
        slicing.bambu_studio()
        slicing.filament_preset("Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle")
    except slicing.SliceError:
        return False
    return profiles.SYSTEM.is_dir()


def real_slicer(test):
    """Runs the real slicer: slow, and skipped where Bambu Studio is not set up."""
    absent = pytest.mark.skipif(not _bambu_ready(), reason="Bambu Studio, its profiles or the preset absent")
    return pytest.mark.slow(absent(test))


@pytest.fixture
def temp_dir(tmp_path, monkeypatch):
    """Where the slicer's temp folders go, so a test can see that none is left behind."""
    folder = tmp_path / "temp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def _lines(out: str) -> dict[str, str]:
    return dict(line.strip().split(": ", 1) for line in out.splitlines() if ": " in line)


@real_slicer
def test_slice_check_reports_grams_and_time_and_keeps_nothing(slice_part, temp_dir, capsys):
    folder = slice_part()

    assert cli.main(["build", "cube", "--slice-check"]) == 0
    out = _lines(capsys.readouterr().out)
    assert float(out["sliced grams"].removesuffix(" g")) > 0
    assert int(out["sliced time"].split()[0]) > 0
    assert not [p for p in folder.rglob("*") if p.name.endswith((".3mf", ".gcode", ".json"))]
    assert list(temp_dir.iterdir()) == []


@real_slicer
def test_a_tampered_resolved_profile_fails_the_build_and_keeps_nothing(
    slice_part, temp_dir, monkeypatch, capsys
):
    folder = slice_part()
    resolve = profiles.resolve

    def tampered(kind, name, **kw):
        settings = resolve(kind, name, **kw)
        if kind == "machine":
            settings["machine_start_gcode"] += "\nM104 S300\n"
        return settings

    monkeypatch.setattr(profiles, "resolve", tampered)

    assert cli.main(["build", "cube", "--slice-check"]) != 0
    err = capsys.readouterr().err
    assert err.startswith("FAIL cube: ") and "machine_start_gcode" in err
    assert not [p for p in folder.rglob("*") if p.name.endswith((".3mf", ".gcode", ".json"))]
    assert list(temp_dir.iterdir()) == []


@pytest.fixture
def supports_on(tmp_path, monkeypatch):
    """A process preset in presets/ that turns supports on."""
    presets = tmp_path / "presets"
    presets.mkdir()
    preset = {"type": "process", "name": "supports on", "inherits": "0.20mm Standard @BBL X1C",
              "enable_support": "1"}  # fmt: skip
    (presets / "supports on.json").write_text(json.dumps(preset), encoding="utf-8")
    monkeypatch.setattr(slicing, "PRESETS_DIR", presets)
    return "supports on"


def _tee() -> Part:
    """A 10 mm post at the origin under a 40 mm bar at 20 mm: its two arms overhang by 15 mm in x."""
    post = Pos(0, 0, 10) * Box(10, 10, 20)
    return post + Pos(0, 0, 21.5) * Box(40, 10, 3)


@real_slicer
def test_supports_are_reported_where_an_overhang_needs_them(slice_part, supports_on, capsys):
    slice_part(build=_tee, process=supports_on)

    assert cli.main(["build", "cube", "--slice-check"]) == 0
    out = _lines(capsys.readouterr().out)
    regions = [v for k, v in out.items() if k.startswith("support ")]
    assert out["sliced supports"] == str(len(regions)) and regions
    for region in regions:
        x0, x1 = (float(v) for v in region.split(",")[0].removeprefix("x ").split(" to "))
        assert x1 <= -4 or x0 >= 4, f"support under the post: {region}"  # the post spans x -5 to 5


@real_slicer
def test_a_plain_box_reports_no_supports(slice_part, supports_on, capsys):
    slice_part(process=supports_on)

    assert cli.main(["build", "cube", "--slice-check"]) == 0
    assert _lines(capsys.readouterr().out)["sliced supports"] == "none"


def test_build_without_the_flag_never_slices(slice_part, monkeypatch):
    slice_part()
    calls = []
    monkeypatch.setattr(cli, "slice_part", lambda *a, **k: calls.append(a))

    assert cli.main(["build", "cube"]) == 0
    assert calls == []


def test_bambu_studio_missing_gives_one_fail_line(slice_part, monkeypatch, tmp_path, capsys):
    slice_part()
    monkeypatch.setenv("PRINTLAB_BAMBU_STUDIO", str(tmp_path / "nowhere" / "bambu-studio.exe"))

    assert cli.main(["build", "cube", "--slice-check"]) != 0
    err = capsys.readouterr().err.splitlines()
    assert len(err) == 1
    assert err[0].startswith("FAIL cube: Bambu Studio not found")
    assert "nowhere" in err[0]
