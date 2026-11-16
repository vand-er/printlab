# Tooling that would help agents write CAD here

What exists for agents writing build123d CAD for FDM parts, and which gap in this repo each one fills. Researched 2026-11-15 from primary sources only: each repo's own code, README and LICENSE at a pinned commit, and official docs. Nothing third-party was installed or run.

**We take ideas, not code**, from anything that isn't permissively licensed. Slicing and printer control are out of scope under [ADR 0001](../adr/0001-agents-never-write-gcode.md). They are marked so below, not recommended.

The repos already reviewed in [prior-art/](prior-art/README.md) are not reviewed again. Only what we haven't adopted from them is listed.

## 1. Candidates, ranked

| # | Candidate | What it is | Gap it fills | Licence | Verdict | Why |
|---|---|---|---|---|---|---|
| 1 | [pzfreo/build123d-mcp](https://github.com/pzfreo/build123d-mcp/tree/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b) (unused parts) | Our CAD engine. It also serves tested reference docs, its skills as resources, coloured multi-part renders and a clearance tool. | G1, G2, G4, G5 | Apache-2.0 | **Adopt** (already a dependency) | It is in `.mcp.json` but doesn't start (section 3). Once it does, most of its help is one resource read away. |
| 2 | [gumyr/bd_warehouse](https://github.com/gumyr/bd_warehouse/tree/fcf23c7991c3f7fa6f28c59cda7276825f84c9bc) | build123d part library by build123d's author: fasteners, heat-set inserts, insert and clearance holes, threads, bearings, gears. | G7 | Apache-2.0 | **Adopt** as a dependency | It fits our lock: it needs build123d ≥0.12, <0.14 ([PyPI](https://pypi.org/pypi/bd-warehouse/json)) and `uv.lock` has 0.13.0. It has no hinges, snap-fits or springs. |
| 3 | [build123d official docs](https://build123d.readthedocs.io/en/stable/) | `llms.txt`, a cheat sheet, the joints tutorial, and examples including a spring | G2, G8 | Apache-2.0 | **Adopt** as reference | The authority on the API. `llms.txt` is generated from the docs themselves. |
| 4 | [DMontgomery40/bambu-printer-mcp](https://github.com/DMontgomery40/bambu-printer-mcp/tree/0e9fa423df476571bc28d6d45ea73faddae2ade3) | Bambu printer MCP server. It has an optional build123d engine and cited FDM fit and flexure guidance. | G3, G4, G8 | GPL-2.0 | **Ideas only** | It has the best fit and flexure guidance found. Printer control and slicing are out of scope. Its CAD engine won't run on Windows. |
| 5 | [m-esm/3d-print-modeling](https://github.com/m-esm/3d-print-modeling/tree/0bd303f67552534c2a3d42650932a85251a7d3a3) | Claude Code skill: a parametric FDM loop with headless multi-angle and section renders, plus an assembly interference gate | G4, G5 | MIT | **Ideas only** | The ideas are right, but it is one author's project with 1 star. Its renderer needs Playwright Chromium. |
| 6 | [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad/tree/2738524be8b30ec3d025d73b499fd2a6028af336) | A full build123d CAD platform with its own server, viewer, snapshot command and printability check | G3, G5 | MIT | **Ideas only** | Adopting it would replace our engine, and it installs by `curl … \| sh`. Its printing rules are worth reading. Its `print3d` skill is out of scope. |
| 7 | [Eli-code1/printagent](https://github.com/Eli-code1/printagent/tree/98cf2d5d3da5ef851d32938e5a3d09684f59c6e5) | Claude Code skills: build123d templates, FDM printability gates, assembly fit, layer-direction load check | G4, G3 | MIT | **Ideas only** | Good shapes for checks, but it has 0 stars and one author, and its tolerance numbers are its own priors. Its Bambu slicing handoff is out of scope. |
| 8 | [flowful-ai/cad-skill](https://github.com/flowful-ai/cad-skill/tree/ebc80490a67b566b30c4a22407acd9f569650958) | Claude Code skill for parametric printable parts in **CadQuery**, with a mating check and multi-view previews | G4 | [PolyForm Noncommercial 1.0.0](https://github.com/flowful-ai/cad-skill/blob/ebc80490a67b566b30c4a22407acd9f569650958/LICENSE) | **Ideas only** | The licence is noncommercial, and it is CadQuery, not build123d. Its collide-or-rattle test is the idea worth taking. |
| 9 | [heyixuan2/bambu-studio-ai](https://github.com/heyixuan2/bambu-studio-ai/tree/cdc26987d5bf1052a055d9403e3cb9630959dd08) | Agent skill for Bambu printing: model search, AI meshes, manifold3d CSG, mesh checks, previews, printer status | G5 (minor) | MIT | **Skip** | Its CAD is mesh CSG from JSON, not build123d. Its useful checks (wall thickness, overhang) are already in build123d-mcp. Slicing, MQTT and printer status are out of scope. |
| 10 | [VadneyK/makerspace-3d](https://github.com/VadneyK/makerspace-3d/tree/970ad6069ee2ee26cf47d06c3d53e1e846aeb33d) | Claude Code plugin for one maker space's X1C: a design skill, a slicing toolkit, and build123d-mcp | none | None (all rights reserved) | **Skip** | It is mostly a Bambu Studio CLI slicing toolkit, which is out of scope. It runs the same MCP server we do. |
| 11 | [rawwerks/VibeCAD](https://github.com/rawwerks/VibeCAD/tree/609e8885270cfdaeb73d96dda2e29362194d544d) | Claude Code plugins: a generic build123d skill, bd_warehouse examples, GLB render, model diff | G2 | MIT | **Skip** | It has been dormant since 2026-01-05. build123d-mcp's quick reference covers the same ground and is tested on every release. |
| 12 | [ocp-vscode / ocp_viewer](https://github.com/bernhard-42/vscode-ocp-cad-viewer/tree/6847ae5a7679a2445968467d4bcf65a2d00bb9f4), [Yet Another CAD Viewer](https://github.com/yeicor-3d/yet-another-cad-viewer/tree/5be952f8c7814b65f2453447471d9aa037eec8b0) | Interactive viewers for build123d models, with colours, assemblies, clipping and measuring | G5 (human side) | Apache-2.0; MIT | **Later, optional** | They are good for a human who wants to orbit an assembly. A coloured GLB opened in a browser covers that first. |

Notes on the rows:

- **build123d-mcp, unused parts.**
  - Its resources include a tested API quick reference (`build123d://quickref`), a selector cookbook and a bd_warehouse catalogue ([llms.md](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/llms.md#mcp-resources)).
  - Its skills can be read as resources such as `build123d://skill/modeling` without calling `install_skill` ([CHANGELOG v0.3.45](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/CHANGELOG.md#v0345--2026-06-10)). The skills are [modeling](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/src/build123d_mcp/skills/b123d-modeling/SKILL.md), [edit](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/src/build123d_mcp/skills/b123d-edit/SKILL.md) and [repair](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/src/build123d_mcp/skills/b123d-repair/SKILL.md).
  - `render_view` draws each named object in its own colour, takes `name:colour`, clips at a plane, labels objects and writes to `save_to` ([llms.md](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/llms.md#render_view)).
  - `clearance` returns gap, containment and overlap volume for two shapes ([llms.md](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/llms.md#clearance)).
- **`design_audit` can't see our parameters.** It audits only literal top-level assignments ([design_audit.py](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/src/build123d_mcp/tools/design_audit.py#L75-L77)). Our dimensions live in a `Params` dataclass, so it would find none. We keep our own pytest version (G6).
- **bd_warehouse.**
  - `InsertHole` sizes a hole for a `HeatSetNut`. It takes a `fit` of Close, Normal or Loose and a `manufacturing_compensation` in mm ([fastener.py](https://github.com/gumyr/bd_warehouse/blob/fcf23c7991c3f7fa6f28c59cda7276825f84c9bc/src/bd_warehouse/fastener.py#L4130-L4165)).
  - Insert sizes come from maker tables: McMaster-Carr, Hilitchi, ruthex, CNC Kitchen and others ([heatset_nut_parameters.csv](https://github.com/gumyr/bd_warehouse/blob/fcf23c7991c3f7fa6f28c59cda7276825f84c9bc/src/bd_warehouse/data/heatset_nut_parameters.csv)).
  - Its modules are bearing, bushing, fastener, flange, gear, o-ring, OpenBuilds, pipe, retaining ring, shaft key, sprocket and thread ([src/bd_warehouse/](https://github.com/gumyr/bd_warehouse/tree/fcf23c7991c3f7fa6f28c59cda7276825f84c9bc/src/bd_warehouse)). None of them is a hinge, snap-fit or spring.
- **build123d docs.**
  - [`llms.txt`](https://build123d.readthedocs.io/en/stable/llms.txt) is a 76-line index of the docs. `llms-full.txt` is about 620 KB, too big to load whole. Both are built by `sphinx_llms_txt` ([docs/conf.py](https://github.com/gumyr/build123d/blob/811152240553fd5ca4c015bb94c3aef50602fc6c/docs/conf.py#L49-L64)).
  - The [Joint Tutorial](https://build123d.readthedocs.io/en/stable/tutorial_joints.html) builds a box with a hinged lid using `RevoluteJoint`. That is close to our collar.
  - [examples/spring.py](https://github.com/gumyr/build123d/blob/811152240553fd5ca4c015bb94c3aef50602fc6c/examples/spring.py) builds a helical spring.
  - `export_gltf` writes colours and materials into a GLB ([Import/Export](https://build123d.readthedocs.io/en/stable/import_export.html)).
  - The [external tools page](https://github.com/gumyr/build123d/blob/811152240553fd5ca4c015bb94c3aef50602fc6c/docs/external.rst) lists the part libraries and viewers that exist. No snap-fit or hinge library is among them.
- **bambu-printer-mcp.**
  - Its `fdm_fit` text chooses a fit by what the interface must do: drop in, slide, locate, grip, snap or press. It says plainly that its bands are its own priors, not sourced values ([design-guidance.ts](https://github.com/DMontgomery40/bambu-printer-mcp/blob/0e9fa423df476571bc28d6d45ea73faddae2ade3/src/design-guidance.ts#L219-L260)).
  - Its `fdm_flexures` text covers compliant-first design, bending in the layer plane, strain chosen by duty, and creep under a held load ([design-guidance.ts](https://github.com/DMontgomery40/bambu-printer-mcp/blob/0e9fa423df476571bc28d6d45ea73faddae2ade3/src/design-guidance.ts#L84-L100)). Our clamp holds a constant preload, so creep matters.
  - Its build123d examples include `hinged_box.py`, `bag_clip.py` and `bistable_clicker.py` ([src/cad/examples/](https://github.com/DMontgomery40/bambu-printer-mcp/tree/0e9fa423df476571bc28d6d45ea73faddae2ade3/src/cad/examples)).
  - Its CAD engine "refuses to run without confinement", which it gets from macOS Seatbelt or Linux bubblewrap, so it won't run here ([README](https://github.com/DMontgomery40/bambu-printer-mcp/blob/0e9fa423df476571bc28d6d45ea73faddae2ade3/README.md#code-cad)).
  - GPL-2.0, so we read it and write our own.
- **m-esm/3d-print-modeling.**
  - [`assembly_check.py`](https://github.com/m-esm/3d-print-modeling/blob/0bd303f67552534c2a3d42650932a85251a7d3a3/scripts/assembly_check.py) checks every pair of parts for overlap and clearance, with an optional motion sweep.
  - [`shoot.py`](https://github.com/m-esm/3d-print-modeling/blob/0bd303f67552534c2a3d42650932a85251a7d3a3/scripts/shoot.py) renders iso, front, side, top and **bottom** views plus two section cuts. Its author says the bottom view caught bugs every other angle missed.
  - [`parts_viewer.py`](https://github.com/m-esm/3d-print-modeling/blob/0bd303f67552534c2a3d42650932a85251a7d3a3/scripts/parts_viewer.py) packs every part into one HTML file the user opens by double-click.
- **text-to-cad.** Its [printing reference](https://github.com/earthtojake/text-to-cad/blob/2738524be8b30ec3d025d73b499fd2a6028af336/skills/cad/references/manufacturing-printing.md) has three rules we lack:
  - Model the part in its print orientation.
  - Flag knife edges where a chamfer meets a face at under 45°.
  - Judge walls per part and clearances per pair.
- **printagent.**
  - [`verifying-assembly-fit`](https://github.com/Eli-code1/printagent/blob/98cf2d5d3da5ef851d32938e5a3d09684f59c6e5/skills/verifying-assembly-fit/SKILL.md) declares each joint with an intent (press, snug, slide or running) and checks it against an as-printed tolerance model.
  - [`check_layer_anisotropy.py`](https://github.com/Eli-code1/printagent/blob/98cf2d5d3da5ef851d32938e5a3d09684f59c6e5/skills/reviewing-structural-loads/scripts/check_layer_anisotropy.py) compares the load direction with the layer plane and finds the weakest cross-section along Z.
- **cad-skill.** [`mating.py`](https://github.com/flowful-ai/cad-skill/blob/ebc80490a67b566b30c4a22407acd9f569650958/mating.py) places two parts as assembled. It fails if they collide, and fails again if a shift of clearance + 0.1 mm still hits nothing, because then the part rattles. Its table of print defaults ([SKILL.md](https://github.com/flowful-ai/cad-skill/blob/ebc80490a67b566b30c4a22407acd9f569650958/SKILL.md#print-friendly-defaults)) is unsourced, for example "PETG … add +0.1mm". Don't use its numbers.
- **makerspace-3d.** Its skill makes slicing with `check_gcode` and Bambu Studio CLI 3MFs a hard rule ([SKILL.md](https://github.com/VadneyK/makerspace-3d/blob/970ad6069ee2ee26cf47d06c3d53e1e846aeb33d/skills/3d-print-design/SKILL.md#L16-L19)). That is the opposite of ADR 0001. Its README warns that the MCP server's first start downloads Python and "can take a minute" ([README](https://github.com/VadneyK/makerspace-3d/blob/970ad6069ee2ee26cf47d06c3d53e1e846aeb33d/README.md#install)).
- **Plugin catalogue.** A search of the Claude plugin catalogue for CAD, 3D printing, build123d and CadQuery found only a file-format converter. It is not relevant.

## 2. Gaps in this repo, and the fix for each

| Gap | What is missing now | Best fix |
|---|---|---|
| **G1. The CAD engine doesn't start** | `.mcp.json` launches `uvx … build123d-mcp@0.3.91`, which fails on this machine (section 3). | Install it once with `uv tool install`, and point `.mcp.json` at the installed `build123d-mcp`. |
| **G2. No build123d reference in the agent's context** | `CLAUDE.md` names no API reference, so agents write build123d from memory. | Add one line to `CLAUDE.md`: at session start read `build123d://quickref` and `build123d://selectors`, and read `build123d://skill/repair` when a solid fails. For anything else, look it up from the [stable `llms.txt`](https://build123d.readthedocs.io/en/stable/llms.txt). Keep `install_skill` denied; the resources make it unnecessary. |
| **G3. No FDM design-rules skill** | [mk3-agent-network.md](prior-art/mk3-agent-network.md#design-rules-that-passed-the-fact-check) collects checked values "to use in our own design-rules skill", but the skill doesn't exist. | Write `.claude/skills/fdm-design-rules/SKILL.md` in our own words: (1) the fact-checked values already in `prior-art/`; (2) choosing a fit by function and designing flexures by duty, both ideas from bambu-printer-mcp; (3) model in print orientation, no knife edges, clearance per pair (text-to-cad). Check every number against its primary source before it goes in. Bambu's PETG data sheet is one such source, cited at [design-guidance.ts L194-196](https://github.com/DMontgomery40/bambu-printer-mcp/blob/0e9fa423df476571bc28d6d45ea73faddae2ade3/src/design-guidance.ts#L194-L196). |
| **G4. No check between parts** | `check_part()` checks one solid alone. The clamp is a cradle, two collars, a cart and a battery, and nothing tests how they meet. | Add `check_fit(a, b, clearance)` to `src/printlab/checks.py` once the clamp needs it. It fails on any overlap volume, and fails if the gap is under the clearance. Add the rattle test from cad-skill, written by us: shift by clearance + δ and require a collision. Copy the meaning of build123d-mcp's `clearance` statuses (Apache-2.0). Use the MCP tool itself only to explore. |
| **G5. The preview can't show an assembly** | `_render_preview()` draws one mesh in one colour, from three views, with no section. | Extend `export.py` so it takes several named parts, draws each in its own colour, and adds a bottom view and a section cut (the m-esm idea). Matplotlib and trimesh are already dependencies. Also write a coloured `out/<part>.glb` with build123d's `export_gltf` so the user can orbit it. While designing, agents can call `render_view(objects="cradle:blue,collar:orange", clip_plane="z", save_to=…)`. |
| **G6. Perturbation is written by hand per part** | `hole-gauge/test_model.py` lists three fields by hand. `design_audit` can't read a `Params` dataclass. | When the clamp arrives, it is the second part, so add a helper to `src/printlab/` that nudges every numeric `Params` field by ±10% and runs `check_part`. |
| **G7. Standard hardware is modelled by hand** | There are no inserts, screws or threads. Hole sizes come from tables in `prior-art/`. | Add `bd_warehouse` to `pyproject.toml`. Use `InsertHole(HeatSetNut(...))`, `ClearanceHole` and the `IsoThread` family. Check its sizes against `prior-art/` and against `hole-gauge` results before trusting them. Pass our measured offset as `manufacturing_compensation`. |
| **G8. No hinge, snap-fit or spring library** | The collars hinge and click shut, and the clamp supplies preload. | No ready library exists in the build123d world. Model them by hand from `Params`. Use build123d `RevoluteJoint` (Joint Tutorial) to place each collar and test its swing with `check_fit`. Use `examples/spring.py` for any helix. Take the flexure approach from G3. Treat snap and preload strength as `NEEDS_TEST` (below). |

### Prior-art ideas not yet adopted

- **build123d-mcp:** the edge check of its validity gate, that every edge is shared by exactly two faces ([build123d-mcp.md](prior-art/build123d-mcp.md#ideas-we-take)). `checks.py` has BRep validity and a solid count, and `export.py` has STL watertightness, but no edge check. Also runnable docs: any code examples in our skills should run as tests.
- **3dp-mcp-server:** wrapping bd_warehouse. That is G7.
- **mk3-agent-network:**
  - gate files whose first line is `VERDICT: PASS/FAIL`, which the orchestrator reads itself;
  - a `NEEDS_TEST` verdict for parts that carry load;
  - a "limits of this system" section in the README;
  - the design-rules skill (G3);
  - measured results feeding back, which starts with the `hole-gauge` part.

## 3. Why the build123d MCP server fails to connect

**Cause: uv fails while installing the server's environment at launch.** It is not a timeout.

Claude Code's log for this project shows both attempts today ([`mcp-logs-build123d/2026-11-16T02-03-55-444Z.jsonl`](file:///C:/Users/maxto/AppData/Local/claude-cli-nodejs/Cache/G--ai-general-printlab/mcp-logs-build123d/2026-11-16T02-03-55-444Z.jsonl)):

- Claude Code gave the server a 30 s budget. Its version probe timed out after about 6 s, so it restarted the server once.
- Both runs died inside `uvx`, before Python ever started: `Failed to install: ipython-9.18.1 …` and `sympy-1.14.0 …`. The cause was `failed to remove directory …\uv\cache\builds-v0\.tmp…: The process cannot access the file because it is being used by another process. (os error 32)`.
- The connection closed after 8.7 s and 6.8 s, well inside the 30 s budget. So raising `MCP_TIMEOUT` ([Claude Code docs](https://code.claude.com/docs/en/mcp)) would not help.

Why it happens:

- `uvx` builds a throwaway environment in the uv cache, and only reuses it after it has once succeeded ([uv tools concepts](https://docs.astral.sh/uv/concepts/tools/)). It never succeeded, so every launch installs from scratch.
- Concurrent installs that share one cache on Windows fail at random with file-access errors. That is open uv issue [astral-sh/uv#2810](https://github.com/astral-sh/uv/issues/2810), and [#11002](https://github.com/astral-sh/uv/issues/11002) was closed as its duplicate.
- Claude Code's restart starts a second install while the first is being torn down. On Windows it ends the server's process tree 300 ms after closing stdin ([Claude Code docs](https://code.claude.com/docs/en/mcp)).
- The log doesn't say which process held the file. A second uvx, an antivirus scan or another session are all possible.

It isn't a known build123d-mcp bug:

- Its issue tracker has no "connection closed" report.
- Its Windows fix for first-call hangs ([CHANGELOG v0.3.87](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/CHANGELOG.md#v0387), issue [#452](https://github.com/pzfreo/build123d-mcp/issues/452)) is already in our pinned 0.3.91. It concerns tool calls, not startup.
- Its README does say to check first that the package can start, with `uv tool run … --version` ([README L53-L57](https://github.com/pzfreo/build123d-mcp/blob/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b/README.md?plain=1#L53-L57)). That step warms the cache before any app launches the server.

**Fix: take the install out of the launch.**

1. Install it once, from a terminal with no Claude session running:

   ```powershell
   uv tool install --python 3.12 build123d-mcp==0.3.91
   ```

   uv copies the executable to `C:\Users\maxto\.local\bin`, which is already on `PATH` (`uv tool dir --bin`). Nothing is installed there yet (`uv tool list`).
2. Point `.mcp.json` at the installed executable, so a launch only starts Python:

   ```json
   { "mcpServers": { "build123d": { "command": "build123d-mcp", "args": [] } } }
   ```

   uv's docs also say that `uvx` uses an installed tool by default. They don't say whether that holds when an exact `@version` is named, so naming the executable is the safer choice.
3. Restart Claude Code and check `/mcp`. To upgrade, run `uv tool install --python 3.12 build123d-mcp==<new>` and change nothing else.

The lighter alternative is to run the README's `--version` check once from a terminal to warm the cache. It still leaves an install at launch whenever the cache is cleared.
