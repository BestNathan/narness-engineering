# Two-Phase Code Localization with System One

## Research question

Can a fast System One model localize code by operating over a bounded, progressively disclosed state/action space without requiring an open-ended ReAct loop or a harness-defined traversal order?

Running task:

> Help me optimize the websocket connection implementation.

## Core principle

The harness should own validity and bounds, but should avoid making semantic navigation decisions that the model itself can make.

The current abstraction is:

~~~text
State
  -> ActionSpaceGenerator
  -> DecisionPrimitive
  -> Effect
  -> Observation
  -> State transition
~~~

The state/action space is progressively disclosed by real observations.

## Why earlier variants were rejected

### Transport batching

Splitting one large candidate set into batches of HTTP requests does not create semantic progress. The original pilot reached 598 model calls because transport batching and per-file line scoring scaled with candidate count.

### Recursive file expansion

Once the directory stage has enumerated every repository directory, selected directories must expose direct files only. Recursively walking selected directories reintroduces descendants that the previous decision already rejected.

### Lines / fixed regions / flat symbols

Pre-expanding file bodies into line, chunk, region, outline, or all-symbol candidate sets exposes too much interior state before the model has decided to inspect it. Source content should appear as an observation produced by an information-gathering action.

### Fixed file batches

A fixed batch adds another harness semantic decision:

~~~text
these four files first
then these four files
then these four files
~~~

Nothing in the task establishes that this ordering is meaningful. The current baseline therefore has no harness-defined file batches.

## Phase 1 — File Locator

~~~text
repository metadata
  -> directory Noul
  -> direct-file metadata
  -> file Noul
  -> PotentialFile[]
~~~

No source body is exposed in Phase 1.

Current defaults:

~~~text
directory threshold = 0.50
file threshold      = 0.65
~~~

There is no Phase-1 max-files cap. Every file above the file threshold becomes part of the Phase-2 initial state.

Phase 1 is therefore a coarse state-space boundary, not a ranking that dictates read order.

## Phase 2 — Global Progressive Reader

All retained Phase-1 files are stat'ed locally and placed in one shared ReaderState.

~~~text
PotentialFile[]
  -> stat
  -> ReaderState.files[]
~~~

A scheduler epoch begins by exposing the complete eligible file frontier to System One.

~~~text
ReaderState
  -> Noul(file A: read now?)
  -> Noul(file B: read now?)
  -> Noul(file C: read now?)
  -> ...
  -> activated file subset
~~~

All file questions are sent in one System One request and share the same state.

The activation score answers a relative temporal question:

> Is reading this file now likely to add useful information, given the complete current state?

It is intentionally distinct from the Phase-1 file score.

An unselected file is deferred, not rejected. It remains in ReaderState and can be rescored after other reads add observations.

## Local file action space

Only globally activated files receive local read-action choices.

For an unread file:

~~~text
ReadRange(head)
ReadRange(middle)
ReadRange(tail)
StopFile
~~~

After observations exist, high-relevance observations are merged into disconnected `RelevantRegion[]` hotspots.

~~~text
RelevantRegion #1 -> before / after
RelevantRegion #2 -> before / after
RelevantRegion #3 -> before / after
largest unread gap
StopFile
~~~

The frontier is bounded to at most eight actions per file.

System One chooses one next action per activated file through Choice. Multiple activated files can therefore be read in the same scheduler epoch without the harness deciding a fixed batch membership.

## ReaderState

~~~text
ReaderState
  goal
  scheduler_round

  files[]
    path
    phase1_score
    stat
      line_count
      size_bytes
      extension
    coverage[]
    read_count
    activation_count
    last_activation_score
    stopped
    stop_reason

  observations[]
    id
    path
    start_line
    end_line
    content
    action_probability
    relevance
~~~

A read observation is appended before its relevance question is evaluated. The next file-scheduling request sees the updated observations and coverage.

## File-owned read budget

A scheduler epoch is not a read budget unit. A file can be deferred for several epochs without consuming budget.

Current per-file budget:

~~~text
soft reads = 4
hard reads = 8
~~~

At or beyond four reads:

~~~text
new observation >= observation threshold
  -> file remains eligible

new observation < observation threshold
  -> stop that file
~~~

At eight reads the file stops unconditionally.

This preserves the earlier file-scoped continuation finding while removing batch ownership completely.

## Decision primitives

~~~text
Phase-1 directory relevance  -> Noul
Phase-1 file relevance       -> Noul
Phase-2 file activation      -> Noul
Per-file next read action    -> Choice
Observation relevance        -> Noul
~~~

Each threshold controls a different failure mode:

~~~text
directory relevance       0.50
Phase-1 file relevance    0.65
file activation           0.65
read-action probability   0.40
observation relevance     0.65
~~~

These are research parameters rather than claimed optima.

