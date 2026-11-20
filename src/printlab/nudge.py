"""The ±10 % nudge audit: each numeric Params field nudged, the part rebuilt and checked.

`audit` runs the nudges in worker processes, one per CPU, since a part with many fields
and a slow build takes minutes per field otherwise.
"""

import os
from collections.abc import Collection
from concurrent.futures import ProcessPoolExecutor
from dataclasses import fields, replace

from printlab.checks import check_fit, check_part
from printlab.parts import load_part

FACTORS = (0.9, 1.1)


def nudged(params, field: str, factor: float):
    """`params` with one field scaled by `factor`: each item of a tuple, an int rounded."""
    value = getattr(params, field)
    if isinstance(value, tuple):
        value = tuple(v * factor for v in value)
    elif isinstance(value, int):
        value = round(value * factor)
    else:
        value = value * factor
    return replace(params, **{field: value})


def numeric_fields(params_type) -> list[str]:
    """The names of the fields whose defaults are numbers or tuples of numbers."""
    def numeric(v):
        return isinstance(v, (int, float)) or (
            isinstance(v, tuple) and all(isinstance(x, (int, float)) for x in v)
        )
    return [f.name for f in fields(params_type) if numeric(f.default)]


def fit_problems(
    bodies: dict, pairs: tuple[tuple[str, str] | tuple[str, str, float | None], ...], gap: float,
    pose: str,
) -> list[str]:
    """`check_fit` on each pair whose bodies are both in this pose; a `print` pose has no Pins.

    A pair may name its clearance, else it is the gap; None checks only that they don't overlap.
    """
    found = []
    for a, b, *clearance in pairs:
        if a in bodies and b in bodies:
            c = clearance[0] if clearance else gap
            if c is None:
                overlap = sum(s.volume for s in (bodies[a] & bodies[b]).solids())
                problems = [f"parts overlap by {overlap:.3f} mm³"] if overlap > 0 else []
            else:
                problems = check_fit(bodies[a], bodies[b], c).problems
            found += [f"{pose} {a}/{b}: {q}" for q in problems]
    return found


def problems(
    part: str, field: str, factor: float,
    pairs: tuple[tuple[str, str] | tuple[str, str, float], ...] | str,
    poses: tuple[str, ...],
) -> list[str]:
    """What breaks with one field nudged: `check_part` on each body in the first pose
    (as printed), and `fit_problems` in every pose."""
    module = load_part(part)
    params = nudged(module.Params(), field, factor)
    if isinstance(pairs, str):  # a function in the part's model, when a nudge renames bodies
        pairs = getattr(module, pairs)(params)
    found = []
    try:
        for i, pose in enumerate(poses):
            # A pose is build()'s arguments after params: a name, or a tuple of them.
            args = pose if isinstance(pose, tuple) else (pose,)
            pose = "/".join(map(str, args))
            bodies = module.build(params, *args)
            if i == 0:
                found += [f"{n}: {q}" for n, b in bodies.items() for q in check_part(b).problems]
            found += fit_problems(bodies, pairs, params.gap, pose)
    except Exception as error:  # a nudge that cannot build at all is a failure too
        found.append(f"build: {error!r}")
    return found


def audit(
    part: str, pairs: tuple[tuple[str, str] | tuple[str, str, float], ...] | str,
    poses: tuple[str | tuple, ...],
    only: Collection[str] | None = None,
) -> dict[tuple[str, float], list[str]]:
    """{(field, factor): problems} for every numeric field of the part's Params, or those `only`."""
    names = [f for f in numeric_fields(load_part(part).Params) if only is None or f in only]
    jobs = [(f, k) for f in names for k in FACTORS]
    # Under pytest-xdist every worker is already a process; one pool per CPU each would
    # start CPUs² processes. Run the slow audits with -n 0 to give the pool every CPU.
    workers = 1 if os.environ.get("PYTEST_XDIST_WORKER") else os.cpu_count()
    with ProcessPoolExecutor(workers) as pool:
        futures = {job: pool.submit(problems, part, *job, pairs, poses) for job in jobs}
        return {job: future.result() for job, future in futures.items()}
