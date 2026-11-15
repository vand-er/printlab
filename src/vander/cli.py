"""vander build <part> — check a part and export STEP, STL and a preview to parts/<part>/out/."""

import argparse
import sys

from vander.checks import check_part, hole_diameters
from vander.export import export_part
from vander.parts import PARTS_DIR, load_part, part_names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vander")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="check and export a part")
    build.add_argument("part", choices=part_names())
    sub.add_parser("list", help="list parts")
    args = parser.parse_args(argv)

    if args.command == "list":
        print("\n".join(part_names()))
        return 0

    part = load_part(args.part).build()
    report = check_part(part)
    if not report.ok:
        for problem in report.problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1

    result = export_part(part, args.part, PARTS_DIR / args.part / "out")
    size = part.bounding_box().size
    print(f"OK {args.part}: {size.X:.1f} × {size.Y:.1f} × {size.Z:.1f} mm, {part.volume:.0f} mm³")
    if holes := hole_diameters(part):
        print(f"   holes: {', '.join(f'{d:g}' for d in holes)} mm")
    for path in (result.step, result.stl, result.preview):
        print(f"   {path.relative_to(PARTS_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
