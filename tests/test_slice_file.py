"""printlab build <part> --slice keeps a sliced file for the phone route (ADR 0004)."""

import subprocess
import tempfile
from types import SimpleNamespace

import pytest
from build123d import Box

from printlab import cli, profiles, slicing

FILAMENT = "Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle"
SLICE_BLOCK = f"""
```slice
process: 0.20mm Standard @BBL X1C
filament: {FILAMENT}
plate: Textured PEI Plate
stl: out/cube.stl
```
"""


@pytest.fixture
def cube(tmp_path, monkeypatch):
    """A fake 10 mm box part with a print.md that names how to slice it."""
    part = SimpleNamespace(build=lambda: Box(10, 10, 10))
    folder = tmp_path / "parts" / "cube"
    folder.mkdir(parents=True)
    (folder / "print.md").write_text(SLICE_BLOCK, encoding="utf-8")
    monkeypatch.setattr(cli, "PARTS_DIR", folder.parent)
    monkeypatch.setattr(cli, "part_names", lambda: ["cube"])
    monkeypatch.setattr(cli, "load_part", lambda _: part)
    return folder


@pytest.fixture
def temp_dir(tmp_path, monkeypatch):
    """Where the slicer's temp folders go, so a test can see that none is left behind."""
    folder = tmp_path / "temp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def _bambu_ready() -> bool:
    try:
        slicing.bambu_studio()
        slicing.filament_preset(FILAMENT)
    except slicing.SliceError:
        return False
    return profiles.SYSTEM.is_dir()


def real_slicer(test):
    """Runs the real slicer: slow, and skipped where Bambu Studio is not set up."""
    absent = pytest.mark.skipif(not _bambu_ready(), reason="Bambu Studio, its profiles or the preset absent")
    return pytest.mark.slow(absent(test))


def _sliced(folder):
    return [p for p in folder.rglob("*") if p.name.endswith((".3mf", ".gcode"))]


def test_slice_and_slice_check_together_exit_with_a_clear_message(cube, capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["build", "cube", "--slice", "--slice-check"])

    assert exit_.value.code != 0
    err = capsys.readouterr().err
    assert "--slice" in err and "--slice-check" in err and "not allowed with" in err
    assert _sliced(cube) == []


@real_slicer
def test_slice_leaves_one_sliced_file_next_to_the_outputs(cube, temp_dir, capsys):
    assert cli.main(["build", "cube", "--slice"]) == 0

    assert _sliced(cube) == [cube / "out" / "cube.gcode.3mf"]
    assert list(temp_dir.iterdir()) == []
    assert "out/cube.gcode.3mf" in capsys.readouterr().out.replace("\\", "/")


@real_slicer
def test_a_tampered_profile_under_slice_leaves_no_sliced_file(cube, temp_dir, monkeypatch, capsys):
    resolve = profiles.resolve

    def tampered(kind, name, **kw):
        settings = resolve(kind, name, **kw)
        if kind == "machine":
            settings["machine_start_gcode"] += "\nM104 S300\n"
        return settings

    monkeypatch.setattr(profiles, "resolve", tampered)

    assert cli.main(["build", "cube", "--slice"]) != 0
    assert "machine_start_gcode" in capsys.readouterr().err
    assert _sliced(cube) == []
    assert list(temp_dir.iterdir()) == []


def test_a_sliced_file_in_a_parts_outputs_is_gitignored():
    check = subprocess.run(
        ["git", "check-ignore", "-q", "parts/clamp/out/clamp.gcode.3mf"], cwd=slicing.PRESETS_DIR.parent
    )
    assert check.returncode == 0
