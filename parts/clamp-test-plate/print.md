# Test plate: how to print and assemble it

Print it after the Pin strip, once its picks are in `CollarParams`. It chooses the Battery and Cart collar bores.

## Print

- **File:** `out/clamp-test-plate.stl`. No Pins are in it.
- **Preset:** system process `0.20mm Standard @BBL X1C`. No supports.
- **Filament:** OVERTURE High Speed PETG, Transparent.
- **Plate:** Textured PEI.
- **Orientation:** as exported. Collars upright, each Door on the bed beside its stub. Don't rotate.
- **Print dialog:** flow calibration on; timelapse off.
- **Expected:** about 7.2 g PETG; about 1 h (Bambu Studio's estimate is the real one).

```slice
process: 0.20mm Standard @BBL X1C
filament: Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle
plate: Textured PEI Plate
stl: out/clamp-test-plate.stl
```

## Pins

Six Pins, one per collar hinge, each a 9 mm offcut of the same 1.75 mm PETG, cut square and deburred.

## Assemble each hinge

1. Close the Door onto its stub: its knuckle goes between the stub's two knuckles, and the Latch hook clicks behind the Keeper.
2. Push a Pin down from the top through all three knuckles. Each mouth has a lead-in.
3. The Pin is a press fit in the stub and turns in the Door. Press it flush with the top and bottom; trim it flush if it stands proud.

Push a Pin back out from below to take a hinge apart.

## Judge

Battery samples (12.6 / 12.8 / 13.0): pick the bore that grips the Battery. Cart samples (12.0 / 12.2 / 12.4): pick the bore that grips the brass.
