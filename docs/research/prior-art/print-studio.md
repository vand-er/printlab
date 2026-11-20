# KvashaIhor/print-studio

A Claude Code skill (plugin) that designs, checks, renders and test-slices models for Bambu Lab printers. Reviewed at [`bda7005`](https://github.com/KvashaIhor/print-studio/tree/bda70052d8d9494ff5cec1d5b4eee3e3735eba33). Licence: MIT, so code could be copied with attribution, but the README rule here still applies: **ideas only**, in our own words.

## Verdict

Thoughtful and mostly correct, written by someone who has looked hard at their own output in Bambu Studio. Its checks fail loudly instead of warning and carrying on, and its overhang maths is the right way round (unlike [3dp-mcp-server](3dp-mcp-server.md)).

Three weaknesses:
- **Little evidence of functional prints.** Every figure in the README (times, grams) is a Bambu Studio estimate. The `proven` clearances record ships empty, and the config itself lists the clearances, hole allowance, minimum wall and bridge length as unconfirmed defaults (`defaults_used`).
- **One person, one printer (P1S), one OS (macOS).** Four commits in 21 minutes on 2026-11-02, then nothing; one star.
- **Its strength is organic meshes** (AI figurines, repair, lithophanes). The functional route is a short reference page and a template.

Review angles: code review, fact-check and provenance. It was not installed or run, as instructed.

## What printlab should take, by value

| # | Idea | printlab today | What would change |
|---|---|---|---|
| 1 | Hard-failing printability checks on the mesh | `check_part`: one solid, valid BRep, fits 256 × 256 × 250. `export_part`: STEP round-trip, watertight STL | Add wall thickness, overhang area, bed contact and tip-over to `checks.py`, split into blockers and warnings |
| 2 | Inspection sheet with every side, plus close-ups at a point | Five views: iso, front, side, top, top third | Add back, bottom and two three-quarter views; add a close-up around (X, Y, Z) and pixel-to-point picking |
| 3 | A fit record: default vs proven | One rule in `CLAUDE.md` (0.2 mm until `hole-gauge` is printed) | One file of fit values, each marked default or proven by a named print, read by every part |
| 4 | FDM feature helpers | None; `agent-cad-tooling.md` G7 proposes `bd_warehouse` | Cone-roof pockets, teardrop holes, bottom chamfer, insert, nut and countersink helpers, with corrected numbers |
| 5 | Slicer-side hole compensation (from the fact-check, not from print-studio) | Geometry offset only | Once `hole-gauge` is measured, put the offset in a process preset's `xy_hole_compensation` |
| 6 | Slice check: grams, time and where supports really go | Forbidden: ADR 0001 defers CLI slicing | Only with a new ADR: slice into a temp folder, read the numbers, deliver nothing from it |
| 7 | A lessons table | Spread across research notes | `docs/lessons.md`: tried, what happened, do instead |
| 8 | Function checks when inspecting | Ad hoc | A short review list: right way up, symmetric twins match, mating features line up |

### 1. Hard-failing printability checks (highest value)

Their mesh check ([`check_mesh.py`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/scripts/check_mesh.py)) exits 2 on a blocker, 1 on warnings and 0 when ready. The ideas worth having:
- **Wall thickness by stepping inward.** Sample points evenly over the surface, step each one a wall's depth inward along its normal, and test whether the point is still inside (they use a fast winding number from libigl). Points that land outside mark a wall thinner than the step. Thin points are binned into 4 mm cells and reported with coordinates, so you can render a close-up there. For printlab, run it at our 1.2 mm load-bearing minimum. Caveats: it only measures along the normal, and it is a sample, so a tiny thin spot can be missed. `trimesh`'s `contains` or `proximity.signed_distance` can do the inside test without adding libigl.
- **Overhang area.** It counts the downward-facing area steeper than 45° from vertical, leaves out the base, and allows a 0.5° slack so an exact 45° chamfer is not counted. The maths is correct. It warns above 5 % of the surface. That threshold is unsourced and too loose for a support-free functional part: printlab should fail on any overhang it did not mean to have.
- **Bed contact and tip-over.** Contact area is the area of downward faces at the lowest Z (it blocks below 20 mm²). Tip-over is a warning when the centre of mass falls outside the convex hull of that contact. This is cheap and useful for tall parts. The [build123d-mcp](build123d-mcp.md) tip-over check gives false positives on clamps; this one uses the contact hull, so test it on the clamp before trusting it.
- **Single body** is already a printlab check.

Their build volume is wrong for the slicer: 256 mm in Z. Bambu Studio's own machine profiles for both the P1S and the X1C set `printable_height` to 250 (read from the local system profiles). printlab's 250 is right. Their plate test also sorts the extents, so it passes a part that only fits once rotated.

### 2. Inspection sheet and close-ups

Their renderer ([`render.py`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/scripts/render.py), [`blender_render.py`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/scripts/blender_render.py)) drives headless Blender. Ideas, not the Blender dependency:
- **Ten views**: front, back, left, right, top, bottom, two three-quarter views, and upper and lower close-ups. printlab has no back or bottom view. Pockets, holes and chamfers on the bed face are only visible from below.
- **Close-up around a point**: crop a cube of ±R mm around (X, Y, Z) and render it from the front, side, above and below. They crop with an exact solid intersection, because cropping by triangles leaves shard-like slivers. In printlab this is one build123d intersection with a `Box`, then the existing z-buffer renderer.
- **Pick**: map a pixel on a close-up back to a 3D point. Their lessons say that guessing a defect's position from a picture was wrong twice. printlab's z-buffer already holds depth per pixel, so picking is an inverse projection.
- **Shading lessons**: same-facing flat faces shade identically, so raised flat details (text on a plate) vanish without cast shadows. Shadows that are too dark get mistaken for defects; they settled on a light shadow.

### 3. A fit record: default vs proven

Their config keeps a `proven` block for clearances confirmed by the user's own test prints, and a `defaults_used` list of values nobody has confirmed yet ([`printer.example.json`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/config/printer.example.json)). This is the mk3 "measured results feed back" idea in a form an agent can read. For printlab, keep one record (hole offset, press, snug, sliding and free fits, insert holes). Mark each value as a default or as proven by a named print (`hole-gauge`, a collar test plate), and have each part's `print.md` say when it relies on an unproven default.

### 4. FDM feature helpers

From [`functional.md`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/references/functional.md), [`modify.md`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/references/modify.md), [`meshops.py`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/scripts/meshops.py) and [`cad_template.py`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/assets/cad_template.py):
- **Cone roof on pockets that open onto the bed.** The pocket's ceiling becomes a 45° cone (its height is half the diameter), so it prints with no support. They found that a flat-roofed 10 mm magnet pocket filled with support. It falls back to a flat roof, with a warning, when less than one minimum wall of material is left above.
- **Teardrop or flat-top horizontal holes** above about 6 mm.
- **Bottom-edge chamfer** of 0.3–0.5 mm against elephant's foot, so mating parts still fit.
- **Insert, nut-trap, clearance and countersink helpers** driven by one size table.
- **Separate printed pins** for parts cut in two: 5 mm pins with 0.25 mm diametral clearance, holes 0.4 mm deeper than half a pin, placed by a distance transform as far from the section's edges as possible.

Take the shapes, not the table: two of its values are wrong (below). Per `CLAUDE.md`, the helpers go into `src/printlab/` only when a second part needs them.

### 5. Hole compensation in the slicer

Not in print-studio, but found while checking its hole allowance. Bambu Studio has **X-Y hole compensation**, which grows only enclosed holes, by twice the value on the diameter, and leaves the outer size alone. It does nothing for holes that open to the side ([Bambu wiki](https://wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation)). The key `xy_hole_compensation` exists in the X1C system process profiles (default 0), so ADR 0002 allows a preset to set it. Trade-off: it changes every closed hole, insert holes included, whose sizes are already chosen for printing. Geometry offsets stay per hole. Keep one or the other, never both, and record which in the fit record.

Bambu's default `elefant_foot_compensation` for "0.20mm Standard @BBL X1C" is already 0.15 mm (local system profiles; [Bambu wiki](https://wiki.bambulab.com/en/software/bambu-studio/parameter/elephant-foot)). A bottom chamfer is still useful, but it is not the only defence.

### 6. Slice check (high value, blocked by ADR 0001)

[`slice_check.py`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/scripts/slice_check.py) does the following:
1. Merges each Bambu system profile (machine, process, filament) with its whole `inherits` chain, because the CLI rejects partial profiles. It sets `from` to `system` and fills `printer_settings_id`, `print_settings_id` and `filament_settings_id` with the preset names.
2. Runs `bambu-studio --orient 0 --arrange 1 --ensure-on-bed --load-settings "machine;process" --load-filaments filament --slice 0 --export-3mf … --outputdir …`. The options match the [CLI wiki](https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage), except `--ensure-on-bed`, which it does not document.
3. Opens the sliced 3MF and reads `Metadata/slice_info.config` for `prediction` (seconds), `weight` (grams) and the slicer's warnings.
4. Walks the embedded G-code. `; FEATURE:` lines containing "support" switch support tracking on, and `; Z_HEIGHT:` lines give the layer. From the extruding moves it reports support grams, Z range, XY box and whether support stands on the bed. Bambu G-code uses relative extrusion (the X1C start G-code sends `M83`), so summing E is valid.
5. `--set KEY=VALUE` refuses keys the process profile lacks, the same guard as our `tests/test_presets.py`.

Its lesson: "supports enabled" is not "supports generated". Read the G-code.

What blocks it for printlab:
- ADR 0001 rejects CLI slicing for now.
- The merged machine and filament JSON files are printer and filament presets written to disk, which ADR 0002 forbids.
- The sliced `.3mf` is a project file holding G-code, the very thing the hard rule bans.

A version that could pass an ADR would:
- slice into a temp folder with the user's preset from `presets/`;
- keep only the numbers (grams, time, support yes/no and where) for `print.md`;
- delete everything else.

Known problems:
- CLI and GUI results can differ ([#1704](https://github.com/bambulab/BambuStudio/issues/1704)).
- Windows CLI slicing has open reports ([#9802](https://github.com/bambulab/BambuStudio/issues/9802)).
- On Windows and Linux it reads profiles from the install's `resources/profiles/BBL`, but the GUI uses updated copies in `%APPDATA%\BambuStudio\system\BBL` (the folder our preset test reads). The two can drift.
- Support grams are computed with PLA density (1.24) and a 1.75 mm filament. For PETG use the filament profile's `filament_density` (1.28 for Bambu PETG HF).

### 7. Lessons table

[`lessons.md`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/references/lessons.md) records each failure in three columns: what was tried, what happened, what to do instead. Rows relevant to us:
- a hook modelled upside down (check function, not just geometry);
- a flat-roof pocket that filled with support;
- an unsupported ledge that grew a 106 mm support tree;
- a background agent that sat two hours on an `rm` permission prompt.

### 8. Function checks when inspecting

[`inspection.md`](https://github.com/KvashaIhor/print-studio/blob/bda70052d8d9494ff5cec1d5b4eee3e3735eba33/skills/print-studio/references/inspection.md) asks three questions of every render:
- Does the part do its job the right way round?
- Do symmetric twins match?
- Do mating features line up?

It also says to confirm a suspected defect with numbers before declaring it.

### Already in printlab

- **Test coupons** for uncertain fits (test plate, lever strip, `juul-fit-strip`, `hole-gauge`).
- **The same view convention**: Z up, front faces −Y.
- **A delivery note** with print time, grams, supports and changed settings (`print.md`).
- **Snap-fit beams that bend in the layer plane.**

## Numbers checked

| Their value | Source check | Verdict |
|---|---|---|
| Clearance holes M2–M5: 2.4 / 2.9 / 3.4 / 4.5 / 5.5 mm, plus 0.2 mm | ISO 273 medium series, as in [3dp-mcp-server.md](3dp-mcp-server.md) | Correct. The +0.2 is their print allowance, the same as our 0.2 mm rule |
| Heat-set insert hole × length: M2 3.2 × 4.0, M3 4.0 × 5.7, M4 5.6 × 8.1, M5 6.4 × 9.5; hole depth = length + 1 mm | Ruthex table as given on the [Helsinki Hacklab wiki](https://wiki.helsinki.hacklab.fi/3D-thread-inserts) (ruthex.de returned HTTP 429). Ruthex's own [drill set](https://www.ruthex.de/en/products/ruthex-hss-bohrer-set-5-tlg-fur-gewindeeinsatze-m2-m2-5-m3-m4-m5-m6-din-338-bohrer-3-2-4-0-5-6-6-4-8-0-mm-fur-kunststoff-stahl-alu-kupfer-messing-uvm) has 3.2, 4.0, 5.6, 6.4 and 8.0 mm bits | Correct. Matches mk3's 4.0–4.2 mm for M3 |
| M2.5 insert: 3.6 mm hole, 4.5 mm long | Ruthex M2.5 is 5.7 mm long ([product](https://www.ruthex.de/en/products/ruthex-gewindeeinsatz-m2-5-70-stuck-rx-m2-5x5-7-messing-gewindebuchsen)) and takes a 4.0 mm hole (Hacklab table) | **Wrong** for Ruthex. It may suit another brand; unsourced |
| No wall rule around inserts | Ruthex minimum wall: 1.3 / 1.6 / 1.6 / 2.1 / 2.6 mm for M2 / M2.5 / M3 / M4 / M5 (Hacklab table) | **Missing.** Add it to the insert helper. It is stricter than our 1.2 mm general minimum |
| Nut across-flats M2–M5: 4 / 5 / 5.5 / 7 / 8 mm, plus 0.2 | ISO 4032 | Correct. Their circumradius conversion for `RegularPolygon` is right: `major_radius=True` is the default in build123d 0.13.0 |
| Countersink made with `CounterSinkHole` at its default angle | build123d 0.13.0 signature: `counter_sink_angle=82` (an imperial angle) | **Wrong for metric screws**, which have 90° heads. Pass 90 |
| Countersunk M3 head 6.0 mm (+0.4) | ISO 10642 M3 head is 6.72 mm theoretical maximum ([fasten.it](https://fasten.it/en/Norms/Norm/DIN%20EN%20ISO%2010642)). 6.0 is the DIN 965 nominal | Fine for DIN 965 / ISO 7046 heads. An ISO 10642 socket head sits about 0.2 mm proud |
| Holes print about 0.2 mm undersize | Agrees with printlab's rule. Still a default until `hole-gauge` is printed | Plausible, unproven |
| Fits "per side": press 0.1, snug 0.2, free 0.3, moving 0.4 | Their own nut trap adds 0.2 to the across-flats size (0.1 per side), and pins get 0.25 on the diameter. mk3 gives press 0–0.1, snug 0.15–0.2, sliding 0.3–0.4, free ≥ 0.5 | **Unclear**: labelled per side, used on the diameter. Our record must say which |
| Minimum wall 0.8 mm (two perimeters); structural 2–3 mm | X1C profiles: 0.42 mm outer and 0.45 mm inner line width, 2 wall loops | 0.8 is right for non-load walls. printlab's 1.2 mm load-bearing minimum stands |
| Overhangs up to 45° from vertical print unsupported | Common practice. Bambu's `support_threshold_angle` defaults to 30° from horizontal, so auto supports appear only on flatter faces | Consistent and conservative |
| Bridges up to about 10 mm; teardrop above about 6 mm; self-tapping hole about 0.85 × screw diameter; printed threads only M8 and up; text 6 mm or larger, embossed 0.6 mm or more; magnet pocket +0.3 mm diameter, +0.2 mm depth | No source given | Unsourced rules of thumb. Prove them on a coupon before relying on them |
| Elephant's foot about 0.2 mm; chamfer 0.3–0.5 mm | Bambu already compensates 0.15 mm by default (X1C 0.20 Standard) | Plausible. The chamfer adds to the slicer's correction |
| Snap-fit beam at least 1.5 mm thick, length at least 5 × deflection | For a cantilever of constant section, strain = 1.5 · t · y / L². At t = 1.5 mm, y = L/5 and L = 10 mm, that is 4.5 % strain | **Don't use.** The ratio ignores strain. Size beams by the strain formula against the filament's elongation |
| Build volume 256 × 256 × 256 mm | Bambu Studio `printable_height` is 250 for both the P1S and X1C | **Wrong in Z** for slicing |

## macOS-only or likely to break on Windows 10

- **Organic route**: Apple Silicon only (an MLX image model, the TRELLIS.2 Mac port, at least 24 GB of unified memory).
- **macOS defaults** in the config and setup: Blender and Bambu Studio app paths, Homebrew, and a `~/.config/print-studio` location. On Windows the executable and profile folder must be set by hand. The code finds the profiles next to the executable, which works for a standard install.
- **macOS commands in the skill text**: `open -a BambuStudio`, `tail -f`, `fc-list` / Font Book. `render.py pick` passes `/dev/null` to Blender; it writes nothing there, so this is harmless.
- **Likely crash on Windows**: `check_mesh.py` prints `✗` for blockers. When stdout is piped (as when an agent runs it), Python on Windows uses the ANSI code page and raises `UnicodeEncodeError` unless `PYTHONUTF8=1` is set. Inferred from the code, not run.
- **Encoding**: profile JSON is read without `encoding="utf-8"`. Low risk: on this machine only 1 of about 2,550 Bambu system profiles has non-ASCII bytes, and it would be skipped silently.
- **CLI slicing on Windows** is untested by the author and has open upstream reports (section 6).
- The author says Linux and Windows are untested.

## Not worth taking

- The organic, lithophane, relief and mesh-repair routes: out of scope for functional parts.
- Blender as a dependency. Our z-buffer renderer can take the views and crops above.
- Delivering a sliced `.3mf`. It conflicts with ADR 0001 and our hard rules.
- Its size table as it stands (M2.5 insert, countersink angle).
