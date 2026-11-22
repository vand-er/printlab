# printlab

Parametric, agent-designed functional parts for a Bambu Lab X1C. Vocabulary is in `GLOSSARY.md`; decisions are in `docs/adr/`; research and prior art are in `docs/research/`; review rules are in `CODING_STANDARDS.md`.

## Hard rules

- **Never write G-code, slicer project files, or printer or filament presets by hand.** Agents produce CAD (STEP, STL, a PNG preview) and may write process presets in `presets/`, which the user imports (ADR 0002). A sliced file comes only from printlab's own slicing step, on request (ADR 0004). Sending anything to the printer is always the user's.
- **Every part has `parts/<name>/print.md`:** the preset to import, filament, plate, orientation, print-dialog options, expected grams and time. Whenever a part is ready to print, repeat it in chat.
- **Every dimension is a named parameter** in the part's `Params` dataclass. `tests/test_standards.py` enforces it.
- **Test first.** Write the part's `test_model.py` assertions (hole sizes, fit, solid count) before the geometry.
- A part is done when its own fast tests pass, CI is green, `uv run printlab build <part>` succeeds, and the user has looked at `out/<part>.png`.

## Layout

```
parts/<name>/model.py       Params dataclass + build(params, pose) -> Part or dict[str, Part]
parts/<name>/test_model.py  assertions for this part (TDD)
parts/<name>/out/           exported STEP, STL, PNG; committed
parts/<name>/print.md       how to print it
presets/<name>.json          Bambu Studio process presets (ADR 0002)
src/printlab/checks.py        check_part(): one valid solid that fits the X1C; check_fit(); hole_diameters()
src/printlab/export.py        export_part(): one Part or {name: Part} -> STEP, STL, GLB, coloured preview, grams
src/printlab/collar.py        CollarParams, Pose; hinge, Latch, Battery and Cart collar builders
src/printlab/strip.py         LabelParams, StripParams; sample strips: Cradle stubs in a row on a PETG strip, PLA labels
src/printlab/clamp.py         ClampParams; Cradle, Lever, Link and linkage, shared by the Lever strip and Clamp
src/printlab/font.py          text(): label glyphs from a font file CI has too
src/printlab/pinhole.py       teardrop(), lead_in(): roofed Pin holes and their lead-ins
src/printlab/nudge.py         the ±10 % Params nudge: nudged(), and audit() across worker processes
src/printlab/parts.py         part_names(), load_part(): find and import parts/<name>/model.py
src/printlab/slice_settings.py  read_slice_settings(): process, filament, plate, PETG STL from print.md's fenced slice block
src/printlab/cli.py           the `printlab` command: build, list
src/printlab/profiles.py      resolve(): Bambu's system profiles as Bambu Studio resolves them; filament()
```

`tests/test_layout.py` checks this block names every module.

Add a helper to `src/printlab/` only once a second part needs it.

## Commands

- `uv run pytest`: fast tests, in parallel; add `-n 0` for a single test
- `uv run pytest -m slow -n 0`: the ±10 % nudge audits, ~45 min. CI runs them on GitHub, one job per part; locally, run only the changed part's fast tests, and set `PRINTLAB_WORKERS=2` for any slow run so the user's PC stays usable.
- `uv run ruff check .`: lint
- `uv run printlab build <part>`: check and export
- `uv run printlab list`: list parts

## Design rules

- Material: PETG or ASA. PLA softens at about 55 °C.
- Minimum wall 1.2 mm for load-bearing parts.
- Use the least filament that keeps full strength: remove material only where no load runs, and orient parts to print without supports.
- Orient snap-fit beams so they bend within the layer plane, never across layer lines.
- Joints that turn are assembled on Pins, never printed in place: clear PETG fuses them (ADR 0003).
- FDM holes print undersize. Use the measured offsets from the `hole-gauge` part once it has been printed; until then, add a 0.2 mm clearance.
- Check every number taken from elsewhere against `docs/research/prior-art/`. The table in `3dp-mcp-server.md` lists values known to be wrong.

## build123d

- Read `docs/research/build123d-pitfalls.md` before chamfers, cones or fit checks.
- Before writing geometry, read the MCP resources `build123d://quickref` and `build123d://selectors`; when a solid fails, read `build123d://skill/repair`. Look anything else up in https://build123d.readthedocs.io/en/stable/llms.txt.
- To measure or debug a shape, prefer the build123d MCP tools (`show(part, "name")`, then `measure`, `compare`, `render_view`) over one-off scripts. Its tip-over check gives false positives on clamps.

## Agent skills

### Issue tracker

GitHub Issues on `vand-er/printlab`, via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the root. See `docs/agents/domain.md`.
