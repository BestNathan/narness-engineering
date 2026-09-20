# Nession Terminal / Session Reconnect Experiment Protocol

> Experiment ID: `nession-terminal-session-reconnect-2026-09`
>
> Status: Setup / task set frozen before treatment implementation.
>
> Target repository: `BestNathan/nession`
>
> Frozen source commit: `0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664`
>
> Frozen from: `staging` at 2026-09-21 experiment setup.

## Research question

Does an AI-native repository representation make an AI coding agent materially better at modifying a real, cross-cutting reconnect workflow?

The selected slice is the Web terminal/session reconnect and re-attach path:

```text
browser visibility wake
        ↓
WebSocketService connection lifecycle
        ↓
SessionRuntime transport generation
        ↓
AttachStateMachine
        ↓
SessionAttachController
        ↓
P2P / relay re-attach
        ↓
terminal runtime / React projection
```

This target was selected because it has all of the properties the research hypothesis needs:

- the same words appear in many unrelated files (`session`, `terminal`, `reconnect`, `attach`);
- behavior crosses platform, product, state machine, controller, transport, hook, and tests;
- there are several distinct reconnect budgets and generations;
- correctness depends on temporal invariants and stale-event suppression;
- failures are observable through deterministic unit/integration tests;
- the slice is important enough to be realistic but bounded enough to run repeatedly.

## Frozen experiment branches

All three branches start from the exact same commit and are excluded from the normal Nession `staging` delivery path.

```text
research/ai-native-repo-a-baseline
research/ai-native-repo-b-semantic-index
research/ai-native-repo-c-agent-native
```

### Treatment A — Baseline

No experimental repository changes.

The agent uses the repository as it existed at the frozen staging commit:

```text
filesystem
grep / glob
existing source
existing docs
existing tests
existing TypeScript/compiler feedback
```

### Treatment B — Semantic index

Keep implementation topology materially unchanged.

Add only machine-oriented semantic resolution:

```text
stable capability IDs
unit manifests
canonical owners
dependency / consumer edges
contract ownership
state ownership
test / invariant mappings
resolver-oriented entry point
```

The purpose of A vs B is to isolate the value of semantic addressability and deterministic resolution from code restructuring.

### Treatment C — Agent-native structure

Start from the same frozen behavior and add:

```text
everything in B
+ stronger behavioral locality
+ explicit canonical ownership
+ reduced accidental aliases
+ bounded abstraction depth where useful
+ executable invariants
+ evidence routing
+ unit-oriented work boundaries
```

The purpose of B vs C is to measure whether code shape itself adds value after semantic indexing already exists.

## Important isolation rule

The three branches are research surfaces only.

They MUST NOT be merged into `staging` as part of normal feature delivery.

Any conclusion that later graduates into Nession or Narness requires a separate design decision and a normal implementation change.

## Controlled variables

For every comparable run keep fixed:

- exact task statement;
- model family and model version where available;
- reasoning/thinking setting;
- system prompt;
- agent harness version;
- context window;
- time and token budget;
- starting branch state;
- runtime/build environment;
- test environment;
- network policy;
- retry policy.

Treatment-specific semantic resolver access is allowed only for B/C because it is the independent variable.

## Primary semantic capability graph

The experiment uses semantic identities independent of physical paths.

```text
capability://web/transport/reconnect
capability://terminal/session/reattach
capability://terminal/session/attach-state
capability://terminal/session/route-recovery
capability://terminal/session/visibility-wake
capability://terminal/session/runtime-snapshot
```

Expected current physical areas include:

```text
web/src/platform/socket/WebSocketService.ts
web/src/platform/socket/types.ts
web/src/platform/attach/AttachStateMachine.ts
web/src/platform/attach/SessionAttachController.ts
web/src/platform/session-runtime/SessionRuntime.ts
web/src/app/useVisibilityReconnect.ts
web/src/product/terminal/useTerminalAttach.ts
web/src/product/terminal/useTerminalOrchestration.ts
related unit/integration tests
```

