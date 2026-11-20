# Clamp joints that turn are assembled on Pins, not printed in place

In clear PETG every print-in-place knuckle hinge fused, at gaps from 0.3 to 0.6 mm (Test plate, gap strip #16). So the collar hinges and the toggle joints print apart and are joined after printing by a 1.75 mm filament offcut: a press fit in the part that holds still, free in the part that turns. Hole sizes are chosen by a Pin strip.

## Considered Options

- **Wider PETG gaps.** 0.6 mm still fused.
- **PLA pin and washers printed in place** (#17). Built, never printed: 102 filament swaps per strip and bridged layers. Deleted, still in git history.
- **Snap-on C knuckles.** No loose parts, but a hard pull pops the Door off and the grip needs its own tuning.
- **Printed or metal Pins, heat-flattened ends.** A filament offcut is free, always on hand, and comes apart.

## Consequences

The Cart collar's slide stays printed in place until a print shows it fuses: a sliding face prints differently from a knuckle.
