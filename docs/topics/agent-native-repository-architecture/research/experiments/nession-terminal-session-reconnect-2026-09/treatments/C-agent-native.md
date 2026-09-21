# Treatment C — Agent-Native Structure

> Status: C0 semantic layer seeded; structural transformation not yet frozen.
>
> Nession branch: `research/ai-native-repo-c-agent-native`

## Purpose

Treatment C asks whether changing the *shape of the code itself* improves autonomous coding after Treatment B has already supplied semantic addressability.

C inherits the same stable capability identities as B. The semantic IDs must remain constant even when physical paths change.

## Structural principles declared before formal runs

1. **Behavioral locality** — a capability's implementation, state transition logic, invariants, and primary tests should live in a bounded local unit.
2. **One canonical owner** — no behavior-critical fact may have multiple editable authorities.
3. **Explicit dependencies** — a unit should reveal what it consumes and what consumes it without requiring repository-wide search.
4. **Low abstraction indirection** — abstractions that force multi-hop navigation without reducing semantic duplication should be flattened for the selected slice.
5. **Executable invariants close to ownership** — the proof surface should be discoverable from the unit.
6. **Stable semantic identity, movable physical representation** — `capability://...` stays stable across the refactor.

## Intended physical shape

Candidate target:

```text
web/src/units/terminal-session/
  transport-reconnect/
    implementation.ts
    types.ts
    __tests__/

  visibility-wake/
    implementation.ts
    __tests__/

  attach/
    state.ts
    controller.ts
    __tests__/

  route-recovery/
    runtime.ts
    __tests__/

  runtime-projection/
    useTerminalAttach.ts
    useTerminalOrchestration.ts
    __tests__/
```

The exact names may change during C construction, but the transformation must be completed and frozen before any formal C task run.

## Constraint against cheating

C must not encode benchmark task answers in filenames, manifests, comments, or helper APIs.

The refactor is allowed to expose stable domain concepts and invariants, but not T01–T24-specific repair hints.

## Measurement cost

C has an up-front engineering cost that B does not have. The study must record that cost separately.

At minimum record:

```text
files moved/created/deleted
lines changed for the structural conversion
tests changed only because of paths/imports
human/agent time to create C
CI failures during C construction
semantic-index maintenance required by the move
```

This matters because even if C produces faster future agent changes, the refactor may not amortize quickly enough to be worthwhile.

## C0

The branch has been seeded with the same `.ai-native` semantic layer as B. No performance claim is attached to C0.

The next C step is the behavior-locality refactor of the selected reconnect slice while preserving all existing behavior and tests.
