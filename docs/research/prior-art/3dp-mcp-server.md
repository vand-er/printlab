# brs077/3dp-mcp-server

An MCP server that wraps build123d and targets the Bambu X1C. Reviewed at [`960e8de`](https://github.com/brs077/3dp-mcp-server/tree/960e8de46fc52b82939bc43619cb16a7d4897374). Licence: CC BY-NC-ND 4.0. **Rejected.**

## Verdict

Mixed, leaning slop.
- **What works:** the core path of run CAD code, export STL/STEP, and measure. A pipe clamp exported from it was watertight and had the right volume.
- **Install:** it fails as published on Linux because of a `README.MD` case mismatch. It also needs `mcp<2`.
- **Broken tools:** about six call build123d APIs that don't exist: shell, section, drawing, 3MF export, non-uniform scale. Four of its 14 fastener types use invalid standard IDs.
- **Tests:** 85 of its 93 tests run on mock shapes, and they mock the very calls that are broken.
- **Printability checks:** they passed 0.4 mm walls, a 280 mm part and flat overhangs. The overhang maths is backwards.
- **Security:** `exec()` runs with full builtins and no timeout, and the path traversal holes were never fixed.
- **Maintenance:** dormant since 2026-03-18.

## Ideas we take

- **Wrap bd_warehouse** for fasteners, bearings and threads instead of modelling them by hand. bd_warehouse is Apache-2.0 and its class names are correct; use it directly.
- **Size against the X1C build plate (256 × 256 mm).** Bambu Studio limits height to about 250 mm.

## Values that are wrong: do not use

| Their claim | Correct |
|---|---|
| Print snap-fit beams vertically | Print them flat, so the beam bends along a layer, not across layer lines |
| M4 / M5 / M6 heat-set insert holes of 5.0 / 6.0 / 7.0 mm | About 5.3–5.6 / 6.3–6.4 / 7.6–8.0 mm (Ruthex, Pencom) |
| M2.5 screw-post hole 2.5 mm | About 2.0–2.2 mm for self-tapping, about 3.5–3.7 mm for an insert |
| M8 / M10 clearance holes 8.4 / 10.5 mm | 9.0 / 11.0 mm (ISO 273 medium, the same class as the rest of their table) |
| Tap-drill sizes used as printed holes | Printed holes come out undersize. Calibrate first. |
| "PETG is food-safe" | Layer lines harbour bacteria, and the resin grade varies. Don't claim this. |
