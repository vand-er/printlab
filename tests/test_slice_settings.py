"""A part's print.md names its slice settings in one fenced `slice` block."""

from pathlib import Path

import pytest

from printlab.parts import PARTS_DIR
from printlab.slice_settings import SliceSettingsError, read_slice_settings

BLOCK = """\
```slice
process: 0.20mm Standard @BBL X1C
filament: Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle
plate: Textured PEI Plate
stl: out/box.stl
```
"""


def write_part(parts_dir: Path, name: str, print_md: str | None) -> Path:
    part = parts_dir / name
    part.mkdir(parents=True)
    (part / "model.py").write_text("", encoding="utf-8")
    if print_md is not None:
        (part / "print.md").write_text(print_md, encoding="utf-8")
    return part


def test_reads_process_filament_plate_and_petg_stl(tmp_path):
    part = write_part(tmp_path, "box", f"# Box\n\n## Print\n\n- **Preset:** whatever.\n\n{BLOCK}")
    s = read_slice_settings("box", parts_dir=tmp_path)
    assert s.process == "0.20mm Standard @BBL X1C"
    assert s.filament == "Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle"
    assert s.plate == "Textured PEI Plate"
    assert s.stl == part / "out" / "box.stl"


def reason(parts_dir: Path, name: str) -> str:
    with pytest.raises(SliceSettingsError) as e:
        read_slice_settings(name, parts_dir=parts_dir)
    return str(e.value)


def test_a_part_without_print_md_cannot_be_sliced(tmp_path):
    write_part(tmp_path, "box", None)
    msg = reason(tmp_path, "box")
    assert "box" in msg and "print.md" in msg


def test_a_print_md_without_the_block_names_the_part_and_the_block(tmp_path):
    write_part(tmp_path, "box", "# Box\n\n- **Preset:** system process `0.20mm Standard @BBL X1C`.\n")
    msg = reason(tmp_path, "box")
    assert "box" in msg and "```slice" in msg


def test_a_block_missing_a_setting_names_the_setting(tmp_path):
    write_part(tmp_path, "box", BLOCK.replace("plate: Textured PEI Plate\n", ""))
    msg = reason(tmp_path, "box")
    assert "box" in msg and "plate" in msg
    assert "filament" not in msg


def test_a_misspelt_key_is_refused(tmp_path):
    write_part(tmp_path, "box", BLOCK.replace("filament:", "filamnet:"))
    assert "filamnet" in reason(tmp_path, "box")


PRINTED = sorted(p.parent.name for p in PARTS_DIR.glob("*/print.md"))


@pytest.mark.parametrize("name", PRINTED)
def test_every_print_md_names_its_slice_settings(name):
    s = read_slice_settings(name)
    assert s.stl.is_file(), s.stl
    assert "labels" not in s.stl.name  # the PETG STL only, never a second filament's
    if s.process.startswith("presets/"):
        assert (PARTS_DIR.parent / s.process).is_file(), s.process


def test_parts_with_print_md_exist():
    assert {"clamp", "clamp-pin-strip"} <= set(PRINTED)
