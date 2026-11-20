# Opt-in slicing from Bambu's own profiles

Narrows 0001 and 0002. On request, an agent may slice a part with the Bambu Studio command line and write a sliced file, `parts/<name>/out/<part>.gcode.3mf` (gitignored), so the user can start the print from Bambu Handy. `printlab build <part> --slice-check` slices the same way but keeps only grams, time and where supports land, for `print.md`. Normal builds never slice.

The command line needs complete printer and filament settings, and the complete X1C printer settings hold its start G-code. So agents never write those settings by hand: a script resolves them from the profiles Bambu Studio itself uses (`%APPDATA%\BambuStudio\system\BBL`) exactly as Bambu Studio does, takes the user's own filament preset unchanged, and uses them only in a temp folder that is deleted afterwards. After slicing, the start, end and layer-change G-code, temperatures and bed area in the output must equal Bambu's originals byte for byte, `result.json` must be clean, and `--no-check` is never used; any difference deletes the file and fails the build. The process preset stays the only thing an agent controls (0002), and the preset check rejects `post_process`, `filename_format` and any key ending in `_gcode`.

The user stays the last gate: they open the sliced file in Bambu Studio, check the toolpath preview, and send it to the printer's card themselves. Agents never send anything to the printer, sign in, or use a LAN access code.

## Considered options

- **Export the complete settings from the GUI by hand.** Rejected: they go stale with every Bambu profile update, and the install-folder and `%APPDATA%` copies already differ.
- **Copy print-studio's `slice_check.py`.** Rejected: it ignores `include`, so the X1C silently gets the generic start G-code.
- **Slice on every build.** Rejected: every build would depend on the Windows command line, which has open bug reports.

Research: `docs/research/bambu-cli-slicing-to-phone.md`.
