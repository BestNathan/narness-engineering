# System One Code Locator

> Experimental research project. This is a localization harness, not a code-changing agent.

Code Locator uses a two-phase architecture with progressive state-space disclosure.

## Phase 1 — File Locator

Phase 1 scores repository structure and direct-file metadata without exposing source bodies:

~~~text
repository
  -> directory Noul
  -> direct-file metadata
  -> file Noul
  -> PotentialFile[]
~~~

Current defaults:

~~~text
directory threshold = 0.50
file threshold      = 0.65
~~~

There is no Phase-1 top-k file cap. Every file that passes the Phase-1 file threshold becomes part of the Phase-2 initial ReaderState.

The directory stage enumerates the repository tree once. The file stage only exposes direct files of retained directories; it never recursively walks selected directories again.

## Phase 2 — Global Progressive Reader

Potential files are not ordered into harness-defined batches and are not pre-expanded into lines, regions, outlines, or symbols.

All retained files enter one shared ReaderState with file stat metadata:

~~~text
PotentialFile[]
  -> stat(file)
  -> one shared ReaderState
~~~

Each scheduler epoch begins with a global file frontier:

~~~text
all eligible files
  -> one Noul question per file in one System One request
  -> score: "should this file receive a read action now?"
  -> activate every file above reader-file-activation threshold
~~~

Only activated files receive per-file read-action Choice questions:

~~~text
activated files
  -> bounded ReadRange / StopFile actions
  -> Choice
  -> read_file
  -> Observation enters ReaderState
  -> Noul observation relevance
  -> update coverage / hotspots / budgets
  -> rescore the complete global file frontier
~~~

An unselected file is deferred, not discarded. It remains in state and can become active in a later scheduler epoch after observations change the state.

This removes two harness decisions from the previous baseline:

~~~text
no Phase-1 max-files cap
no fixed file batch ordering
~~~

## Reader controls

~~~text
reader file activation threshold = 0.65
read window                      = 140 lines
soft reads per file              = 4
hard reads per file              = 8
read-action probability          = 0.40
observation relevance            = 0.65
~~~

File activation, read-action confidence, and observation relevance are different decisions and have independent thresholds.

## ReaderState

~~~text
ReaderState
  goal
  scheduler round

  files[]
    path
    Phase-1 score
    stat { line_count, size_bytes, extension }
    coverage[]
    read_count
    activation_count
    last_activation_score
    stopped / stop_reason

  observations[]
    path / line range
    content
    action probability
    relevance score
~~~

After read_file returns, content is appended to ReaderState before observation relevance is evaluated. The next global file scheduling request sees the updated state.

## Dynamic read actions

For an unread activated file, stat creates a coarse local action frontier:

~~~text
ReadRange(head)
ReadRange(middle)
ReadRange(tail)
StopFile
~~~

After observations exist, high-relevance observations are merged into bounded disconnected RelevantRegion hotspots. The file can expose before/after actions around several hotspots plus one exploration-gap action.

Source ranges are information-gathering actions, not precomputed semantic answer candidates.

## File-owned read budget

Read budgets belong to files rather than scheduler epochs.

A file gets four normal reads. At or beyond the soft limit, a new high-relevance observation earns another read. A low-relevance observation stops that file. Eight reads is the unconditional per-file hard cap.

This is independent of global scheduling: a file can be deferred for several scheduler epochs without consuming its read budget.

## Decision primitives

~~~text
Phase-1 candidate relevance     -> Noul
Phase-2 file activation         -> Noul
Next read action for a file     -> Choice
Observed-content relevance      -> Noul
~~~

The primitive is selected by decision semantics.

## Run

Offline fixture:

~~~bash
python3 research/code-locator/src/system_one_code_locator.py \
  research/code-locator/fixtures/repository \
  "Help me optimize the websocket connection implementation" \
  --offline-decider
~~~

Important controls:

~~~text
--directory-threshold
--file-threshold
--reader-file-activation-threshold
--reader-window-lines
--reader-soft-reads
--reader-hard-reads
--reader-action-threshold
--observation-threshold
~~~

Legacy batch/top-k CLI flags are accepted only for compatibility and are ignored.

## Claude Code cross-trace

The repository also contains a manual cross-trace workflow:

~~~text
.github/workflows/system-one-code-locator-accuracy.yml
~~~

Despite the historical filename, the workflow is now an observational comparison, not an accuracy oracle.

Both systems receive the same task and exact subject revision. Claude Code runs through the existing `ds` environment with read-only repository tools.

Claude uses two fresh sessions with different responsibilities:

~~~text
Session A: localization only
  -> repository search / Read / Grep / Glob / Bash
  -> final files + evidence ranges
  -> no confidence output

Session B: confidence only
  -> new session
  -> no repository tools
  -> sees immutable Session-A draft + exact evidence source
  -> assigns overall / file / evidence confidence
~~~

The Claude artifact preserves both stages:

~~~text
localization.raw.jsonl
localization-draft.json
execution-path.json
execution-summary.md
localization-manifest.json

confidence.raw.jsonl
confidence-manifest.json
confidence-summary.md

localization-result.json
manifest.json
~~~

The confidence session cannot alter Session A's file set or evidence ranges; structural drift fails the workflow.

Claude Code is not treated as ground truth or as an optimization target for System One. File/range agreement is retained only as descriptive research data.

## Current global-scheduler baseline

Real run `35839323377` on the Nession websocket task retained 18 Phase-1 files and allowed System One to schedule them globally.

The first scheduler epoch activated only three files:

~~~text
0.86 server websocket
0.81 WebSocketService.ts
0.78 agent websocket
~~~

The run used:

~~~text
12 model calls
8 reads
3 unique files read
4 scheduler epochs
3.78s elapsed
~~~

Claude Code independently used 42 tool calls over 43 turns. The difference in search trajectories is recorded rather than treated as a winner/loser result.

See:

~~~text
docs/pilots/nession-websocket-global-scheduler-cross-trace-2026-09-23.md
~~~

## Research directions

1. Separate file activation from an explicit task-sufficiency / stop decision.
2. Observation-driven cross-file actions such as InspectDependency / FindReferences / InspectDefinition.
3. Phase-1 and Phase-2 threshold studies using score snapshots rather than rerun drift.
4. ReaderState compaction as observations accumulate.
5. Noul versus Choice where the semantic decision can reasonably use either primitive.
6. Multi-task cross-traces and later human-reviewed gold sets when absolute accuracy is needed.

See `docs/design.md` for the detailed model.


## Canonical localization result

Both System One and Claude Code emit the same final-result contract:

~~~text
localization-result.json
~~~

It records final valuable files, file-level confidence, valuable source ranges, range-level confidence/reason, exact source content, and execution-cost metrics.

Cost fields include elapsed time, token usage, model calls / turns / tool calls when available, provider USD cost when reported, and per-stage breakdowns.

Confidence values preserve their source semantics rather than pretending to be calibrated across models. For Claude, confidence is produced only by the second fresh session after localization is frozen. See `docs/localization-result.md`.
