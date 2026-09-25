# Product consistency

Research on keeping a product the same across a generative design workflow, and on measuring it the way a person sees it: colour, shape, parts, text and logo, what goes missing and what gets invented.

Follows [From CAD to Shelf](https://github.com/meryboth/from-cad-to-shelf): its pipeline, its gate and its two products are the starting point and the baseline.

> Status: phase 0 (setup). No experiment runs yet.

## Research

| File | What it is |
|---|---|
| [`research/INFORME.md`](research/INFORME.md) | State of the art, starting point and experiment design (Spanish) |
| [`research/PROTOCOL.md`](research/PROTOCOL.md) | The formal protocol, frozen before the first run |
| [`research/LITERATURE.md`](research/LITERATURE.md) | Every source, with verified links |
| [`research/P3_INSPIRACION.md`](research/P3_INSPIRACION.md) | Design research and decision for the third product, VELA |

## Products

All three are invented and built from code, so the geometry is exact. No real brand, logo or product is used.

| Product | What it is | Built by |
|---|---|---|
| LUMEN | A handheld game console | `fixtures/lumen/build.py` (from From CAD to Shelf) |
| FIELD 16 | A pocket camera | `fixtures/field16/build.py` (from From CAD to Shelf) |
| VELA V-43 | A low-attention e-ink phone, text-heavy on purpose | `fixtures/vela/screen.py` + `fixtures/vela/build.py` |

```bash
py fixtures/vela/screen.py
blender -b -P fixtures/vela/build.py -- --export products/vela
blender -b -P pipeline/passes.py -- products/vela runs/vela/passes
py tools/variation.py vela          # the same product under four studio lights: the real-variation baseline
```

## Code

| Path | What it is |
|---|---|
| `pipeline/` | Ported unchanged from From CAD to Shelf at `64caef5` (see `pipeline/PORTED.md`). `qa.check` is the baseline gate |
| `tools/variation.py` | Renders each product under four lights, for the real-variation baseline |
| `research/scripts/` | `summarize_runs.py` and `render_report.py`: every number in the report comes from `results.json` |
