# AI-Native Codebase: Code Shape, Retrieval, and Productivity Experiment

> Status: Active research / experiment planned.
>
> This note studies a narrower question inside Agent-Native Repository Architecture:
>
> **What kind of codebase lets an AI agent add and modify software with less search, less ambiguity, less context, fewer retries, and more reliable verification?**
>
> The goal is not to make code unusual for its own sake. The goal is to optimize the software production system for AI workers.

## 1. Core thesis

The repository itself is part of the agent harness.

A coding model does not work against "code" in the abstract. It works inside an environment composed of:

```text
repository structure
+ names
+ contracts
+ dependencies
+ search tools
+ compiler feedback
+ tests
+ runtime observations
+ history
```

If this environment is noisy, ambiguous, implicit, or expensive to navigate, stronger models still waste reasoning and tool calls reconstructing information that the repository could have exposed directly.

The working thesis is:

> **AI-native code should optimize addressability, locality, determinism, and feedback quality before optimizing human aesthetic preferences such as minimal line count or clever abstraction.**

The long-term objective is measurable productivity:

```text
AI software productivity
=
correct useful changes
/
(context + search + inference + retries + verification cost)
```

Human readability remains valuable, but it is not the primary optimization target when it conflicts with machine efficiency.

## 2. The current failure mode: search as guessing

A typical coding agent receives:

```text
"Fix terminal session reconnect."
```

It then performs something like:

```text
grep "session"
grep "reconnect"
glob "**/*terminal*"
read
read
read
infer
```

This is a probabilistic information-retrieval loop.

A word such as `session` may match:

```text
Session
SessionService
SessionPage
SessionConfig
create_session
session_id
tmux session
terminal session
HTTP session
tests
docs
comments
```

Even semantic search only upgrades lexical similarity into semantic similarity. It does not create a stable identity.

The desired transition is:

```text
search
  ↓
semantic search
  ↓
resolution
```

Instead of asking:

```text
"Which files look relevant?"
```

the workspace should increasingly answer:

```text
"What semantic capability owns this behavior, what does it depend on, and what evidence proves it?"
```

## 3. Stable semantic addresses

A capability should have a canonical identity independent of file location.

Example:

```text
capability://terminal/session/reconnect
```

That identity can resolve to:

```text
Capability:
  terminal.session.reconnect

Contract:
  protocol/session_reconnect.rs

Implementation:
  features/terminal/reconnect.rs

State:
  terminal/session_state.rs

Tests:
  tests/terminal/reconnect/*

DependsOn:
  - transport.websocket
  - tmux.attach

UsedBy:
  - web.terminal
  - cli.attach

Invariants:
  - reconnect MUST reuse the existing tmux session
  - reconnect MUST preserve terminal history
  - reconnect MUST be idempotent
```

The key separation is:

```text
stable semantic identity
!=
physical file path
```

Files may move. Implementations may be regenerated. The semantic address remains stable.

This lets historical knowledge, task routing, tests, evidence, and change impact attach to an identity that survives refactors.

## 4. One concept, one authority

Agent retrieval becomes unreliable when the same fact is authored in many places.

Example:

```text
backend/config.rs       30min
frontend/constants.ts   1800000
docs/session.md         30 minutes
helm/values.yaml        1800
test/helper.rs          30 * 60
```

The agent must infer which value is authoritative.

AI-native design should prefer:

```text
session.timeout
      ↓
one canonical definition
      ↓
references / projections / generated representations
```

A useful rule is:

> **Duplicate code may be acceptable. Duplicate authority is not.**

Generated repetition can be cheap and deterministic. Repeated knowledge with multiple editable owners creates ambiguity.

## 5. Behavioral locality

Traditional repositories often organize by technical layer:

```text
controllers/
services/
repositories/
models/
utils/
```

A single behavioral change then crosses many directories.

An agent-friendly alternative is stronger behavioral locality:

```text
session/
  create/
  attach/
  reconnect/
  terminate/
```

A behavior may expose a local semantic closure:

```text
unit.yaml
contract.rs
implementation.rs
state.rs
tests.rs
```

