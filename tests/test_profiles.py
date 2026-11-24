"""The profile resolver gives Bambu's X1C settings as Bambu Studio resolves them (ADR 0004)."""

import json

import pytest

from printlab import profiles

BBL = profiles.SYSTEM
X1C = "Bambu Lab X1 Carbon 0.4 nozzle"

installed = pytest.mark.skipif(not BBL.is_dir(), reason="Bambu Studio system profiles not installed")


def test_filament_preset_is_found_by_name_under_the_user_s_folder(tmp_path):
    preset = tmp_path / "80784227" / "filament" / "base" / "Overture PETG.json"
    preset.parent.mkdir(parents=True)
    preset.write_text("{}", encoding="utf-8")
    assert profiles.filament_preset("Overture PETG", root=tmp_path) == preset
    with pytest.raises(profiles.ProfileError, match="'Other' not found"):
        profiles.filament_preset("Other", root=tmp_path)


def test_missing_profile_names_the_file_it_looked_for(tmp_path):
    with pytest.raises(profiles.ProfileError, match="nowhere.json"):
        profiles.resolve("machine", "nowhere", root=tmp_path)


def _file(kind: str, name: str) -> dict:
    return json.loads((BBL / kind / f"{name}.json").read_text(encoding="utf-8"))


@installed
def test_x1c_gets_its_own_start_gcode_from_the_include_template():
    machine = profiles.resolve("machine", X1C)
    template = _file("machine", f"{X1C} template machine_start_gcode")
    generic = _file("machine", "fdm_machine_common")
    assert machine["machine_start_gcode"] == template["machine_start_gcode"]
    assert machine["machine_start_gcode"] != generic["machine_start_gcode"]


@installed
def test_process_profile_holds_its_whole_inherits_chain_with_the_child_winning():
    name = "0.20mm Standard @BBL X1C"
    process = profiles.resolve("process", name)
    chain = [name, "fdm_process_single_0.20", "fdm_process_single_common", "fdm_process_common"]
    for link in chain:
        assert _file("process", link).keys() <= process.keys(), link
    assert process["travel_speed"] == ["500", "500"]  # fdm_process_common has "400"
    assert process["layer_height"] == "0.2"  # only in fdm_process_common
    assert process["from"] == "system"
    assert process["print_settings_id"] == name


@installed
def test_machine_profile_names_itself_for_the_command_line():
    machine = profiles.resolve("machine", X1C)
    assert machine["from"] == "system"
    assert machine["printer_settings_id"] == X1C
