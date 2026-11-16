# Coding standards

Read at review. Ruff (`uv run ruff check .`) and `tests/test_standards.py`, `test_glossary.py` and `test_layout.py` enforce the mechanical rules; these are the judgement calls.

## Geometry

- Each design rule in `CLAUDE.md` holds for every new or changed body: walls, support-free orientation, snap-fit bending in the layer plane, hole offsets, least filament.
- A printed dimension lives in `Params` with its unit and reason in a trailing comment. A modelling tolerance (boolean overlap, degenerate-tip guard) is a named module constant.
- Builders take sizes as arguments when another part (Lever strip, Clamp) will reuse them, as `src/printlab/collar.py` does.

## Tests

- Each spec number a test asserts cites its source in a comment (`# spec #10: …`).
- A test's expected value comes from the spec or an independent measurement, never from the code under test.
- Each acceptance box is tested on the ticket's own part, never as covered by another part's tests.
- Fit tests use `check_fit`; solid and build-volume tests use `check_part`. A part test re-implements neither.
- A test that takes more than about 20 s is marked `@pytest.mark.slow`.

## Layout

- A helper moves to `src/printlab/` only once a second part needs it.