The objective is not "put everything in one file."

The objective is:

> **Minimize the amount of unrelated repository state that must be loaded to make one correct change.**

This suggests a new architecture metric:

```text
change context radius
```

A good unit has a small radius: the agent can understand its contract, dependencies, implementation, invariants, and tests without traversing a large fraction of the repository.

## 6. Unit as the work object

The file is a storage primitive. It does not need to remain the agent's primary work primitive.

Instead of:

```text
Read(file)
Search(text)
ReplaceText(file)
```

an agent-native workspace could expose:

```text
ResolveCapability(...)
GetUnit(...)
InspectDependency(...)
PatchUnit(...)
ValidateUnit(...)
GetImpact(...)
```

A unit could be represented as:

```yaml
id: terminal.session.reconnect

provides:
  - capability://terminal/session/reconnect

consumes:
  - capability://terminal/session/lookup
  - capability://transport/ws/send

contracts:
  - protocol://session/reconnect/v2

state:
  reads:
    - session.connection_state
  writes:
    - session.connection_state

invariants:
  - existing tmux session must be reused
  - history must survive reconnect
  - reconnect must be idempotent

tests:
  - reconnect_existing_session
  - reconnect_after_ws_drop
  - reconnect_is_idempotent
```

The filesystem can remain the storage backend while the agent works against a semantic object model.

## 7. Repository indexes should be first-class

Today an agent repeatedly reconstructs repository knowledge:

```text
new task
  ↓
grep / glob / read
  ↓
reconstruct mental model
```

This is similar to performing a full table scan for every database query.

An AI-native repository should support derived indexes:

```text
Repository
   │
   ├── Symbol Index
   ├── Capability Index
   ├── Contract Index
   ├── Dependency Graph
   ├── State Ownership Index
   ├── Invariant Index
   ├── Test / Evidence Index
   └── Change History Index
```

A task can then execute:

```text
Task
  ↓
Resolve affected capabilities
  ↓
Traverse dependency graph
  ↓
Load minimal semantic closure
  ↓
Modify
  ↓
Validate affected evidence
```

The repository becomes queryable rather than merely searchable.

## 8. Prefer low semantic entropy over low line count

AI-native code may value explicitness differently from human-oriented style.

For example, this may be easier to reason about:

```rust
struct SessionReconnectHandler;
struct SessionCreateHandler;
struct SessionTerminateHandler;
```

than a deeply generic pipeline whose behavior emerges through multiple layers of macros, reflection, generic factories, or runtime registration.

This does not mean "never abstract."

It means abstraction should be evaluated by its effect on:

```text
navigation cost
hidden coupling
change radius
inference depth
verification cost
```

A useful principle is:

> **Token count is not the same as semantic complexity.**

One hundred explicit lines may be easier for an agent to modify correctly than twenty lines whose behavior depends on six levels of indirection.

The optimization target is closer to:

```text
minimize semantic entropy
```

than:

```text
minimize LOC
```

## 9. Types are feedback channels

A strong type system does more than prevent human mistakes.

For an agent, the compiler is an environment sensor.

Compare:

```rust
async fn reconnect(session: Session) -> Result<Session>
```

with:

```rust
fn reconnect(
    session: DisconnectedSession,
) -> Result<ConnectedSession, ReconnectError>
```

The second interface communicates more state and produces higher-quality repair feedback.

This reframes:

```text
type system
compiler
linter
schema validator
runtime assertion
```

as feedback infrastructure for autonomous coding.

The design question becomes:

> What information should be encoded into executable constraints so an agent can discover mistakes through the environment rather than through prose reasoning alone?

## 10. Invariants should be executable

A comment such as:

```text
"Reconnect should not create a new tmux session."
```

is information.

An executable invariant is feedback.

Conceptually:

```text
invariant://terminal/session/reconnect/reuse-existing-tmux
```

with a deterministic check:

```text
new_tmux_sessions == 0
```

The coding loop becomes:

```text
Agent change
   ↓
compiler / tests / invariants / runtime observation
   ↓
feedback
   ↓
repair
   ↓
evidence closure
```

