"""printlab build <part> — check a part and export STEP, STL, GLB and a preview to parts/<part>/out/."""

import argparse
import sys

from build123d import Compound

from printlab.checks import check_part, hole_diameters
from printlab.export import export_part, named_parts
from printlab.parts import PARTS_DIR, load_part, part_names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="printlab")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="check and export a part")
    build.add_argument("part", choices=part_names())
    sub.add_parser("list", help="list parts")
    args = parser.parse_args(argv)

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

    result = export_part(bodies, args.part, PARTS_DIR / args.part / "out")
    size = Compound(children=list(bodies.values())).bounding_box().size
    print(
        f"OK {args.part}: {size.X:.1f} × {size.Y:.1f} × {size.Z:.1f} mm, "
        f"{result.step_volume:.0f} mm³, about {result.grams:.1f} g PETG"
    )
    for body_name, body in bodies.items():
        if holes := hole_diameters(body):
            prefix = f"{body_name} " if len(bodies) > 1 else ""
            print(f"   {prefix}holes: {', '.join(f'{d:g}' for d in holes)} mm")
    for path in (result.step, result.stl, result.glb, result.preview):
        print(f"   {path.relative_to(PARTS_DIR.parent)}")
    # A part may set GRAM_BUDGET in its model.py; going over it warns but still exports.
    budget = getattr(module, "GRAM_BUDGET", None)
    if budget is not None and result.grams > budget:
        print(
            f"WARN {args.part}: about {result.grams:.1f} g is over the {budget:g} g budget",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
