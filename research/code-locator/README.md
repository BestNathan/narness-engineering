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

## Phase 2 — Independent File Range Runtimes

Phase 2 no longer puts every retained file into one shared System One state.

The TypeSafe request context is bounded, and files do not need cross-file
semantic comparison during range localization. Each Phase-1 file therefore
owns an independent FileRuntime:

~~~text
PotentialFile[]
  -> FileRuntime(file A)
  -> FileRuntime(file B)
  -> FileRuntime(file C)
  -> ...
~~~

Each FileRuntime sees only:

~~~text
goal
this file's metadata
this file's coverage
this file's raw observations
this file's current range actions
~~~

No observation from one file is exposed to another file.

The Harness does not parse source text. It does not use AST, LSP, symbols,
imports, keywords, or semantic chunks.

### Dynamic range actions

For an unread file:

~~~text
ReadRange(head)
ReadRange(middle)
ReadRange(tail)
StopFile
~~~

After reads exist, the Harness mechanically derives:

~~~text
ReadRange(expand_before)
ReadRange(expand_after)
ReadRange(jump)
StopFile
~~~

`jump` probes the midpoint of large unread gaps. `before/after` expand
around ranges selected in the previous epoch.

All actions are grounded only from line count, coverage, and runtime history.

### Action scoring and concurrency

Each file-local request contains two decision primitives:

~~~text
Choice:
  StopFile vs ContinueFile

Noul:
  one utility score per ReadRange
~~~

The Stop/Continue Choice is the control-flow decision. It is not compared
numerically with ReadRange utility.

Current ReadRange threshold:

~~~text
parallel action threshold = 0.65
~~~

The threshold controls ReadRange concurrency, but control-flow and concrete
read utility are now reconciled when they disagree:

~~~text
if Choice == StopFile and best ReadRange >= threshold:
  ask System One to resolve StopFile vs that concrete ReadRange

if Choice == ContinueFile and every ReadRange < threshold:
  ask System One to resolve StopFile vs the best concrete ReadRange

if resolved choice == StopFile:
  model_stop

if resolved choice == ReadRange:
  execute that explicitly authorized read

otherwise:
  execute all non-overlapping ReadRanges >= threshold
~~~

There is no unconditional low-score top-1 fallback. Low read scores still do
not cause Harness-defined termination; they trigger a second explicit model
control decision.

### Stop semantics

`StopFile` is an explicit model action. The prompt tells System One to raise
its stop score when current evidence is sufficient to judge the file and
further reads are unlikely to materially improve localization.

Mechanical terminal states remain separate:

~~~text
model_stop
action_space_exhausted
budget_exhausted
error / cancelled
~~~

### DecisionView versus durable state

Each FileRuntime keeps complete durable observations, but the request
DecisionView is mechanically bounded. It includes recent complete raw
observations up to a character budget plus full coverage metadata.

The DecisionView also exposes a bounded exploration-yield history: recent
control choices, maximum ReadRange utility, selection mode, and the current
consecutive low-utility streak. This lets StopFile reason about diminishing
returns without the Harness interpreting source semantics.

This is context management and runtime telemetry, not semantic summarization.

### Result evidence

After a FileRuntime terminates, observed ranges are scored for result relevance.
Those post-loop scores do not affect navigation or stopping.

## Run the range runtime

~~~bash
python3 research/code-locator/src/system_one_range_runtime.py \
  <repository> \
  "Help me optimize the websocket connection implementation" \
  --window-lines 140 \
  --parallel-threshold 0.65 \
  --evidence-threshold 0.65 \
  --max-jumps 2 \
  --max-file-epochs 32
~~~

The dedicated manual workflow is:

~~~text
.github/workflows/system-one-range-runtime-v0.yml
~~~

## Current per-file baseline

Real run `35857120750` on
`BestNathan/nession@b76fe4921a63023a69ce91399328ab53d3526664`:

~~~text
Phase-1 files       17
FileRuntime count   17

model_stop           0
space exhausted     16
budget exhausted     1

