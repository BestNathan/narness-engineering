# Two-Phase Code Localization with System One

## Research question

Can a fast System One model localize code by operating over a bounded, dynamically disclosed read-action space instead of running an open-ended ReAct browsing loop or scoring a pre-expanded representation of the whole file?

Running task:

> Help me optimize the websocket connection implementation.

## Why the previous pipeline was insufficient

Earlier prototypes exposed directory -> file -> line, fixed region, outline, and symbol frontiers. They established three important facts:

1. Transport batching is not semantic progress. Splitting one oversized frontier into many HTTP calls only hides a state-space problem.
2. Directory pruning must be preserved. The file stage may only expose direct files of retained directories.
3. Pre-expanding file interiors is the wrong abstraction. Even symbols can form a huge flat frontier before the model has chosen to inspect those parts of the file.

A file body should therefore appear as an observation produced by a chosen read action.

## Phase 1 — File Locator

~~~text
repository metadata
  -> directory Noul
  -> direct-file metadata
  -> file Noul
  -> bounded PotentialFile[]
~~~

No source body is exposed in Phase 1.

Baseline defaults:

~~~text
directory threshold = 0.50
file threshold      = 0.65
max files           = 16
~~~

These values are intentionally tighter than the original 0.35 / 0.50 pilot and are research parameters rather than claimed optima.

## Phase 2 — Progressive Reader

For each batch of PotentialFile values:

~~~text
stat
  -> ActionSpaceGenerator
  -> Choice
  -> read_file
  -> Observation
  -> append Observation to ReaderState
  -> Noul relevance
  -> update coverage / evidence
  -> ActionSpaceGenerator
  -> repeat
~~~

A line range is an information-gathering action, not a semantic answer candidate.

## ReaderState

~~~text
ReaderState
  goal
  batch_index
  round

  files[]
    path
    phase1_score
    stat
      line_count
      size_bytes
      extension
    coverage[]
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

The read observation is appended before its relevance question is evaluated. The next Choice request sees previous observations and coverage. State therefore changes as a direct consequence of execution.

## Dynamic action frontier

The harness constructs valid actions; the model never invents paths or offsets.

Initial unread file:

~~~text
ReadRange(head)
ReadRange(middle)
ReadRange(tail)
StopFile
~~~

After observations exist, high-relevance observations are merged into disconnected `RelevantRegion[]` hotspots. The frontier is built from several retained hotspots rather than collapsing the file onto one strongest anchor:

~~~text
RelevantRegion #1 -> before / after
RelevantRegion #2 -> before / after
RelevantRegion #3 -> before / after
largest unread gap
StopFile
~~~

The baseline caps the file at three relevant regions and eight total actions, so multi-hotspot preservation does not become whole-file expansion. Regions are ranked by maximum relevance and recency. Low-relevance observations still contribute coverage but do not create local expansion actions.

The generator remains deliberately simple. Future generators may use identifiers, imports, declarations, or LSP information discovered from observations, but should not pre-expand the entire file.

## Multi-file batches

Files are active in fixed-size batches, four by default. One reader round sends one Choice question per active file in one System One request. All questions share the same ReaderState for that batch.

~~~text
file_0 -> choose one action for A
file_1 -> choose one action for B
file_2 -> choose one action for C
file_3 -> choose one action for D
~~~

This is semantic concurrency, not transport batching: the batch defines the files that are simultaneously active and mutually visible in state.

## Decision primitives and confidence

Phase-1 directory/file localization uses Noul because multiple candidates may independently be relevant.

Reader navigation uses Choice because each active file needs one next action. The chosen option probability is compared with a reader-action threshold before execution.

Observed content uses Noul because multiple read ranges may independently contain useful evidence.

~~~text
directory relevance  >= 0.50
file relevance       >= 0.65
read action prob.    >= 0.40
observation relevance>= 0.65
~~~

These thresholds control different failure modes and should be calibrated independently.

## Request topology

The runtime intentionally has no fixed total call count.

Phase 1 currently uses two requests:

~~~text
directory Noul
file Noul
~~~

Each active reader batch then uses at most two requests per round:

~~~text
Choice next actions for all active files
Noul relevance for all newly-read observations
~~~

Call count therefore follows semantic interaction depth and active batches, not source-line count.

## Research studies

### A. Phase-1 threshold calibration

