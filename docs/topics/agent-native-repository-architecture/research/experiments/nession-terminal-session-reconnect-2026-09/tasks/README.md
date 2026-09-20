# Frozen Task Set

> These task statements are frozen for experiment revision 1.
>
> They intentionally describe behavior rather than physical file paths.
>
> Gold ownership and likely affected artifacts are stored separately under `gold/` and must not be supplied to the coding agent.

The first experiment uses 24 independent task intents across the terminal/session reconnect slice.

## Benchmark status

These 24 task intents remain the candidate task pool, but they are **not yet formal benchmark instances**.

Pilot 0 found that several bug intents are already satisfied by the frozen source. Before a task becomes admissible for A/B/C comparison it must have a task fixture manifest that makes the requested condition observably absent or broken.

See [Pilot 0](../pilot-0.md) and the experiment protocol's task-fixture layer.

## Bug-fix tasks

### T01 — Wake reconnect must ignore disposed transports

When the browser tab becomes visible again after being backgrounded, the wake reconnect path must not try to reconnect a WebSocket transport that has already been disposed. Preserve all existing wake-reconnect behavior for a live disconnected transport.

### T02 — Late attach success after route switch must be ignored

A P2P attach started on one route can resolve after the user changes route. Ensure that a late successful attach from the old route cannot mark the new route as attached.

### T03 — Late attach failure after cancellation must be ignored

If an in-flight P2P attach is cancelled, a later timeout/error resolution from that request must not increment reconnect state or force relay.

### T04 — Repeated transport-loss notification must be idempotent

While a session is already reconnecting, repeated loss notifications for the same transport generation must not repeatedly advance recovery state or emit duplicate route-recovery events.

### T05 — Handshake refusal must not consume reconnect loops

A peer that explicitly refuses the post-open handshake should leave the transport disconnected without entering the normal socket-loss reconnect loop.

### T06 — Stale socket callbacks must not mutate the live connection

After a physical WebSocket has been superseded, late open/close/handshake callbacks from that stale socket must not change connection state or schedule reconnect work.

## Small feature tasks

### T07 — Surface reconnect attempt count in the session runtime snapshot

Expose the live transport reconnect-attempt count through the session runtime snapshot so higher layers can observe it without reaching into the WebSocket service.

### T08 — Surface the last reconnect cause

Add a typed reconnect-cause field to the session runtime observable state. It should distinguish at least socket loss, attach timeout, and explicit visibility wake; clear it after a successful stable attach.

### T09 — Add immediate wake reconnect telemetry

Expose one observable event when visibility wake causes an immediate reconnect. Do not emit the event if wake reconnect is skipped.

### T10 — Add configurable attach retry budget

Make the P2P attach retry budget configurable per session runtime while preserving the current default behavior.

### T11 — Add configurable attach timeout

Allow a session runtime to configure the timeout passed to P2P attach while preserving the existing default.

### T12 — Expose recovery mode

Expose whether the session is currently recovering through P2P retry, candidate rotation, or forced relay. It must remain a derived runtime fact rather than duplicate mutable state.

## Behavioral-change tasks

### T13 — Wake reconnect should also re-arm an exhausted disconnected transport once

If a previously authenticated transport exhausted its normal reconnect budget while the page was backgrounded and is now stopped in `disconnected`, one visibility wake may initiate one fresh explicit connection attempt. It must not create an unbounded retry loop.

### T14 — Successful attach resets attach retry budget only after current generation succeeds

Do not reset the P2P attach retry count because an old generation succeeds late. Reset only when attach succeeds for the current transport generation.

### T15 — Route change to the same URL must create exactly one new physical connection

A user route-intent change can resolve to the same URL. It must still replace the transport generation but open exactly one new physical socket.

### T16 — Preserve latest viewport size across reconnect

When P2P re-attaches after a transport loss, the attach request must use the most recently observed terminal size, including a size update that happened while disconnected.

### T17 — Manual route exhaustion must never silently force relay

When a manually selected route exhausts its recovery budget, the terminal must enter the failed state and remain on the manual route until the user changes intent.

### T18 — Auto route exhaustion must force relay exactly once

When automatic P2P recovery exhausts, force relay exactly once and do not emit repeated force-relay transitions from subsequent stale failures.

## Refactoring tasks

### T19 — Centralize transport-failure classification

Remove duplicated knowledge about which attach failures are transport-level failures. Introduce one canonical classifier used by attach recovery logic without changing observable behavior.

### T20 — Make reconnect transition output explicit

Refactor attach transition results so the recovery action is represented as one explicit typed action rather than multiple booleans that can theoretically conflict. Preserve current behavior.

### T21 — Separate transport generation from attach attempt identity

Refactor naming/types so a transport generation and an attach request attempt cannot be accidentally confused in recovery code. Preserve behavior and tests.

### T22 — Extract reconnect backoff policy

Make WebSocket reconnect backoff a separately testable deterministic policy with the existing base delay, exponential behavior, and 30-second cap unchanged.

## Verification / impact tasks

### T23 — Add an invariant test for no duplicate attach on one transport generation

Add a deterministic test proving that repeated triggers while one attach is in flight for the same transport generation cannot create a second attach request.

### T24 — Add an invariant test for recovery convergence

Add a deterministic test covering the full automatic recovery path: attached P2P → transport loss → retry/candidate recovery → forced relay after exhaustion. The test must prove recovery converges without duplicate attach or duplicate force-relay actions.

## Task balance

```text
Bug fix / failure semantics     T01–T06
Small feature / observability   T07–T12
Behavior changes                T13–T18
Refactoring                     T19–T22
Verification / invariants       T23–T24
```

No task names a source file. The agent must locate the behavior from repository structure and available treatment interfaces.
