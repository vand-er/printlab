# build123d pitfalls

Found while building the clamp (spec #10, tickets #4, #5, #11–#14). Each cost an implementer a debugging loop.

## Distances and fits

- **A true cone skews OpenCascade's `distance_to`.** A 0.3 mm gap to a cone read 0.295 mm, once 0. Use faceted ends (`RegularPolygon` extruded with `taper`), as the knuckle spikes in `collar.py` do.
- **Distances next to a chamfer read about 3e-5 mm short.** So `checks.FIT_TOLERANCE` is 1e-4 mm, not 1e-6.
- **A diagonal gap is wider than its clearance.** An edge diagonally across a gap from another body sits gap·√2 away (0.42 mm at 0.3 mm); `joint_margin` (0.2 mm) in the Clamp covers it. Likewise a stop face at 45° needs a vertical push of gap·√2 to touch.
- **Faceted knuckles stand proud between facets.** At open angles off a facet boundary a ridge protrudes; the vertical knuckle-end gap is about 0.04 mm wider than `gap` to clear it.

## Booleans

- **A boolean can return a wrong result without raising.** `a & b` came back empty for bodies 0.05 mm into each other (the crank cap and Link), and `door − keepout` kept 5.6 mm³ inside the Pin's column. Decide contact by `distance_to`, not by an intersection's solids, and confirm a cut by its volume or solid count.
- **A flat facet facing a split plane triggers it.** The knuckle spikes failed at 14 and 18 facets, where a facet faced the Door's split at +Y, and passed at 15 and 16. Point a ridge at the split (`rotation=90` in `collar._below_spike`), and test a builder across the facet counts the nudge audit reaches.

## Chamfers and edge breaks

- **Chamfering a polygon outline fails.** A 48-sided outline gave inconsistent volumes and failed the STEP round-trip. Build outlines from true arcs and tangent lines (`clamp._disc_hull_prism`).
- **Breaking one edge bares the facing edge on the next body.** Run edge breaks in passes until a pass breaks nothing, re-finding edges after each chamfer, and drop zero-volume scraps that fallback cuts leave (`SLIVER`).
- **A sliver keeps making sharp edges.** A 0.01 mm sliver, such as a hook lead-in ending just inside a corner, spawns new sharp edges on every pass. End features exactly on corners.
