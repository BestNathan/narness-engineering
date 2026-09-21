# Candidate Task Audit — T13–T24

> Status: Pre-freeze validity review.

The task pool is being audited against the frozen source before formal runs. A benchmark task is rejected or revised when the requested behavior/evidence already exists or is too highly correlated with another task.

| Task | Frozen-source finding | Decision |
|---|---|---|
| T13 | Explicit visibility wake already calls `connect()` for a stopped disconnected transport; exhausted reconnect budget does not automatically prevent that explicit attempt | keep as regression task with controlled fixture |
| T14 | Current-generation/stale-success semantics are already guarded and substantially overlap T02 | **replace** to reduce task correlation |
| T15 | Exact same-URL route-change behavior is already implemented and directly tested | keep only as controlled regression fixture |
| T16 | Runtime keeps latest `lastResize`; retry path exists, but current tests do not directly prove a disconnected size update reaches the next attach request | keep as controlled regression fixture |
| T17 | Manual-route exhaustion behavior already exists and is tested at state-machine/runtime levels | keep only as controlled regression fixture |
| T18 | Single force-relay convergence already exists and has direct runtime coverage | keep only as controlled regression fixture |
| T19 | Transport-failure prose strings are already centralized in one controller set; original 'centralize classifier' task has weak/possibly already-satisfied starting state | **replace** |
| T20 | Transition output is still represented by multiple booleans (`forceRelay`, `bumpRouteEpoch`, `retryAttach`) | keep as structural refactor |
| T21 | Transport generation and attach-attempt generation are both plain numbers and can be confused | keep as type-safety refactor |
| T22 | Backoff computation exists as a private helper but is not an independently owned/tested policy | keep, sharpen structural acceptance |
| T23 | The exact requested invariant test already exists: 'does not send duplicate attach for the same transport generation' | **replace** |
| T24 | Recovery behavior is covered in pieces, but no single test proves the whole attached-P2P → loss → recovery → forced-relay convergence chain | keep as integrated evidence task |

## Replacements

### T14R — Preserve live transport across non-routing context churn

Updating session context that does not change the effective endpoint or token must preserve the existing `WebSocketService` instance and its reconnect-attempt budget.

Examples of non-routing churn:

```text
viewport size update
transportReady update
value-equivalent address-plan/context rebuild
```

The task must prove that such updates do not silently rebuild the physical transport or reset transport reconnect attempts.

Why it is useful:

- tests distinction between session context and transport identity;
- crosses route-recovery and transport-reconnect capability boundaries;
- does not duplicate stale-attach generation tasks.

### T19R — Replace prose-string transport failure classification with a typed failure kind

The attach recovery path currently identifies transport failures by matching error prose such as `Connection lost`, `WebSocketService disposed`, and `Connection timeout`.

Refactor the selected slice so attach recovery consumes a typed/discriminated failure kind instead of owning a set of transport error strings.

Behavior must remain unchanged for timeout, transport failure, genuine agent refusal/error ack, and contract-violating rejection.

Why it is useful:

- removes semantic coupling to error text;
- creates a stronger machine-readable contract;
- is a genuine cross-capability refactor rather than an already-completed centralization task.

### T23R — Add an invariant test for competing recovery signals converging to one relay transition

Add deterministic evidence for a race-shaped case:

```text
automatic P2P recovery decides to force relay
        +
a stale/late candidate or transport recovery signal arrives
        ↓
exactly one force-relay runtime event
exactly one relay begin
no return to P2P recovery
```

This is distinct from T18: T18 repairs a deliberately injected duplicate-force-relay behavior; T23R asks for explicit durable evidence for the competing-signal invariant.

## Result

The formal pool remains 24 tasks, but revision 1 uses T14R, T19R, and T23R in place of the original T14, T19, and T23.
