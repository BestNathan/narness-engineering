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

After observations exist:

~~~text
ReadRange(after strongest observation)
ReadRange(before strongest observation)
ReadRange(largest unread gap)
StopFile
~~~

The baseline generator is deliberately simple. Future generators may use identifiers, imports, declarations, or LSP information discovered from observations, but should not pre-expand the entire file.

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