These paths are not the semantic identity and may differ in Treatment C.

## Acceptance environment

Primary commands:

```bash
cd web
npm test -- <targeted vitest files>
npm run build
npm run lint
```

Targeted tests should be preferred during repair loops. Full build/lint remains part of evidence closure.

## Run procedure

For every task and treatment:

1. Reset the treatment branch/worktree to its frozen treatment start SHA.
2. Start a fresh agent session.
3. Record run metadata before the first tool call.
4. Give the exact task text from `tasks/README.md`.
5. Record all search/glob/read/resolver/edit/validation operations.
6. Record loaded artifacts and classify relevance against the hidden gold file.
7. Record the first proposed edit and whether it targeted the correct semantic owner.
8. Run task-specific acceptance checks.
9. Run required evidence closure checks.
10. Store the trace summary in `runs/`.
11. Reset the worktree before another run.

Tasks are independent. No solution from one task may be carried into the next task's starting state.

## Required measurements

Per run:

```text
time_to_first_relevant_artifact
first_hit_correct
search_calls
glob_calls
resolver_calls
files_read
unique_files_read
irrelevant_files_read
important_artifacts_missed
input_tokens            # when available
output_tokens           # when available
reasoning_tokens        # when available
time_to_first_edit
patch_count
reverted_patch_count
out_of_scope_edits
compiler_failures
test_failures
repair_loops
task_success
evidence_complete
wall_time
model_cost               # when available
```

## Relevance classification

Each artifact read during a run is classified against the hidden gold set:

```text
primary   — owns behavior required by the task
relevant  — necessary dependency / consumer / test / contract
adjacent  — reasonable background but not necessary
irrelevant — does not contribute to the required change
```

This classification drives retrieval precision and search-noise metrics.

## Failure taxonomy

```text
R1  target not found
R2  wrong semantic owner selected
R3  important dependency/consumer missed
R4  contract misunderstood
R5  invariant missed
R6  implementation error
R7  verification gap
R8  feedback insufficient or misleading
R9  tool/runtime failure
R10 task ambiguity
R11 treatment metadata stale/incorrect
R12 architecture treatment introduced accidental complexity
```

## Experiment stages

### Stage 0 — Setup

- freeze source commit;
- create A/B/C branches;
- freeze task set;
- freeze hidden semantic gold set;
- document the protocol.

### Stage 1 — Baseline characterization

Run Treatment A first.

This is important: B/C must not be tuned against individual baseline failures after seeing task results unless that tuning is explicitly recorded as a second experiment.

### Stage 2 — Implement Treatment B

Build the semantic index/resolver from repository facts.

Do not restructure implementation merely to make the index easier.

### Stage 3 — Run B

Use the same task set and controls.

### Stage 4 — Implement Treatment C

Restructure the selected semantic slice using the pre-declared AI-native principles.

Record every structural decision.

### Stage 5 — Run C

Use the same task set and controls.

### Stage 6 — Analysis

Compare:

```text
A vs B → value of semantic resolution
B vs C → value of code shape/locality beyond metadata
A vs C → end-to-end value of the complete treatment
```

### Stage 7 — Conclusion

Each hypothesis must be classified:

```text
Supported
Partially supported
Not supported
Inconclusive
```

The experiment is not complete until `conclusion.md` contains a written conclusion.

## Anti-bias rules

- Do not delete failed runs.
- Do not change a task after seeing how one treatment handles it; create a new experiment revision instead.
- Do not add B/C metadata that directly states the solution to a particular task.
- Do not use implementation paths in the task prompt.
- Do not use composite productivity score without publishing component metrics.
- Report regressions as well as gains.
- If Treatment C makes build or maintenance harder, count that cost.

## Setup record

The frozen Nession staging commit was:

```text
0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664
Merge pull request #880 from BestNathan/fix/extension-relay-auth
```

At setup time, the three research branches were created directly from that SHA and did not modify `staging`.