This is the repository as a closed-loop environment rather than a passive source tree.

## 11. Change impact should be resolvable

After a change to:

```text
terminal.session.reconnect
```

the workspace should be able to answer:

```text
Direct impact:
  web.terminal.connection
  cli.attach

Transitive impact:
  terminal.workspace.restore

Required evidence:
  invariant: reconnect.reuses_tmux
  test: reconnect_ws_disconnect
  contract: session.protocol.v3
```

The ideal loop is:

```text
edit
  ↓
impact analysis
  ↓
selective verification
  ↓
evidence
```

rather than:

```text
edit
  ↓
run everything
  ↓
hope failures explain the cause
```

## 12. The produced artifact is change + evidence

The agent's output should not be defined only as a diff.

A stronger completion object is:

```text
Change:
  terminal.session.reconnect@gen42

Evidence:
  compiler: pass
  unit tests: pass
  invariant:
    duplicate_tmux == false
  integration:
    reconnect_after_ws_drop == pass
  benchmark:
    reconnect_latency < threshold
```

The operational goal becomes:

> **Produce a correct change with sufficient evidence.**

This also changes the human role.

Humans should increasingly review:

```text
intent
boundaries
contracts
invariants
policy changes
risk escalation
outcomes
```

instead of attempting to line-review every generated implementation at machine production speed.

## 13. Working AI-friendliness model

A preliminary model is:

```text
AI Friendliness
≈
(Addressability × Locality × Feedback Quality × Determinism)
/
(Ambiguity × Context Cost × Search Noise × Repair Cost)
```

This is not yet a formal metric.

The experiment below exists to determine which of these terms are measurable and whether improving them causes real productivity gains.

---

# Experiment Goal: Prove or Disprove the Repository-Architecture Hypothesis

## 14. Goal

Narness should not graduate these ideas into canonical architecture based on intuition alone.

The research target is:

> **Empirically determine whether an agent-native repository representation improves coding throughput and retrieval reliability for the same model and the same software tasks.**

The experiment must produce:

1. a reproducible setup;
2. a recorded execution process;
3. raw and aggregated measurements;
4. failure analysis;
5. a written conclusion, including negative or mixed results.

The experiment is incomplete until a conclusion is recorded.

## 15. Primary hypotheses

### H1 — Retrieval precision

Stable semantic addresses and derived repository indexes reduce irrelevant exploration.

Expected direction:

```text
irrelevant files read ↓
false-positive search results ↓
time to first relevant unit ↓
```

### H2 — Retrieval recall

Explicit dependency and capability relationships reduce missed affected code.

Expected direction:

```text
missed consumers ↓
missed contracts ↓
missed tests / invariants ↓
```

### H3 — Context efficiency

Behavioral locality and semantic resolution reduce the context required before the first correct edit.

Expected direction:

```text
context tokens ↓
tool calls ↓
files opened ↓
```

### H4 — Change quality

Explicit contracts, types, and executable invariants improve first-pass correctness.

Expected direction:

```text
patch attempts ↓
failed validation loops ↓
regressions ↓
```

### H5 — End-to-end productivity

The architecture increases successful useful changes per unit cost, not merely search quality.

Expected direction:

```text
time to evidence closure ↓
compute / token cost ↓
task success rate ↑
```

## 16. Experimental treatments

Use the same frozen code snapshot and derive controlled variants.

### A — Baseline repository

The existing repository as an agent sees it today.

Allowed navigation:

```text
filesystem
grep
glob
language-server functions if already available
existing documentation
existing tests
```

### B — Semantic-index treatment

Keep the implementation physically unchanged.

Add only:

```text
stable semantic capability IDs
unit manifests
dependency / consumer edges
contract ownership
test / invariant mappings
resolver interface
```

This isolates the value of resolution and metadata from physical restructuring.

### C — Agent-native structure treatment

Starting from the same behavior, additionally introduce:

```text
behavioral locality
explicit canonical ownership
reduced accidental aliases
bounded abstraction depth where justified
executable invariants
selective evidence routing
```

This tests the combined architectural hypothesis.

