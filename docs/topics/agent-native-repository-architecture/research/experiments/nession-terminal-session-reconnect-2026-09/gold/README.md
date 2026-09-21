# Hidden Semantic Gold Set

> Do not include this file in coding-agent context during experiment runs.
>
> The gold set evaluates navigation and scope. It is not a required implementation recipe.

## Semantic owners

```text
G1 capability://web/transport/reconnect
   primary:
     web/src/platform/socket/WebSocketService.ts
     web/src/platform/socket/types.ts

G2 capability://terminal/session/visibility-wake
   primary:
     web/src/app/useVisibilityReconnect.ts

G3 capability://terminal/session/attach-state
   primary:
     web/src/platform/attach/AttachStateMachine.ts

G4 capability://terminal/session/reattach
   primary:
     web/src/platform/attach/SessionAttachController.ts

G5 capability://terminal/session/route-recovery
   primary:
     web/src/platform/session-runtime/SessionRuntime.ts

G6 capability://terminal/session/runtime-projection
   primary:
     web/src/product/terminal/useTerminalAttach.ts
     web/src/product/terminal/useTerminalOrchestration.ts
```

Primary verification areas:

```text
web/src/platform/attach/__tests__/unit/AttachStateMachine.test.ts
web/src/platform/attach/__tests__/unit/SessionAttachController.test.ts
web/src/platform/session-runtime/__tests__/unit/SessionRuntime.test.ts
web/src/platform/terminal-runtime/__tests__/unit/ConnectionManager.test.ts
web/src/product/terminal/__tests__/integration/useTerminalAttach.test.ts
related socket tests
related app visibility tests if added
```

## Per-task expected semantic scope

| Task | Primary owner(s) | Expected secondary scope |
|---|---|---|
| T01 | G2, G1 | visibility tests, socket disposed fact |
| T02 | G4, G5 | attach-controller/runtime tests |
| T03 | G4 | attach-controller tests |
| T04 | G3, G5 | runtime/state-machine tests |
| T05 | G1 | socket handshake/reconnect tests |
| T06 | G1 | socket generation tests |
| T07 | G5, G1 | runtime snapshot tests |
| T08 | G3, G4, G5 | runtime/attach tests |
| T09 | G2 | visibility-wake tests |
| T10 | G3, G4, G5 | attach state/controller/runtime tests |
| T11 | G4, G5 | controller/runtime tests |
| T12 | G5, G3 | runtime snapshot tests |
| T13 | G2, G1 | visibility/socket tests |
| T14 | G5, G1 | runtime/socket identity-preservation tests |
| T15 | G5, G1 | runtime/socket tests |
| T16 | G5, G4, G6 | runtime + terminal attach tests |
| T17 | G3, G5 | state-machine/runtime tests |
| T18 | G3, G5 | state-machine/runtime tests |
| T19 | G4, G1 | typed transport-failure contract + controller behavior tests |
| T20 | G3, G4, G5 | state-machine/controller/runtime tests |
| T21 | G4, G5 | controller/runtime tests |
| T22 | G1 | socket policy unit tests |
| T23 | G5, G3 | competing recovery-signal convergence invariant |
| T24 | G3, G4, G5 | state-machine/controller/runtime integration test |

## Known invariants

### I1 — one in-flight attach per transport generation

Repeated triggers for the same transport generation must not create parallel attach requests.

### I2 — stale attach resolution is a no-op

A request superseded/cancelled by a generation change cannot alter current attach state.

### I3 — current-generation attach success is the only attach success that counts

Old work may resolve but cannot reset retry state or mark the current transport attached.

### I4 — transport generation changes on route replacement

Route-intent changes and transport replacement must produce a new generation identity.

### I5 — manual route does not silently fail over

Manual-route recovery exhaustion ends in a failed state rather than forced relay.

### I6 — automatic recovery converges to relay after budget exhaustion

Automatic routing may retry/rotate, but once recovery is exhausted it must converge to one relay transition.

### I7 — visibility wake is explicit, bounded recovery

Wake may create an immediate explicit reconnect opportunity but must not create an independent infinite retry mechanism.

### I8 — stale physical WebSocket events cannot control current state

Generation guards own stale socket callback suppression.

### I9 — reconnect budget reset requires an established connection

Opening a socket is insufficient when a handshake exists; readiness/handshake success establishes the connection.

### I10 — latest viewport dimensions flow into current re-attach

A re-attach must not replay stale terminal dimensions when a newer size is known.

## Gold relevance rule

A loaded file counts as primary/relevant only when it contributes directly to the requested behavior, its contract, or required proof.

Historical planning docs, unrelated session UI components, tmux backend files, and unrelated protocol/session files are expected search-noise candidates for this experiment unless the task specifically requires them.

This distinction is important because the terms "session", "terminal", "attach", and "reconnect" occur across a large part of Nession.
