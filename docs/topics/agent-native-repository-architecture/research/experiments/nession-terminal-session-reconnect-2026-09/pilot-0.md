# Pilot 0 — Validate the Experiment Before Collecting Formal Data

> Status: In progress.
>
> Purpose: validate task quality, isolation, and evidence mechanics. Pilot data is **not** included in the final A/B/C statistical comparison because the researcher had already inspected parts of the target code while designing the experiment.

## Why a pilot was necessary

The first attempt immediately exposed a validity problem in the frozen task set:

Several "bug-fix" tasks describe behaviors that the frozen Nession snapshot already appears to enforce.

If such a task is given to an agent, a correct response may be "no code change is required", while another agent may invent a change. That measures task interpretation more than repository architecture.

The formal experiment therefore needs an explicit **task fixture** layer:

```text
Treatment base
    ↓
Task fixture / controlled mutation
    ↓
Agent receives task statement
    ↓
Agent repairs / implements
    ↓
Acceptance evidence
```

Every formal task must begin from a state in which its acceptance condition is known to be unsatisfied (for a bug task) or absent (for a feature task).

## Pilot T01

Task:

> When the browser tab becomes visible again after being backgrounded, the wake reconnect path must not try to reconnect a WebSocket transport that has already been disposed.

### Baseline observation

The frozen code checked:

```text
visible
authenticated before
service exists
connectionState == disconnected
```

but did not check `WebSocketService.isDisposed`.

`connect()` itself rejects a disposed service, so the existing behavior was bounded but still attempted a reconnect and emitted an error. T01 therefore represented a real missing guard.

### Pilot implementation

Research-only branch:

```text
research/ai-native-a-t01
```

The change:

- added the disposed guard to the wake reconnect hook;
- added a focused jsdom integration test;
- preserved the previous unauthenticated and connection-state guards.

Research draft PR:

```text
BestNathan/nession#881
```

The PR targets `research/ai-native-ci-base`, not `staging`.

### Isolated CI

A dedicated base branch was created:

```text
research/ai-native-ci-base
```

It differs from the frozen source only by an experiment validation workflow. Research PRs target this branch so Nession's normal staging PR gate and iteration path are not used.

The first workflow run is:

```text
AI Native Research Validation
run: 35524635219
```

This validates the task branch with:

```text
npm ci
npm test
npm run build
npm run lint
```

### Measurement caveat

T01 is a pilot, not formal A data.

Before the T01 run began, experiment setup had already inspected the relevant wake and transport code. Therefore:

```text
first-hit accuracy
search cost
context acquisition cost
```

would be contaminated by prior knowledge.

The code/evidence pipeline is useful; the navigation metrics from this run are not admissible in the final comparison.

## Static validity check: T02–T06

A quick task-validity review of the same frozen snapshot found that several proposed bugs are already guarded.

### T02 — late attach success after route switch

The baseline already has an attach-generation guard in `SessionAttachController`, and route-intent changes cancel the active attach before rebuilding the transport.

Result:

```text
likely already satisfied
```

### T03 — late attach failure after cancellation

The same generation/cancel mechanism makes late resolution a no-op.

Result:

```text
already intentionally guarded
```

### T04 — repeated transport-loss notification idempotence

The runtime contains phase guards plus a disconnect re-entrancy guard. A first loss leaves `attached`; repeated reconnecting/connecting notifications do not redispatch `TRANSPORT_LOST`.

Result:

```text
appears already satisfied; needs fixture-backed acceptance to be a benchmark task
```

### T05 — handshake refusal must not consume reconnect loops

The transport explicitly distinguishes handshake refusal from socket loss and settles at `disconnected` without scheduling reconnect.

Result:

```text
already satisfied by design (#692 behavior)
```

### T06 — stale socket callbacks must not mutate the live connection

The socket lifecycle uses physical-socket generation guards, including the post-handshake success path.

Result:

```text
already satisfied by design
```

## Protocol amendment

Formal runs will not begin until every task has a fixture manifest.

Each task will define:

```yaml
task_id:
kind: bug | feature | refactor | verification

fixture:
  precondition:
  treatment_a_setup:
  treatment_b_setup:
  treatment_c_setup:

acceptance:
  tests:
  invariants:
  expected_behavior:

gold:
  semantic_owners:
  required_evidence:
```

For bug tasks, the fixture must intentionally create the observable defect.

For feature tasks, the fixture is usually the unmodified treatment base, but acceptance must prove the requested capability is absent before the run.

For refactor tasks, acceptance must include behavior preservation plus a structural condition.

For verification tasks, acceptance must prove the new evidence was absent before the run.

## Formal-data rule

Pilot runs are tagged:

```text
pilot: true
admissible_for_final_analysis: false
```

Formal A/B/C runs require:

1. a fresh agent session;
2. no prior task-specific source inspection in that session;
3. the task fixture applied before the session starts;
4. identical task intent and acceptance semantics across treatments;
5. recorded raw trace or equivalent tool-call log.

## Immediate next step

Build fixture manifests for T01–T06 first, then execute the first **formal** baseline batch from fresh sessions.

This pilot already produced a useful conclusion about experiment design:

> A task benchmark must prove that the requested change is absent in the starting state. Otherwise the benchmark can reward unnecessary edits and cannot cleanly measure repository navigation or coding productivity.