Sweep directory and file thresholds while holding reader settings fixed. Measure relevant-file recall/precision, file frontier size, downstream reads, tokens, and false-prune stage.

### B. Reader confidence calibration

Sweep reader-action threshold independently of observation threshold. Measure discovery failure, wasted reads, evidence precision/recall, and stop reasons.

### C. Multi-file batch size

Compare 1, 2, 4, and 8 files per batch. Measure cross-file decision quality, state size, model calls, token cost, and latency.

### D. Noul versus Choice

Compare the primitives only in decision points that can reasonably be represented both ways. The baseline intentionally uses Noul for independent relevance and Choice for one-next-action selection.

### E. Dynamic action-space quality

Compare the simple range generator against richer observation-driven generators, including identifier-bearing neighbors, import/dependency targets, and syntax/LSP proposals.

## Shared System One harness model

The code reader and Kubernetes demo now share the same core abstraction:

~~~text
State
  -> ActionSpaceGenerator
  -> DecisionPrimitive
  -> Effect
  -> Observation
  -> State transition
~~~

The action space is progressively disclosed by real observations rather than enumerated in full at the start.


## Multi-hotspot trace finding

The first real two-phase trace showed why a single strongest anchor is insufficient. In `crates/nession-agent/src/server/websocket.rs`, the reader found one relevant region at lines 1-140 (0.87), lost local relevance at 141-280 (0.60), then discovered a second relevant region at 1585-1724 (0.74). A strongest-only generator could not expose neighbors of the second hotspot because the first hotspot still had the higher score.

The current baseline therefore treats disconnected high-relevance regions as separate action-space anchors. See [the trace analysis](pilots/nession-websocket-two-phase-trace-analysis-2026-09-23.md).

## Evidence-driven round budget

The fixed four-round baseline can terminate immediately after discovering a useful new hotspot. The reader therefore distinguishes a soft interaction budget from an absolute hard cap:

~~~text
soft rounds = 4
hard rounds = 8
~~~

At or beyond the soft limit, continuation is file-scoped. Every active file must independently produce a new observation whose relevance is at or above the observation threshold to earn its own next round. Files that fail this test stop, while other files in the same batch may continue. The hard limit is unconditional.

~~~text
round < soft limit
  -> all active files continue normally

round >= soft limit
  -> for each active file:
       new high-relevance observation?
         yes -> file earns one more round
         no  -> stop that file

batch continues while any file remains active

round == hard limit
  -> stop all remaining files regardless of score
~~~

This separates two roles that were previously conflated: the batch is concurrent decision context, while the file owns continuation budget. Continuation remains a consequence of newly observed state and still has a deterministic upper cost bound.

The first experiment should hold thresholds, window size, file batch size, and multi-hotspot logic constant. The target trace case is `server/handler.rs`, where the previous run discovered a new relevant region on round four but could not expose a follow-up action because the hard `max_rounds=4` loop ended.

### File-scoped continuation finding

The first soft/hard implementation granted continuation at batch scope. A high-signal `server_client.rs` observation kept `cli/client/connection.rs` alive for two extra low-value reads. The file-scoped follow-up run 35833457198 corrected this: the CLI file scored 0.64 at round four and stopped immediately, while `server_client.rs` independently continued through rounds five, six, and seven.

See [the file-scoped round budget baseline](pilots/nession-websocket-file-scoped-round-budget-2026-09-23.md).

## Accuracy finding: static Phase-1 frontier

A same-revision Claude Code + `ds` reference run showed that the reader has strong local accuracy once it reaches a primary file, but the static Phase-1 file frontier creates irreversible false negatives.

For the websocket task, System One covered 4/5 Claude primary files and 16/20 primary evidence regions (85.8% of reference primary evidence lines). The missed primary file was `MessageRouter.ts`, scored 0.64 at rank 21. Yet the first high-confidence observation from `WebSocketService.ts` explicitly imports `./MessageRouter` and `./types`.

This changes the preferred next design from 'lower Phase-1 confidence until all dependencies fit' to 'allow Phase 2 observations to disclose new grounded cross-file actions'. Candidate action types include `InspectDependency`, `FindReferences`, and `InspectDefinition`. Such actions should remain harness-generated and bounded; System One only selects among valid discovered actions.

See [the Claude reference accuracy study](pilots/nession-websocket-claude-reference-accuracy-2026-09-23.md).
