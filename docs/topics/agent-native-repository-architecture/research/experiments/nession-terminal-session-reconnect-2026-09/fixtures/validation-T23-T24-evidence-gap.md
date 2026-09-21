# Evidence-Gap Validation — T23 / T24

T23 and T24 are evidence tasks, so their starting-state validity is established by **mutation survival**, not by making clean production behavior fail.

## T23 — competing recovery signals

Mutation:

```text
remove force-relay idempotence guard
→ repeated recovery outcomes may emit duplicate force-relay transitions
```

Validation branch:

```text
research/ai-native-a-mutation-t23
```

Workflow run:

```text
35555856328
```

Result:

```text
npm test        PASS (all existing tests)
npm run build   PASS
npm run lint    PASS
```

Therefore the current visible suite does **not** prove the T23 competing-signal invariant.

Decision:

```text
T23 evidence gap: CONFIRMED
```

## T24 — stale P2P work across forced relay

Mutation:

```text
force relay
but do not cancel the in-flight P2P attach
→ stale P2P work may still resolve after relay fallback
```

Validation branch:

```text
research/ai-native-a-mutation-t24
```

Workflow run:

```text
35555864469
```

Result:

```text
npm test        PASS (all existing tests)
npm run build   PASS
npm run lint    PASS
```

Therefore the current suite does **not** prove that stale in-flight P2P attach work loses authority across the P2P → relay transition.

Decision:

```text
T24 evidence gap: CONFIRMED
```

## Formal acceptance rule

For T23/T24, adding a test is successful only if:

```text
clean implementation + submitted test     PASS
known semantic mutation + submitted test  FAIL
```

The executable runner now supports treatment-specific hidden mutation patches and records whether each mutation is killed.

This is intentionally stronger than counting a new test file or accepting a test that passes only against clean code.
