# pzfreo/build123d-mcp

An MCP server that gives agents build123d CAD tools. Reviewed at [`4aaafe2`](https://github.com/pzfreo/build123d-mcp/tree/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b), version 0.3.92.dev0; the latest on PyPI is 0.3.91. Licence: Apache-2.0. **This is our CAD engine.**

## Verdict

Maintained, used and accurate.

- **Tests:** 1366 of 1378 pass. The 10 failures are path-traversal tests that tripped because the clone was under `/tmp`, an artefact of our test setup.
- **Geometry:** a test box with a hole and fillets measured 7649 mm³, matching a hand calculation. STL and STEP exports were re-verified independently.
- **Domain facts:** all 15 build123d API claims we spot-checked match the upstream source.
- **Project health:** one consistent maintainer, 10 outside contributors, 91 PyPI releases, active as of 2026-11-13.

## How we use it

- Give each part a name by registering it with `show(part, "name")`. A plain variable is invisible to its tools.
- Deny the `install_skill` tool. It lets the model write into `.claude/skills/`, `AGENTS.md` and other agent-instruction files.
- **Do not trust its sandbox.** Code inside `execute()` can reach `os` through `from build123d import os`, open files through `io.open`, and write anywhere through build123d's own `export_stl`. Its `security.md` is out of date. The real boundary is Claude Code's permission prompts.
- **Do not trust its tip-over check on clamps.** It reported a stable split-ring clamp as a tip-over error.
- Overlapping or multi-solid parts pass its validity gate with only a warning. Our own tests must require exactly one solid.
- Long chains of boolean operations can quietly turn into nonsense geometry. Check volume and face count after any heavy boolean work.

## Ideas we take

1. **A validity gate with more than one layer:** OpenCascade's `BRepCheck`, then a check that every edge is shared by exactly two faces, then a mesh-level manifold check.
2. **Round-trip export:** write the STEP, re-import it, and check the re-imported copy rather than the in-memory shape.
3. **A perturbation audit (`design_audit`):** rebuild the part with each top-level dimension nudged ±10% and flag dimensions whose change breaks it. This catches designs that only work at one exact size, which matters for parametric clamps you will keep tweaking.
4. **Runnable documentation:** its quick-reference examples run as tests, which is why its API guidance is accurate. Do the same for any code examples in our skills.
