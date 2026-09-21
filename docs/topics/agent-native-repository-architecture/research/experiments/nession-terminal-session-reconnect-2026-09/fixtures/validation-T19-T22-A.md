# Structural-Absence Validation — T19–T22 / Treatment A

All four structural refactor tasks were validated against the frozen A treatment.

| Task | Workflow run | Expected missing property | Observed result | Decision |
|---|---:|---|---|---|
| T19 | 35555791219 | typed attach failure kind | a `kind: 'transport'` failure with changed prose was misclassified as agent error and force-relayed | ACCEPTED |
| T20 | 35555798785 | one discriminated recovery `action` | `result.action` was `undefined`; legacy booleans remained authoritative | ACCEPTED |
| T21 | 35556083372 | distinct exported `TransportGeneration` / `AttachAttemptGeneration` types | TypeScript build could not import either identity; compile-time non-assignability contract therefore failed | ACCEPTED |
| T22 | 35555812474 | exported standalone reconnect backoff policy | `computeReconnectDelayMs` was not exported/available | ACCEPTED |

## T21 oracle note

The T21 acceptance is compile-time by design. The final corrected oracle first runs successfully under Vitest's transpile-only execution, then fails in `npm run build` because the requested exported identity types do not exist in the baseline. Its type-level assertions are also constructed so mutually assignable identity types fail compilation after those exports are added.

This means the oracle checks both:

```text
named type surface exists
+
identities are not mutually assignable
```

rather than relying on runtime behavior.

## Decision

```text
T19–T22 A starting states: ACCEPTED
```

Together with T23/T24 mutation-survival validation, the full T19–T24 refactor/evidence block now has a validated pre-run condition.