The sequence A → B → C is important. A single A/B comparison would confound semantic indexing with physical refactoring.

## 17. Candidate real-world target

A good first target should be non-trivial but bounded.

Candidate:

```text
Nession terminal/session reconnect
```

Why it is suitable:

```text
crosses transport, session state, tmux lifecycle, web/CLI consumers, and tests
contains real navigation ambiguity
has observable runtime behavior
has meaningful invariants
can produce bug-fix, extension, and refactoring tasks
```

The exact target repository and commit SHA must be frozen before the experiment starts.

## 18. Task set

Use at least 20 tasks, ideally 24–30.

Tasks should be balanced across:

```text
bug fixes
small feature additions
behavior changes
contract changes
refactors
test additions
failure diagnosis
impact-analysis-only tasks
```

Each task must have a hidden gold record prepared before agent execution:

```yaml
task_id: reconnect-07
expected_capabilities:
  - terminal.session.reconnect
required_touch_set:
  - ...
allowed_optional_touch_set:
  - ...
required_invariants:
  - ...
required_tests:
  - ...
acceptance_command:
  - ...
```

The gold record is used only for evaluation, not supplied to the agent.

## 19. Controlled variables

Keep these fixed across treatments:

```text
model name and exact version
thinking / reasoning setting
system prompt
agent harness
tool availability, except the treatment-specific resolver
context window
time budget
token / compute budget
task statement
starting commit
build environment
test environment
network policy
retry policy
```

Randomize task order to reduce learning and temporal effects.

If the model provider cannot guarantee an identical backend over the experiment period, record timestamps and model identifiers and run treatments close together.

## 20. Measurements

### Navigation

Record:

```text
time to first relevant unit/file
first-hit correctness
grep/search calls
glob calls
files opened
unique files opened
semantic resolver calls
dependency traversals
```

### Retrieval quality

For every loaded artifact classify it against the hidden gold set:

```text
relevant
adjacent but useful
irrelevant
```

Compute:

```text
navigation precision
navigation recall
irrelevant-context ratio
false-positive retrieval rate
false-negative affected-unit rate
```

"Search did not retrieve the wrong thing" must be measured, not asserted.

### Context and inference

Record when available:

```text
input tokens
output tokens
reasoning tokens
cached tokens
number of model turns
```

### Change process

Record:

```text
time to first edit
number of patches
reverted patches
files changed
semantic units changed
out-of-scope edits
compiler failures
test failures
repair loops
```

### Completion

Record:

```text
task success
acceptance tests
invariants
regressions
time to evidence closure
total wall time
total model cost
```

## 21. Key derived metrics

### Search noise

```text
search_noise
=
irrelevant artifacts loaded
/
all artifacts loaded
```

### Context acquisition cost

```text
context_acquisition_cost
=
tool calls before first valid edit
+ normalized input tokens before first valid edit
```

### Change localization

```text
change_localization
=
required semantic units touched
/
all semantic units touched
```

### Repair efficiency

```text
repair_efficiency
=
successful evidence closure
/
failed validation iterations + 1
```

### End-to-end productivity

A candidate composite measure:

```text
productive_change_rate
=
accepted tasks
/
(total wall time × normalized compute cost)
```

Do not use the composite score alone. Publish the underlying measurements so a favorable aggregate cannot hide a regression in correctness.

## 22. Experimental procedure

For each treatment and task:

```text
1. Reset to the frozen starting state.
2. Start a fresh agent session.
3. Record treatment, model, harness, task ID, and environment.
4. Give the identical task statement.
5. Capture every tool call and model turn.
6. Capture every file/unit loaded.
7. Capture all edits and validation attempts.
8. Run the predefined acceptance suite.
9. Record final evidence.
10. Reset before the next run.
```

Prefer multiple runs per task if cost permits.

At minimum, repeat tasks where stochastic variance or anomalous failures could change the conclusion.

## 23. Process log

The experiment must maintain an append-only run log.

Suggested schema:

```text
run_id
task_id
treatment
repository_sha
model
model_version
harness_version
started_at
ended_at
tool_calls
search_calls
files_read
relevant_files_read
irrelevant_files_read
input_tokens
output_tokens
reasoning_tokens
patch_count
validation_failures
task_success
evidence_complete
notes
```

