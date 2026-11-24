# Bambu Studio CLI slicing, and starting the print from the phone

Question: how printlab could, as an opt-in step, produce a sliced Bambu Studio file (`.gcode.3mf`) that the user starts from Bambu Handy on the X1C, without agents entering credentials or sending anything to the printer. Researched 2026-11-20. Nothing was sliced and the printer was not touched.

Sources are primary unless marked. Source-code line numbers refer to tag `v02.09.01.70` of [bambulab/BambuStudio](https://github.com/bambulab/BambuStudio/tree/v02.09.01.70), the version installed here.

## Summary

- The CLI is the GUI's own binary. It slices STL (not STEP), writes a `.gcode.3mf` and reports time and grams. It needs **fully resolved** machine, process and filament JSON files. The partial preset files Bambu ships, and the ones printlab writes, are not enough.
- A fully resolved machine file contains the X1C start and end G-code. Whoever writes that file controls the start G-code, which is exactly what ADR 0002 forbids agents to write. Opting in needs an ADR. The config must be generated mechanically from Bambu's own files and checked against them byte for byte.
- The lead script (`slice_check.py`) gets this wrong in a way that matters on this machine: it ignores the `include` key, so the X1C gets the generic start G-code from `fdm_machine_common`.
- Bambu Handy cannot open a local file, and it does not work in LAN-only or Developer mode. To start a file from the phone, the file must already be on the printer's storage or in the cloud print history, and putting it there is a network send. That send stays the user's job.
- **Recommended route:** the agent writes `parts/<name>/out/<part>.gcode.3mf` and stops. The user opens it in Bambu Studio, checks the toolpath preview, and clicks **Send** (to the printer's microSD card over LAN). Later, on the phone: Handy → device → Files → the file → Print. The X1C stays in normal cloud mode. Copying the file to the microSD card by hand works too, and then the print is started on the printer's screen.

## 1. The command line on Windows

### This machine

| Item | Value | Evidence |
|---|---|---|
| Install | `G:\bambu studio\` (not `C:\Program Files\`) | uninstall registry entry: `DisplayIcon = G:\bambu studio\bambu-studio.exe` |
| Version | 02.09.01.70 | registry `DisplayVersion`; the current release on [GitHub releases](https://github.com/bambulab/BambuStudio/releases/tag/v02.09.01.70) (2026-11-03) |
| Executable | `G:\bambu studio\bambu-studio.exe`, a small launcher that loads `BambuStudio.dll` and calls `bambustu_main` | `src/BambuStudio_app_msvc.cpp` L189-294 |
| Profiles shipped | `G:\bambu studio\resources\profiles\BBL\` with `BBL.json` version 02.09.00.74 | file |
| Profiles the GUI uses | `%APPDATA%\BambuStudio\system\BBL\`, version **02.09.00.83** (updated over the air) | file |
| User presets | `%APPDATA%\BambuStudio\user\<account id>\{process,filament}\`, among them the user's own `Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle.json` (158 keys, `"from": "User"`, `inherits` empty, so already fully resolved) | files |

The two profile sets differ. `Bambu Lab X1 Carbon 0.4 nozzle template machine_start_gcode.json` has different SHA-256 hashes in the install folder and in `%APPDATA%`. A script that reads the install folder slices with older start G-code than the GUI does. Read `%APPDATA%\BambuStudio\system\BBL` to match a hand slice.

### Flags (from `src/libslic3r/PrintConfig.cpp`, `CLIActionsConfigDef` / `CLITransformConfigDef` / `CLIMiscConfigDef`, L10935-11436, and the official [Command Line Usage wiki](https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage), last edited 2026-03-31)

| Flag | Meaning |
|---|---|
| `--load-settings "machine.json;process.json"` | at most one machine file and one process file |
| `--load-filaments "f1.json;..."` | one file per filament slot |
| `--slice 0` | slice all plates (`i` = plate i only) |
| `--export-3mf out.3mf` + `--outputdir dir` | write the project; after `--slice`, it carries the G-code |
| `--orient 0/1`, `--arrange 0/1`, `--ensure-on-bed` | placement |
| `--curr-bed-type "Textured PEI Plate"` style `--key=value` | overrides with the highest priority (wiki) |
| `--no-check` | skips validity checks such as G-code path conflicts. **Never use it.** |
| `--skip-modified-gcodes` | "Skip the modified gcodes in 3mf from Printer or filament Presets". With a 3MF input, edited G-code keys are reset to the system values (`BambuStudio.cpp` L3535-3540: "gcodes %1% modified, reset to default.") |
| `--export-settings f.json` | dumps the resolved config the CLI used (L6793) |
| `--debug 0-5`, `--pipe` | logging, progress |

Inputs: `Model::read_from_file` accepts `.stl`, `.obj`, `.amf`, `.3mf`, `.gltf/.glb`, `.fbx` (`src/libslic3r/Model.cpp` L339-458). **It does not accept STEP**, so printlab hands the CLI its STL. A Bambu `.3mf` must come first in the file list (`CLI_FILELIST_INVALID_ORDER`, L2077). Further model files may follow it, but that was not tested, and a forum user reported a crash with 2.04 on macOS ([thread](https://forum.bambulab.com/t/add-stl-step-file-to-a-3mf-from-the-command-line/221244), no staff reply).

Example command, adapted from the wiki's "Slice stls" row. The paths are illustrative.

```
"G:\bambu studio\bambu-studio.exe" --orient 0 --arrange 1 --load-settings "machine.json;process.json" --load-filaments "filament.json" --slice 0 --export-3mf part.gcode.3mf --outputdir out part.stl
```

### Profile files: the main pitfall

- The wiki says plainly that the files "should be a full config instead of the one used in resources/profiles/BBL/…", and it links example files. The official examples (`machine.json`, `process.json`, `filament.json`, downloaded from the wiki attachments) have 110 to 190 keys, keep `"from": "system"`, `inherits` and `include` as labels, and **contain the full `machine_start_gcode` text inline**.
- How the CLI loads a file: `load_from_json` reads only the keys in the file. It does not follow `inherits` or `include` (`src/libslic3r/Config.cpp` L987-992 store them as labels only). `from` must be `system`, `User` or `user`, or the CLI exits with `CLI_CONFIG_FILE_ERROR` (`BambuStudio.cpp` L2487-2491). Only the keys present are copied into the print config (`update_full_config`, L3528-3590). So **a partial preset silently falls back to the slicer's built-in defaults** for every missing key. Those defaults are not the X1C system values.
- Missing G-code keys become empty strings. `load_default_gcodes_to_config` (L729-788) creates `machine_start_gcode`, `machine_end_gcode`, `layer_change_gcode`, `time_lapse_gcode` and the rest as empty strings when they are absent. A machine file without start G-code therefore slices without error and produces a file with **no X1C start sequence**.
- How the GUI resolves a preset (`src/libslic3r/PresetBundle.cpp` L6390-6462): it starts from the fully resolved parent named in `inherits`, then applies each `include` file (only the keys that differ from defaults), then the file's own keys. On the X1C, `machine_start_gcode` exists **only** in the included file `Bambu Lab X1 Carbon 0.4 nozzle template machine_start_gcode.json`. The next value up the `inherits` chain is the generic one in `fdm_machine_common.json` (`G28`, `G29`, ...), which is not the X1C sequence. Thirty machine files in the BBL folder use `include`.
- Two more keys the GUI fills in: `printer_settings_id`, `print_settings_id` and `filament_settings_id` should be the preset names. The CLI sets the first two itself (L2563, L2602).
- `printer_model_id` (e.g. `BL-P001` for the X1C) is read from `resources/profiles/BBL/machine_full/<model>.json` (L2564-2575). That folder **is not in a desktop install**: `BBL\` holds only `filament`, `machine` and `process`. The id is then left out of the plate metadata (L8104). This was inferred from source and not tested. Check whether Studio or the printer warns about a printer mismatch on a test file.
- Version gate: a 3MF made by a newer minor version is refused unless `--allow-newer-file` is given (L2088-2090).
- On Linux Flatpak and AppImage builds, users reported `--load-settings` being ignored or "Invalid option" ([forum](https://forum.bambulab.com/t/cli-cannot-apply-external-presets/197842), no staff reply). Those reports do not cover Windows; they are a reason to check the output's resolved config rather than trust the input.

### The lead: `slice_check.py` (KvashaIhor/print-studio)

It flattens `inherits` (parent first, child wins), sets `from: system` and the `*_settings_id` keys, writes `_machine/_process/_filament.json` and runs the command above. It parses `Metadata/slice_info.config` for `prediction` (seconds) and `weight` (grams).

The flags and the output parsing are confirmed against source. The flattening is **unsafe for the X1C**:

- it ignores `include`, so the X1C start, end, layer-change, time-lapse and filament-change G-code come from the generic parents;
- it reads a configured profile folder; if that is the install folder, the profiles are older than the GUI's;
- its support-gram estimate assumes PLA density.

Do not copy it as it is.

### Reading time and grams

- `<outputdir>/result.json`, written by the CLI on every exit (`record_exit_reson`, L494-629), holds `return_code`, `error_string`, and per plate `total_predication` (seconds), `warning_message` and object bounding boxes.
- In the `.gcode.3mf` (a zip file): `Metadata/slice_info.config` has plate attributes `prediction` and `weight` (`src/libslic3r/Format/bbs_3mf.cpp` L372-373). The archive also holds `Metadata/plate_1.gcode` plus `plate_1.gcode.md5` (L7199), `Metadata/project_settings.config` (the resolved config that was actually used) and `plate_1.png`.

## 2. Routes from the file to a print started on the phone

Facts that limit every route:

- Handy has no LAN mode. "Bambu Handy does not currently support printer LAN mode and must use the Internet to connect to the printer" ([Handy quick start](https://wiki.bambulab.com/en/studio-handy/handy/bambu-handy-quick-start), updated 2026-08-25). Developer Mode works "exclusively … in LAN Mode" and "will not allow the printer to be connected to Bambu Cloud" ([Third-party integration](https://wiki.bambulab.com/en/software/third-party-integration), updated 2026-03-18). **A phone start needs the printer bound to the user's account in normal cloud mode.**
- Authorization Control (X1 firmware 01.08.05.00, 2025-03-12, [release history](https://wiki.bambulab.com/en/x1/manual/X1-X1C-firmware-release-history)) rejects control commands from unauthorized software, including starting a print over LAN or cloud from anything but Bambu Studio, Handy or Bambu Connect. **Starting prints from an SD card is explicitly unaffected** (third-party integration page). The X1 firmware is now at 01.12.01.00 (2026-10-21). Note 01.12.00.00 fixed a false nozzle-type-mismatch report "when starting a print via sliced files store in machine's memory", which shows the firmware checks a stored file's nozzle type against the installed nozzle.
- Handy cannot import or slice a local file. The official quick start lists printing from MakerWorld, from Print History, and **Files** ("access and manage files stored on your printer's internal or connected storage, including model files"). No official page found says Handy opens a `.3mf` from the phone.

| # | Route | Needs | Agent may do | Must stay the user's |
|---|---|---|---|---|
| A | **Studio "Send" to microSD card, then Handy → Files → Print** | cloud-bound printer; PC and printer on the same LAN; Studio's network plug-in | write the `.gcode.3mf` | open it in Studio (it opens in preview-only mode, and Send "send[s] the original file directly, no re-export/validation", `src/slic3r/GUI/Jobs/SendJob.cpp` L166-167), click Send; start it on the phone. Starting from Handy Files is backed by the official Files description and a 2023 user report ([forum](https://forum.bambulab.com/t/start-prints-from-sd-card-built-in-memory-from-handy-app/21030), disputed by a P1S owner). **Verify once on the user's phone.** |
| B | Copy the file to the microSD card by hand, then the printer screen → Print Files → SD Card | a card reader | write the file to `out/` | move the card, start the print (official [Studio quick start](https://wiki.bambulab.com/en/software/bambu-studio/studio-quick-start), "Export plate sliced file"). The phone can then start it via route A's Files step. |
| C | Studio "Print" through the cloud, then later reprints from Handy → Print History | Bambu account and cloud sync ("required to enable print history which allows you to reprint your history models on the Bambu Handy app", Studio quick start) | write the file | the first start happens on the PC. Only reprints happen on the phone. |
| D | Bambu Connect: import the `.gcode.3mf`, send it to the printer | Windows app; account sign-in for cloud printers (its feature list starts with "Cloud Account Login"); Bambu says LAN mode through Connect needs no account ([blog, 2025-01-20](https://blog.bambulab.com/updates-and-third-party-integration-with-bambu-connect)) | nothing. Opening the `bambu-connect://import-file?path=…` URL scheme is the first step of a send, so an agent must not call it either. | the import and the send. This offers nothing over route A for a user who already has Studio. |
| E | FTPS upload to the printer's card (port 990, LAN access code) | LAN access code. Developer Mode leaves "MQTT channel, live stream, and FTP open" (blog) | **no**: it needs a credential and is a network send to the printer | all of it. Not recommended. |
| F | MakerWorld upload / draft, then print from Handy | account; MakerWorld re-slices uploads with its cloud CLI (the `machine_full` profiles and the "before uploading" CLI error strings, L129-176, point to this) | no | all of it. Not verified here, and the file printed would not be the one printlab checked. Not recommended. |

**Recommended: route A.** It keeps the printer in its normal cloud mode, needs no new software, and makes the user look at the real toolpath preview before anything reaches the printer. It also puts the file on the card, so the actual start can wait for the phone. Route B is the fallback when the LAN send fails.

All routes still need one desktop or physical step by the user. A start from the phone alone is impossible unless the file is already on the printer or in the cloud, and putting it there is the send that agents must not do.

## 3. Safety: what in a sliced file comes from where

In a `.gcode.3mf` sliced by the CLI, every value comes from the three JSON files handed to it plus `--key=value` overrides. Bambu's ownership of a value lasts only as long as those files are faithful copies of Bambu's.

| In the G-code | Comes from | Example on the X1C |
|---|---|---|
| Start sequence (homing, bed and nozzle heat-up, wipe, ABL, flow calibration, AMS load, runout detection) | machine `machine_start_gcode`, from the include template (631 lines, dated 20251031) | `M140/M190 S[bed_temperature_initial_layer_single]`, `M104/M109 S[nozzle_temperature_initial_layer]`, `G28`, `M412 S1` |
| End, layer-change, time-lapse and filament-change G-code | machine templates and `fdm_bbl_3dp_001_common` | |
| Temperatures substituted into the placeholders above | filament preset (`nozzle_temperature*`, plate temperatures for each plate type, chamber) | the user's Overture preset: nozzle 245, `hot_plate_temp` 70 |
| Bed area, excluded areas, height, kinematic limits | machine preset (`printable_area`, `bed_exclude_area`, `machine_max_*`) | the CLI has an error for changed printable area, height or excluded areas (`CLI_MODIFIED_PARAMS_TO_PRINTER`, L150). When it fires was not traced. |
| Toolpath: layers, walls, infill, speeds, accelerations, supports, brim, print sequence | process preset, which is **what printlab writes** (ADR 0002) | |

Process keys that matter for safety:

- Process presets contain no G-code keys. G-code keys live only in machine and filament profiles: `fdm_machine_common.json` has `machine_start_gcode`, `machine_end_gcode` and `change_filament_gcode`; `fdm_filament_common.json` has `filament_start_gcode` and `filament_end_gcode`.
- **The process preset does carry `post_process`**, a list of scripts the GUI runs on the G-code (`PrintConfig.cpp` L5417). The CLI rejects it only for 3MF inputs under the normative check (`BambuStudio.cpp` L2130-2139), not in a `--load-settings` file. printlab's preset check should reject `post_process`, `filename_format` and any key ending in `_gcode` outright.
- `print_sequence = by object` risks the toolhead hitting earlier objects. The CLI checks this (`CLI_OBJECT_COLLISION_IN_SEQ_PRINT`).

Checks the CLI itself runs, which exit non-zero and are recorded in `result.json`:

- objects partly outside the bed (L7013);
- toolpath conflicts (L7670-7674);
- G-code outside the printable area (L7752-7764);
- filament incompatible with the plate type;
- filaments with too large a temperature difference;
- sequential-print collisions;
- spiral-mode conflicts.

`--no-check` turns the path checks off (L6851). The area checks use the bed from the machine file they are given, so they are only as good as that file.

Checks the firmware or Studio run: the 3MF carries an MD5 of each plate's G-code. Firmware 01.12.00.00 shows the printer checks the nozzle type against a stored file. Opened in Studio, a `.gcode.3mf` is sent unchanged, without re-validation (`SendJob.cpp` L166). No primary source found describes firmware-side G-code range checks. The heater limits are the printer's own and were not researched here.

Weighing the risk ADR 0001 cites: if the machine and filament files are byte-for-byte resolutions of Bambu's `%APPDATA%` system profiles and the user's own filament preset, then the start and end G-code and the temperatures are the same as a hand slice in the GUI. The agent then controls only the process keys ADR 0002 already allows and the model's placement on the bed. The remaining risk is a resolver bug like `slice_check.py`'s, which produces wrong start G-code silently, with a clean exit.

Checks that would make that risk testable:

1. Resolve `inherits` and `include` exactly as `PresetBundle.cpp` L6390-6462 does: parent, then includes (differences from defaults only), then own keys. Read from `%APPDATA%\BambuStudio\system\BBL`. Use the user's filament preset file unchanged.
2. After slicing, open `Metadata/project_settings.config` in the output and assert that every key in the CLI's G-code key set (`BambuStudio.cpp` L726-727) equals the system template text exactly, that the temperature keys equal the filament preset, and that `printable_area` and `bed_exclude_area` equal the system machine profile.
3. Require `result.json` `return_code == 0` and no `--no-check`.
4. The user still opens the file in Studio's preview before sending (route A).

These checks are still automated, and ADR 0001 notes that automated checks "have already proven fallible here". Route A keeps the user's look at the preview as the final gate.

## Open items to verify once by hand

- That Handy → device → Files can start a `.gcode.3mf` the user sent to the X1C's card, on the user's app version.
- Whether a CLI-sliced file without `printer_model_id` triggers a printer-mismatch warning in Studio or on the printer.
- Whether `--export-3mf` with an STL input works on 02.09.01.70 on Windows. This needs one supervised run by the user, which this research did not do.
  - Checked 2026-11-21 (#30): it works. The user's filament preset has no `type` key (Studio takes it from the folder), and without one the CLI stops with return code -5, "The input preset file is invalid and can not be parsed". printlab adds only that label; every setting stays byte for byte. The output trims the per-AMS `filament_dev_*` drying lists to one value.
