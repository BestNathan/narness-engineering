# Feature Absence Validation — T07–T12 / Treatment A

All six feature-oriented tasks were validated against the frozen A treatment using task-specific hidden acceptance tests.

| Task | Workflow run | Expected failure | Observed failure | Result |
|---|---:|---|---|---|
| T07 | 35555344293 | transport reconnect attempts absent from runtime snapshot | `transportReconnectAttempts` was `undefined`, expected `0` | ACCEPTED |
| T08 | 35555349503 | typed recovery cause absent | `lastRecoveryCause` was `undefined`, expected `socket-loss` | ACCEPTED |
| T09 | 35555356645 | structured visibility-wake telemetry absent | reconnect happened, telemetry callback count was `0`, expected `1` | ACCEPTED |
| T10 | 35555362313 | per-runtime attach retry budget absent | runtime remained on P2P after the configured short budget should have exhausted | ACCEPTED |
| T11 | 35555370539 | per-runtime attach timeout absent | attach used `10000ms`, expected configured `321ms` | ACCEPTED |
| T12 | 35555377435 | derived recovery-mode projection absent | `recoveryMode` was `undefined`, expected `none` before recovery | ACCEPTED |

## Validity

Each validation failed at the requested feature boundary rather than from syntax, import, or fixture setup errors.

The rest of the Web suite remained green in each run, so these are narrow feature-absence oracles rather than broad repository failures.

## Decision

```text
T07–T12 starting states: ACCEPTED
```

These tasks can now advance to cross-treatment oracle projection. Treatment B uses the same runtime behavior as A, so the same hidden acceptance semantics apply directly. Treatment C must install the same semantic oracle at its localized canonical paths without changing the task contract.
