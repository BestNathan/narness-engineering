# Evidence Selection

Select evidence from the changed behavioral surface, not from habit.

| Changed surface | Required local evidence |
|---|---|
| Documentation only | English-content/docs sanity only |
| Private implementation with unchanged public behavior | format + compile + focused unit tests |
| Public routing behavior | format + compile + unit tests + `public_contract` integration test |
| `Cargo.toml` or toolchain semantics | compile + unit + integration; use full scope because ownership widened |

## Negative controls

Do not:

- delete or weaken an assertion to make the suite pass;
- replace deterministic checks with manual inspection;
- run unrelated expensive evidence and present volume as confidence;
- claim a public behavior change is proven by private unit tests alone.

## Failure handling

A failed proof should lead directly to the owning behavior:

1. identify the failing invariant;
2. fix the producer or owner of the behavior;
3. rerun the narrow proof;
4. expand to the remaining required evidence only after the narrow proof is green.