reads              138
valuable files      11
evidence regions    46

model calls        145
input tokens  1,316,145
output tokens    19,858
elapsed          33.243s
~~~

Sixteen files reached 100% coverage. The 6,617-line `handler.rs` reached
94.2% coverage before the 32-epoch safety budget.

The important result is architectural: the per-file runtime completed without
the shared-state context overflow. It also showed that current `StopFile`
semantics are conservative; no file stopped early by model choice.

See:

~~~text
docs/pilots/nession-websocket-per-file-range-runtime-v0-2026-09-23.md
~~~

## Claude Code cross-trace

The repository also contains a manual cross-trace workflow:

~~~text
.github/workflows/system-one-code-locator-accuracy.yml
~~~

Despite the historical filename, the workflow is now an observational comparison, not an accuracy oracle.

The System One side now runs the current independent per-file range runtime,
not the historical global progressive reader. Both systems receive the same
task and exact subject revision. Claude Code runs through the existing `ds`
environment with read-only repository tools.

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

## Historical global-scheduler baseline

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

1. Improve `StopFile` semantics without reintroducing Harness-driven stopping.
2. Study range-action generation density: seed / expand / jump geometry.
3. Parallelize independent FileRuntime instances without changing semantics.
4. Phase-1 threshold studies using frozen score snapshots.
5. Bound DecisionView context mechanically while keeping durable FileState complete.
6. Re-run cross-traces using the per-file runtime baseline.
7. Human-reviewed gold datasets only when an absolute accuracy claim is required.

See `docs/design.md` for the detailed model.


## Canonical localization result

Both System One and Claude Code emit the same final-result contract:

~~~text
localization-result.json
~~~

It records the frozen subject repository/revision, final valuable files, file-level confidence, valuable source ranges, range-level confidence/reason, exact source content, and execution-cost metrics. The generic comparator rejects results whose canonical subject identities differ.

Cost fields include elapsed time, token usage, model calls / turns / tool calls when available, provider USD cost when reported, and per-stage breakdowns.

Confidence values preserve their source semantics rather than pretending to be calibrated across models. For Claude, confidence is produced only by the second fresh session after localization is frozen. See `docs/localization-result.md`.


### StopFile Choice baseline

Real run `35864316780` validates the current stop policy:

~~~text
17 FileRuntime instances

model_stop               4
action_space_exhausted  12
budget_exhausted         1

reads                  134
model calls            130
elapsed             25.952s
~~~

The four genuine early stops occurred with unread content still remaining:

~~~text
server/websocket.rs        91.3% coverage
WebSocketService.ts        77.5%
CLI connection.rs          86.0%
web_client_registry.rs     99.3%
~~~

`StopFile` now means the model has enough representative evidence to finalize
the file-level localization result. It does not mean full-file coverage.

See `docs/pilots/nession-websocket-per-file-range-runtime-v0-2026-09-23.md`.


## Experimental localization algorithms

Two additional System One localization strategies are implemented as isolated
experiments and do not replace the current per-file range-runtime baseline.

### A — Explore-Guided Evidence Filtering

Keeps the current FileRuntime state/action-space mechanics, but changes the
decision objective from topical relevance to NEW MATERIAL EVIDENCE. Reads that
repeat an already established fact, add only wrappers/logging/debug plumbing,
or are merely topically related should receive lower value.

~~~text
research/code-locator/src/system_one_evidence_guided_runtime.py
~~~

### B — Adaptive Semantic Zoom Search

Starts with stratified probes across the whole file, uses Choice probabilities
to retain a multi-hotspot beam, keeps an explicit exploration slot, then
recursively splits/refines selected ranges down to a target resolution.

~~~text
research/code-locator/src/system_one_adaptive_zoom.py
~~~

The shared manual workflow runs both algorithms against the same subject and
task:

~~~text
.github/workflows/system-one-localization-algorithms.yml
~~~

See `docs/system-one-localization-algorithms.md` for the full algorithms and
prototype parameters.
