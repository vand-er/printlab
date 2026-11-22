# Lever strip: how to print and assemble it

Print it after the Test plate, once its bore picks are in `ClampParams`. It chooses the Stroke (0.3 / 0.6 / 0.9 mm) on the real Cart and Battery.

## Print

- **File:** `out/clamp-lever-strip.stl`. No Pins are in it.
- **Preset:** system process `0.20mm Standard @BBL X1C`. No supports.
- **Filament:** OVERTURE High Speed PETG, Transparent.
- **Plate:** Textured PEI.
- **Orientation:** as exported. Each Cradle upright with its Cart collar on the rib above the Battery collar; the Doors on the bed in front; the Lever, three caps and the Link flat behind, each lead-in on top. Don't rotate.
- **Print dialog:** flow calibration on; timelapse off.
- **Expected:** about 14.5 g PETG; about 1.5 h (Bambu Studio's estimate is the real one).

```slice
process: 0.20mm Standard @BBL X1C
filament: Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle
plate: Textured PEI Plate
stl: out/clamp-lever-strip.stl
```

## Pins

Five per Clamp, fifteen in all, cut from the same 1.75 mm PETG, square and deburred:

| Pin | Length | Presses into | Turns in |
|---|---|---|---|
| Battery collar hinge | 12.0 mm | Cradle's knuckles | Battery Door |
| Cart collar hinge | 9.0 mm | Cart collar body's knuckles | Cart Door |
| Pivot | 6.8 mm | Cradle lug | Lever |
| Crank | 8.3 mm | Lever | Link |
| Lower Link | 6.5 mm | Cart collar's ear | Link |

Each linkage Pin gets one cap; the three caps are the same.

## Assemble each Clamp

1. **Battery collar.** Close the Door onto the Cradle, its knuckle between the Cradle's two, the Latch clicked behind the Keeper. Push the 12 mm Pin down from the top until flush at both ends.
2. **Cart collar.** The same with the Cart Door and the 9 mm Pin.
3. **Lever.** Hold it against the outside of the lug, lead-ins outward, lying flat on the Cradle's back. Push the 6.8 mm Pin from outside through the Lever into the lug until flush with the lug's inner face. Press a cap on, lead-in towards the Lever, until flush with the Pin's end.
4. **Link.** Lay it over the pivot cap, lead-ins outward, its holes on the Lever's crank hole and the ear's hole. Push the 8.3 mm Pin through it into the Lever until flush with the Lever's inner face. Push the 6.5 mm Pin through it into the ear until it bottoms.
5. **Caps.** Press a cap on each of those two Pins, lead-in inward, until flush with the Pin's end.

Each Pin presses into one part and turns freely in the other. Lever off: pull the caps, push the pivot and crank Pins out from the inside; the lower Link Pin's hole is blind, so pull it with pliers.

## Judge

Fit each Clamp on the Battery and a Cart and flip the Lever over centre. Pick the smallest Stroke that fires every time without crushing the Battery's pin.
