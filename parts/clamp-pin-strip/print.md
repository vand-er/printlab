# Pin strip: how to print and judge it

Print it before any part moves to Pins (ADR 0003). It chooses three hole sizes for a 1.75 mm PETG offcut.

## Print

- **Files:** `out/clamp-pin-strip.stl` (PETG) and `out/clamp-pin-strip-labels.stl` (labels). Import both as one object (Bambu Studio asks; answer Yes), then give the label parts the PLA filament.
- **Preset:** system process `0.20mm Standard @BBL X1C`. No supports.
- **Filament:** OVERTURE High Speed PETG, Transparent, for the three rows; white PLA for the labels.
- **Plate:** Textured PEI.
- **Orientation:** as exported. Rows flat on the bed, vertical tubes upright, horizontal holes along Y. Don't rotate.
- **Print dialog:** flow calibration on; timelapse off.
- **Expected:** about 2.0 g PETG plus a trace of PLA; about 30 min (Bambu Studio's estimate is the real one). Two filament swaps, both in the first layers.
- **Not by the phone route:** its sliced file would leave out the labels; slice it in Bambu Studio by hand.

```slice
process: 0.20mm Standard @BBL X1C
filament: Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle
plate: Textured PEI Plate
stl: out/clamp-pin-strip.stl
```

## Judge

Cut three offcuts of the PETG spool, each about 20 mm, square and deburred. Push the Pin in from the mouth (the chamfered end: the top of a tube, the back end of a horizontal hole).

1. **Vertical press fit (front row, 1.75 / 1.85 / 1.95):** push a Pin into each hole by hand. Pick the smallest hole that takes the Pin all the way by hand and holds it: it shouldn't fall out or turn when you shake the strip.
2. **Vertical clearance (middle row, 2.05 / 2.15 / 2.25):** push a Pin right through and spin it between your fingers. Pick the smallest hole in which it turns freely, with no tight spot along its length.
3. **Horizontal press fit (back row, 1.75 / 1.85 / 1.95):** as row 1. Pick the smallest hole that takes the Pin by hand and holds.

Push each Pin back out from the far end to check it comes apart.

Give the three picks to the agent. They become `pin_press_hole_vertical`, `pin_clearance_hole` and `pin_press_hole_horizontal` in `CollarParams` (`src/printlab/collar.py`).
