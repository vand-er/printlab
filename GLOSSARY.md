# printlab

Agent-designed functional parts printed on a Bambu X1C. The first part is a clamp that holds a cart onto a battery whose threaded connection is broken.

## Language

### The assembly being repaired

**Cart**:
The disposable cartridge that screws onto the battery through a 510 threaded connection.
_Avoid_: Cartridge, tank, pod

**Battery**:
The rechargeable power unit the cart sits on.
_Avoid_: Pen, mod, base

**Seat**:
The joint where the cart's contact meets the battery's contact pin. In this repair its threads are stripped, so it only conducts while something presses the cart down.
_Avoid_: Connection, threads, joint

**Preload**:
The constant axial force pressing the cart into the seat. The clamp exists to supply it.
_Avoid_: Tension, pressure, grip

### The clamp

**Clamp**:
The printed part that holds the cart seated on the battery and supplies the preload. It detaches by hand and works with any cart.
_Avoid_: Holder, adapter, coupler

**Cradle**:
The clamp's fixed back half. It spans the seat and guides the cart into line with the battery, so the pair sits straight as if threaded.
_Avoid_: Spine, rail, guide

**Collar**:
A hinged ring on the cradle that clicks shut around the battery (the battery collar) or the cart (the cart collar). The battery collar closes first.
_Avoid_: Clip, ring, clamshell

**Door**:
The hinged half of a collar, which swings open and is held shut by the latch.
_Avoid_: Lid, flap

**Latch**:
The hook that snaps a collar shut and holds it closed until its tab is pressed.
_Avoid_: Clasp, catch, lock

**Keeper**:
The ramped block on a collar's fixed half that the latch's hook rides over and snaps behind.
_Avoid_: Catch, strike

**Pin**:
The separate rod pushed through a joint's knuckles after printing, which the joint turns on.
_Avoid_: Axle, rod

**Pin cap**:
The printed disc pressed onto a linkage Pin's outer end, which keeps the Pin from sliding out.
_Avoid_: Retainer, washer

**Lever**:
The part that, flipped past centre with a snap, pulls the cart collar down a fixed distance and so sets the preload. It is flipped last and released first.
_Avoid_: Cam, buckle, toggle

**Link**:
The bar from the lever to the cart collar, which pulls the collar down as the lever goes over centre.
_Avoid_: Rod, arm

**Stroke**:
How far the lever pulls the cart collar down, measured with the lever locked flat.
_Avoid_: Travel, throw

### Test prints

**Test plate**:
The first print: collar samples at three bores each, so the bores are chosen by feel before anything else is printed.
_Avoid_: Test print, gauge

**Lever strip**:
The second print: three small clamps built at the chosen bores, one per stroke, so the stroke is chosen on the real cart and battery.
_Avoid_: Stroke test

**Pin strip**:
The print that chooses the Pin's holes: rows of vertical and horizontal holes in a PETG strip, judged by hand with offcuts of the filament that become the Pins.
_Avoid_: Pin gauge

**Gap strip**:
Battery collar samples with print-in-place hinges at four gaps, to choose the smallest gap that turns and snaps.
_Avoid_: Gap test

### Checking and printing

**Blocker**:
A check result that fails the build, such as a wall under the minimum or an overhang the part did not declare.
_Avoid_: Fault

**Warning**:
A check result reported but not failing the build.
_Avoid_: Notice

**Inspection sheet**:
The set of rendered views of a part, from every side, that the user and agent look at before printing.
_Avoid_: Preview, render

**Fit record**:
The one list of clearances every part uses, each value on the diameter and marked as a default or as proven by a named print.
_Avoid_: Clearance table, tolerances

**Proven value**:
A fit-record value confirmed by a named test print; any other value is a default.
_Avoid_: Calibrated

**Sliced file**:
A part sliced by printlab with Bambu's own printer settings and the user's filament preset, ready for the user to send to the printer.
_Avoid_: G-code, project file, 3MF

**Slice check**:
A slice made only to learn a part's grams, time and where supports land; the sliced output is discarded.
_Avoid_: Test slice, dry run
