# printlab

Parametric, agent-designed functional parts for a Bambu Lab X1C. Vocabulary is in `GLOSSARY.md`; decisions are in `docs/adr/`; research and prior art are in `docs/research/`.

## Hard rules

- **Never write G-code or slicer project files.** Agents produce CAD only: STEP, STL and a PNG preview. The user slices by hand in Bambu Studio.
- **Every dimension is a named parameter** in the part's `Params` dataclass. No magic numbers in `build()`.
- **Test first.** Write the part's `test_model.py` assertions (hole sizes, fit, solid count) before the geometry.
- A part is done when `uv run pytest` passes, `uv run printlab build <part>` succeeds, and the user has looked at `out/<part>.png`.

## Layout

```
parts/<name>/model.py       Params dataclass + build(params, pose) -> Part or dict[str, Part]
parts/<name>/test_model.py  assertions for this part (TDD)
parts/<name>/out/           exported STEP, STL, PNG; committed
src/printlab/checks.py        check_part(): one valid solid that fits the X1C; check_fit(); hole_diameters()
src/printlab/export.py        export_part(): one Part or {name: Part} -> STEP, STL, GLB, coloured preview, grams
src/printlab/collar.py        CollarParams, Pose; hinge, Latch, Battery and Cart collar builders
src/printlab/clamp.py         ClampParams; Cradle, Lever, Link and linkage, shared by the Lever strip and Clamp
```

Add a helper to `src/printlab/` only once a second part needs it.

## Commands

- `uv run pytest`: all tests
- `uv run printlab build <part>`: check and export
- `uv run printlab list`: list parts

## Design rules

- Material: PETG or ASA. PLA softens at about 55 °C.
- Minimum wall 1.2 mm for load-bearing parts.
- Use the least filament that keeps full strength: remove material only where no load runs, and orient parts to print without supports.
- Orient snap-fit beams so they bend within the layer plane, never across layer lines.
- FDM holes print undersize. Use the measured offsets from the `hole-gauge` part once it has been printed; until then, add a 0.2 mm clearance.
- Check every number taken from elsewhere against `docs/research/prior-art/`. The table in `3dp-mcp-server.md` lists values known to be wrong.

## The build123d MCP server (`.mcp.json`)

- Register shapes with `show(part, "name")` so its tools can see them.
- Before writing geometry, read the MCP resources `build123d://quickref` and `build123d://selectors`; when a solid fails, read `build123d://skill/repair`. Look anything else up in https://build123d.readthedocs.io/en/stable/llms.txt.
- `install_skill` is denied in `.claude/settings.json`; leave it denied.
- Its sandbox is not a security boundary, and its tip-over check gives false positives on clamps.
- Use it to explore and measure. The part's source of truth is always `parts/<name>/model.py`.
