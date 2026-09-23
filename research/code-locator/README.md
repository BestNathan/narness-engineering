# System One Code Locator

> Experimental research project. This is a localization harness, not a code-changing agent.

Code Locator now uses a two-phase architecture.

## Phase 1 — File Locator

Phase 1 scores repository structure and file metadata without exposing source bodies:

~~~text
repository -> directory Noul -> direct files -> file Noul -> PotentialFile[]
~~~

Current baseline controls:

~~~text
directory threshold = 0.50
file threshold      = 0.65
max files           = 16
~~~

The directory stage enumerates the repository tree once. The file stage only exposes direct files of retained directories; it never recursively walks selected directories again.

## Phase 2 — Progressive Reader

Potential files are not pre-expanded into lines, regions, outlines, or symbols. The harness first reads file stat, generates a bounded read-action space, and lets System One decide where to read.

~~~text
PotentialFile[]
  -> stat
  -> dynamic ReadRange actions
  -> Choice
  -> read_file
  -> Observation enters ReaderState
  -> Noul observation relevance
  -> update coverage and scores
  -> generate next action frontier
  -> repeat
~~~

A source range is therefore an information-gathering action, not a precomputed semantic candidate.

## Multi-file reader batches

The reader processes multiple files concurrently. The default batch size is four. In one reader round, the harness creates one Choice question per active file and sends all questions in one System One request. Each file chooses one grounded next action while sharing the batch ReaderState.

Default reader controls:

~~~text
file batch size          = 4
read window              = 140 lines
soft rounds per batch    = 4
hard rounds per batch    = 8
read action threshold    = 0.40
observation threshold    = 0.65
~~~

The action threshold applies to the probability of the selected Choice option. A read below the threshold is not executed. The observation threshold decides whether read content becomes retained final evidence.

## ReaderState

~~~text
ReaderState
  goal
  batch_index / round
  files[]
    path
    Phase-1 score
    stat { line_count, size_bytes, extension }
    coverage[]
    stopped / stop_reason
  observations[]
    path / line range
    content
    action probability
    relevance score
~~~

After read_file returns, the content is appended to ReaderState before System One is asked to score the observation. The next action decision sees the updated observations and coverage.

## Dynamic actions

An unread file starts with a coarse action frontier such as head, middle, tail, and stop. After observations exist, the harness generates actions around bounded high-relevance regions plus an exploration gap. Relevant content therefore increases local reading resolution without requiring the whole file to be expanded up front.

The reader now uses a file-scoped soft/hard round budget. Four rounds is the normal budget. At or beyond the soft limit, each active file must produce a new observation above the observation threshold to earn its own next round. Files that do not earn continuation stop independently, while other files in the same batch may continue. No batch can exceed eight rounds.

## Decision primitives

~~~text
Phase-1 candidate relevance -> Noul
Next read action           -> Choice
Observed-content relevance -> Noul
~~~

The primitive is selected by decision semantics rather than globally choosing Noul or Choice for the whole locator.

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
--phase1-max-files
--reader-file-batch-size
--reader-window-lines
--reader-soft-rounds
--reader-hard-rounds
--reader-action-threshold
--observation-threshold
~~~

## Research directions

1. Phase-1 threshold versus relevant-file recall, precision, and downstream reader cost.
2. Reader-action threshold versus exploratory IO and discovery failure.
3. Observation threshold versus evidence precision and recall.
4. File batch sizes 1, 2, 4, and 8.
5. Noul versus Choice only where the semantic decision can reasonably use either primitive.
6. Richer dynamic action generators based on clues discovered in observations.
7. Reader stopping / sufficiency policies.
8. System One progressive reading versus System Two ReAct under the same read budget.

See docs/design.md for the detailed research model.

## Accuracy reference workflow

The progressive-reader behavior is also evaluated against a Claude Code System 2 reference on the same exact subject revision and verbatim task.

~~~text
.github/workflows/system-one-code-locator-accuracy.yml
~~~

The comparison reports Phase-1 reference recall, final evidence-file agreement, primary/supporting recall, and evidence-region / line coverage. Claude is treated as a reference baseline rather than ground truth.

The first Nession websocket comparison found 80% primary-file recall and 85.8% primary evidence-line coverage. Its most important finding was that `MessageRouter.ts` was visible to Phase 1 but missed at score 0.64 / rank 21, while `WebSocketService.ts:1-140` already exposed the import needed to discover it dynamically.