## Request topology

Phase 1:

~~~text
1. directory Noul
2. file Noul
~~~

Each Phase-2 scheduler epoch can then use:

~~~text
3. global file-priority Noul
4. local read-action Choice for activated files
5. observation-relevance Noul for produced observations
~~~

There is no fixed total call count. Calls follow state transitions rather than candidate-array transport batching.

## Real global-scheduler trace

Run `35839323377` used the same Nession revision and websocket task as the earlier experiments.

Phase 1 retained 18 files — all files above threshold, with no top-k truncation.

The first Phase-2 global scheduling request selected only:

~~~text
0.86 crates/nession-server/src/server/websocket.rs
0.81 web/src/platform/socket/WebSocketService.ts
0.78 crates/nession-agent/src/server/websocket.rs
~~~

The other 15 files remained in state but were deferred.

Epoch 2 selected the same three. Epoch 3 selected only `WebSocketService.ts` and the agent websocket file. Epoch 4 selected none and the scheduler stopped.

Aggregate:

~~~text
18 Phase-1 files in initial ReaderState
4 scheduler epochs
72 file-priority decisions
8 file activations
8 reads
3 unique files read
12 model calls
195,977 input tokens
3.78s elapsed
~~~

This trace demonstrates that fixed file batches are unnecessary for the model to form a narrower read frontier.

It does not establish that the three-file trajectory is correct.

## Activation versus sufficiency

The current baseline stops when no file activation score meets the activation threshold.

That means one threshold currently answers two distinct questions:

~~~text
FilePriority(path):
  should this file be read now?

TaskSufficiency(state):
  is there enough evidence to stop exploring?
~~~

Those are not obviously equivalent.

A future experiment should separate them. For example, a scheduler could defer all current files yet still decide that exploration should continue via a different action, dependency discovery, or another frontier.

This question should be evaluated independently rather than tuning activation because another agent explored more files.

## Observation-driven cross-file discovery

Phase 1 remains a static frontier. Observations can reveal imports, identifiers, types, modules, or runtime relationships that point to files outside that frontier.

Potential grounded actions include:

~~~text
InspectDependency(path)
InspectDefinition(identifier)
FindReferences(identifier)
SwitchToDiscoveredFile(path)
~~~

The harness should derive valid actions from observed repository facts; System One should choose among those actions.

This preserves a high-confidence Phase 1 while allowing the state space to grow from real evidence.

## Claude Code cross-trace methodology

Claude Code + `ds` is recorded as a separate System-2 trajectory, not ground truth and not an optimization target.

The manual workflow:

~~~text
.github/workflows/system-one-code-locator-accuracy.yml
~~~

uses the historical filename but now records a cross-trace.

For Claude it saves:

~~~text
claude.raw.jsonl
execution-path.json
execution-summary.md
reference.json
manifest.json
~~~

The raw stream preserves every Claude Code event. The normalized execution path records ordered Read / Grep / Glob / Bash calls, inputs, errors, and result-size/preview metadata.

Run `35839323377` recorded:

~~~text
42 Claude tool calls
  24 Read
   2 Grep
  16 Bash
43 turns
79.8s
~~~

Its sequence progressed from repository inspection and broad websocket grep to server/agent websocket files, connection clients, web transport, session runtime, MessageRouter, handler/broker/registry paths, and additional targeted regions.

That trajectory can be compared with System One's much narrower global-scheduler trajectory without assuming that either final file set is the correct answer.

See:

~~~text
pilots/nession-websocket-global-scheduler-cross-trace-2026-09-23.md
~~~

## Historical findings retained

### Multi-hotspot

A single strongest relevance anchor prevented a second high-relevance region from expanding. The reader now retains several disconnected `RelevantRegion[]` anchors.

### Fixed round budget

A hard four-round loop could stop immediately after discovering a new hotspot. Read continuation became evidence-driven and file-scoped.

### Batch-scoped continuation

One high-signal file could previously keep low-value sibling files alive. Continuation ownership was moved to the file.

These findings remain valid under the global scheduler; only the batch concept itself has now been removed.

## Research studies

1. File activation versus explicit task sufficiency / stop.
2. Observation-driven cross-file discovery.
3. Phase-1 and activation threshold replay on frozen score snapshots.
4. ReaderState compaction as raw observations accumulate.
5. Noul versus Choice for semantically equivalent decision points.
6. Multi-task cross-traces between System One and System 2 agents.
7. Human-reviewed gold datasets only when an absolute accuracy claim is required.

## Shared harness model

The code reader and Kubernetes System One experiment converge on the same abstraction:

~~~text
State
  -> grounded ActionSpace
  -> System One decision
  -> Effect
  -> Observation
  -> State transition
~~~

The harness provides valid bounded actions. The model decides which semantic direction to take.