Raw traces should be retained when practical so aggregate results remain auditable.

## 24. Failure analysis

A failed task should be classified by cause.

Suggested taxonomy:

```text
R1 target not found
R2 wrong target selected
R3 important dependency missed
R4 contract misunderstood
R5 invariant missed
R6 implementation error
R7 verification gap
R8 feedback was insufficient
R9 tool/runtime failure
R10 task ambiguity
```

The experiment is valuable even if overall success rates are similar.

For example, B may not improve completion rate but may sharply reduce R1/R2 failures, revealing that retrieval improved while implementation remained the bottleneck.

## 25. Analysis protocol

Compare A, B, and C per task and in aggregate.

Report:

```text
median
p25 / p75
mean where meaningful
success counts
failure taxonomy counts
per-task deltas
```

Do not rely only on average wall time because outliers and provider latency can dominate it.

The most important comparisons are:

```text
A vs B:
Does semantic resolution improve retrieval without code restructuring?

B vs C:
Does code shape/locality add value beyond metadata?

A vs C:
Does the complete agent-native treatment improve end-to-end productivity?
```

## 26. Required conclusion

The final report must explicitly choose one of these forms:

```text
Supported
Partially supported
Not supported
Inconclusive
```

for each hypothesis H1–H5.

The conclusion must include:

```text
what improved
what did not improve
what became worse
which treatment caused the change
which tasks benefited most
which tasks did not
what confounders remain
what should be adopted now
what should remain experimental
```

A negative result is a valid research outcome.

No Narness architectural rule should graduate merely because it sounds AI-native.

## 27. Graduation gate

This research should influence canonical Narness architecture only if the experiment produces reproducible evidence of at least one material improvement without an unacceptable correctness regression.

Candidate material improvements include:

```text
substantial reduction in search noise
substantial reduction in context acquisition
higher first-hit target accuracy
fewer missed dependencies
fewer repair loops
lower evidence closure time
higher accepted-task rate
```

The threshold should be set before final analysis, not after seeing the results.

## 28. Research output structure

When execution begins, add:

```text
research/
  ai-native-codebase-and-productivity-experiment.md
  experiments/
    <experiment-id>/
      protocol.md
      tasks/
      gold/
      runs/
      results.md
      conclusion.md
```

The experiment should leave behind both process and conclusion.

The repository should make it possible for a future researcher or agent to reconstruct:

```text
what was tested
how it was tested
what happened
why the conclusion was reached
```

## 29. Current conclusion

No empirical conclusion has been reached yet.

The present conclusion is only methodological:

> **"Repository architecture is part of the agent harness" is a testable hypothesis, not a design truth. Narness should build the experiment, collect evidence, and let the measured coding process decide which agent-native repository ideas graduate into architecture.**

## Active experiment

The first concrete experiment is now frozen against Nession:

- [Nession Terminal / Session Reconnect Experiment Protocol](experiments/nession-terminal-session-reconnect-2026-09/protocol.md)
- [Frozen Task Set](experiments/nession-terminal-session-reconnect-2026-09/tasks/README.md)
- [Hidden Semantic Gold Set](experiments/nession-terminal-session-reconnect-2026-09/gold/README.md)
- [Runs](experiments/nession-terminal-session-reconnect-2026-09/runs/README.md)
- [Results](experiments/nession-terminal-session-reconnect-2026-09/results.md)
- [Conclusion](experiments/nession-terminal-session-reconnect-2026-09/conclusion.md)

The Nession source snapshot is pinned at `0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664`. Three isolated research branches represent baseline, semantic-index, and agent-native-structure treatments.

## Related work

- [Agent-Native Repository Architecture](../README.md)
- [Generational Source Architecture](../design/generational-source-architecture.md)
- [Engineering Surfaces](../../engineering-surfaces/README.md)
- [Change-to-Evidence Planning](../../change-to-evidence-planning/README.md)
- [Harness Engineering](../../harness-engineering/README.md)
