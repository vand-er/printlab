# vand-er

Functional parts for a Bambu Lab X1C, designed as parametric build123d code and checked by tests.

## Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. Run `uv sync`.
3. Run `uv run pytest`.

## Make a part

```
uv run vander build hole-gauge
```

This writes `parts/hole-gauge/out/hole-gauge.{step,stl,png}`. Open the STL or STEP in Bambu Studio and slice it there.

## Parts

| Part | What it's for |
|---|---|
| `hole-gauge` | Print first. Measure each hole to learn how undersize your X1C prints holes. |
