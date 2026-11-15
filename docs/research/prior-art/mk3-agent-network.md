# Matt28296/3D-Printing-Agent-Network

A Claude Code multi-agent system that takes a Prusa MK3 part from request to SD card. Reviewed at [`f2276a6`](https://github.com/Matt28296/3D-Printing-Agent-Network/tree/f2276a6eb96077cee03177cffcc953106022efe2). **No licence, so ideas only.**

## Verdict

Real, working software written by someone who knows FDM printing. It is not slop.
- **Tests:** 140 passed, 1 skipped. The skip only needs PrusaSlicer.
- **G-code validator:** a genuine stateful parser.
- **Domain facts:** about 95% correct against Prusa firmware source and the Prusament material data sheets.

Three weaknesses:
- It was published as one bulk commit and has no record of a real print.
- Its safety layer stops mistakes, but not a misbehaving agent.
- It only works with the MK3.

## Ideas we take

1. **Agents write parametric CAD, never G-code.** A hook blocks any write to a `.gcode` file. The slicer makes the G-code, and a human approves it before it prints.
2. **The deterministic layer is tested Python, not LLM judgement.** Mesh checks, hole measurement and validation are scripts with tests. Agents call them; they don't reimplement them.
3. **Gate files instead of trusting summaries.** Each stage writes a file whose first line is `VERDICT: PASS` or `VERDICT: FAIL`. The orchestrator reads the file itself, and after three failures of the same gate it hands the problem to the human.
4. **`NEEDS_TEST` is an honest strength verdict.** Until real material coupons have been measured, a part that carries load gets a physical proof test written into its acceptance criteria. It does not get a calculated pass.
5. **A "limits of this system" section in the README.** It says plainly what is automated, what stays human (and why), and where agent CAD is weak, for example on organic shapes and anything judged on looks.
6. **Measured results feed back.** After inspection the human records the real dimensions, and the next job starts from them.

## Design rules that passed the fact-check

These are source-checked values to use in our own design-rules skill:
- Softening points: PLA about 55 °C, PETG about 68–70 °C, ASA about 93–95 °C. These are Prusament heat deflection temperatures.
- The hole for an M3 heat-set insert is 4.0–4.2 mm across.
- Fit clearances, as defaults to be calibrated: press fit 0–0.1 mm, snug 0.15–0.2 mm, sliding 0.3–0.4 mm, free 0.5 mm or more.
- PrusaSlicer has no setting that compensates holes only. Its `xy_size_compensation` is applied to each side of every outline, holes included.
- Placeholder stiffness values are slightly high. Use PETG about 1.5 GPa and PLA about 2.2 GPa.

## Lessons from its bugs

- **An approval file the agent can write is not an approval.** A `python3 -c` one-liner forged `approval.json` and got past the export gate. Any human gate we add must be something an agent cannot produce.
- **Substring-matching hooks are not a boundary.** `bash -c`, `eval`, globs and string concatenation all got past them. Treat hooks as guardrails against honest mistakes.
- **Validators must handle every syntax the input allows.** The parser skipped `M104S400` because it had no spaces, and that skipped every check on the line. Bambu Studio writes the G-code here, so for us this applies to geometry checks.
