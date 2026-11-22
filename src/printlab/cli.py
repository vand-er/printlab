"""printlab build <part> — check a part and export STEP, STL, GLB and a preview to parts/<part>/out/."""

import argparse
import sys

from build123d import Compound

from printlab.checks import check_part, hole_diameters
from printlab.export import export_part, named_parts
from printlab.parts import PARTS_DIR, load_part, part_names
from printlab.reference import Invalid, Passed, compare_first_layers
from printlab.slice_settings import SliceSettingsError, read_slice_settings
from printlab.slicing import SliceError, slice_part


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="printlab")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="check and export a part")
    build.add_argument("part", choices=part_names())
    slicing = build.add_mutually_exclusive_group()
    slicing.add_argument(
        "--slice-check",
        action="store_true",
        help="slice with Bambu Studio and report grams, time and supports; keep no sliced file",
    )
    slicing.add_argument(
        "--slice",
        action="store_true",
        help="as --slice-check, and keep the sliced file in out/ for the phone route (docs/phone-route.md)",
    )
    build.add_argument(
        "--reference",
        metavar="PART",
        help="with --slice-check or --slice, check the first layers against this reference print's",
    )
    sub.add_parser("list", help="list parts")
    args = parser.parse_args(argv)
    if args.command == "build" and args.reference is not None:
        if not (args.slice_check or args.slice):
            build.error("--reference needs --slice-check or --slice")
        if args.reference not in part_names():
            build.error(f"--reference: no part named {args.reference!r}")

    if args.command == "list":
        print("\n".join(part_names()))
        return 0

    module = load_part(args.part)
    bodies = named_parts(module.build(), args.part)
    failed = False
    for body_name, body in bodies.items():
        for problem in check_part(body).problems:
            print(f"FAIL {body_name}: {problem}", file=sys.stderr)
            failed = True
    if failed:
        return 1

    # A part may set SEPARATE_STL = {suffix: body-name prefix} for bodies in a second filament.
    separate = getattr(module, "SEPARATE_STL", {})
    result = export_part(bodies, args.part, PARTS_DIR / args.part / "out", separate)
    size = Compound(children=list(bodies.values())).bounding_box().size
    print(
        f"OK {args.part}: {size.X:.1f} × {size.Y:.1f} × {size.Z:.1f} mm, "
        f"{result.step_volume:.0f} mm³, about {result.grams:.1f} g PETG"
    )
    for body_name, body in bodies.items():
        if holes := hole_diameters(body):
            prefix = f"{body_name} " if len(bodies) > 1 else ""
            print(f"   {prefix}holes: {', '.join(f'{d:g}' for d in holes)} mm")
    for path in (result.step, result.stl, *result.separate_stls.values(), result.glb, result.preview):
        print(f"   {path.relative_to(PARTS_DIR.parent)}")
    # A part may define notes(bodies) -> lines worth reporting, such as how its filaments swap.
    for line in getattr(module, "notes", lambda bodies: [])(bodies):
        print(f"   {line}")
    # A part may set GRAM_BUDGET in its model.py; going over it warns but still exports.
    budget = getattr(module, "GRAM_BUDGET", None)
    if budget is not None and result.grams > budget:
        print(
            f"WARN {args.part}: about {result.grams:.1f} g is over the {budget:g} g budget",
            file=sys.stderr,
        )
    if args.slice_check or args.slice:
        # A stale sliced file never outlives a new slice, even one that fails.
        keep = PARTS_DIR / args.part / "out" / f"{args.part}.gcode.3mf"
        keep.unlink(missing_ok=True)
        try:
            settings = read_slice_settings(args.part, PARTS_DIR)
            # Only the bodies in the STL that is sliced, not those in a second filament's STL.
            sliced = {n: b for n, b in bodies.items() if not n.startswith(tuple(separate.values()))}
            report = slice_part(settings, keep if args.slice else None, sliced)
        except (SliceError, SliceSettingsError) as problem:
            print(f"FAIL {args.part}: {problem}", file=sys.stderr)
            return 1
        minutes, seconds = divmod(round(report.seconds), 60)
        print(f"   sliced with: {settings.process}; {settings.filament}; {settings.plate}")
        print(f"   sliced grams: {report.grams:.2f} g")
        print(f"   sliced time: {minutes} min {seconds} s")
        print(f"   sliced supports: {len(report.supports) or 'none'}")
        for n, region in enumerate(report.supports, 1):
            (x0, x1), (y0, y1), (z0, z1) = region.x, region.y, region.z
            print(
                f"   support {n}: x {x0:.0f} to {x1:.0f}, y {y0:.0f} to {y1:.0f}, z {z0:.1f} to {z1:.1f} mm"
            )
        if args.slice:
            print(f"   sliced file: {keep.relative_to(PARTS_DIR.parent)} (to print it: docs/phone-route.md)")
        _print_islands(report.islands)
        if args.reference is not None:
            return _check_reference(args.part, report, args.reference)
    return 0


def _check_reference(part: str, report, reference: str) -> int:
    """Slice the reference print fresh, from its PETG STL only, and compare the first layers."""
    try:
        theirs = slice_part(read_slice_settings(reference, PARTS_DIR))
    except (SliceError, SliceSettingsError) as problem:
        print(f"FAIL {part}: reference print {reference}: {problem}", file=sys.stderr)
        return 1
    verdict = compare_first_layers(report, theirs)
    if isinstance(verdict, Invalid):
        print(
            f"FAIL {part}: first-layer settings differ from {reference}'s in {', '.join(verdict.settings)}",
            file=sys.stderr,
        )
        return 1
    if isinstance(verdict, Passed):
        smallest = "; ".join(
            f"layer {layer} {own:.1f} mm² against {ref:.1f} mm²"
            for layer, (own, ref) in verdict.smallest.items()
        )
        print(f"   reference print {reference}: every island at least its smallest ({smallest})")
        return 0
    for smaller in verdict:
        island = smaller.island
        print(
            f"WARN {part}: layer {island.layer} {island.body}: {island.area:.1f} mm², "
            f"below {reference}'s {smaller.reference_area:.1f} mm²",
            file=sys.stderr,
        )
    return 0


def _print_islands(islands) -> None:
    """Each first layer's islands, by body and then largest first."""
    for layer in sorted({i.layer for i in islands}):
        own = [i for i in islands if i.layer == layer]
        print(f"   layer {layer} islands: {len(own)}")
        for n, island in enumerate(own, 1):
            (x, y), area = island.centroid, island.area
            print(f"   layer {layer} island {n}: {island.body}, {area:.1f} mm² at x {x:.1f}, y {y:.1f}")


if __name__ == "__main__":
    sys.exit(main())
