# Hierarchical Code Localization with System One

> Research note for the System One Progressive Action Spaces topic.

## Question

Can a fast System One model locate task-relevant source code without running an open-ended ReAct browsing loop?

The concrete example is:

> Help me optimize the websocket connection implementation.

The experiment treats repository exploration as progressive state disclosure. The harness deterministically exposes the next bounded candidate set; System One only estimates semantic relevance inside that set.

## Working model

```text
Goal
  +
Observed repository structure
  |
  v
Harness expands state
  |
  v
Finite candidate set
  |
  v
System One relevance judgment
  |
  v
Harness prunes and expands again
```

For the initial prototype:

```text
repository
  -> directories
  -> files
  -> source lines
  -> merged code ranges
```

This is the same underlying shape as the Kubernetes experiment:

```text
Kubernetes:
cluster -> namespaces -> pods -> containers -> grounded command

Code localization:
repository -> directories -> files -> lines -> grounded snippets
```

The domain adapter changes; the harness pattern does not.

## System One is a semantic filter, not the navigator

A ReAct implementation could repeatedly ask a model to decide which directory to list, which file to open, and which command to run. That gives the model control of both semantic judgment and exploration mechanics.

The prototype separates those responsibilities:

```text
Harness
  - enumerate candidates
  - read files
  - split content
  - preserve provenance
  - apply thresholds
  - batch requests
  - merge final ranges
  - record evidence

System One
  - estimate whether each exposed candidate is relevant to the goal
```

This keeps deterministic operations outside the model and makes each model call independently inspectable.

## Why independent probabilities matter

Unlike action selection, localization is not a single-winner problem. A websocket change may involve a connection manager, hook, protocol type, retry policy, and tests at the same time.

The experiment therefore uses one Noul question per candidate. Each candidate gets an independent relevance probability and the harness retains all candidates above the current threshold.

This also makes threshold behavior explicit and measurable.

## Threshold schedule and recall risk

The initial schedule is deliberately recall-biased at the top and precision-biased near source content:

```text
directory >= 0.35
file      >= 0.50
line      >= 0.70
```

The exact values are experimental.

A false positive at the directory stage only creates more downstream work. A false negative at the directory stage can permanently hide every relevant file below it. Therefore early-stage threshold calibration is a first-class runtime concern, not merely a model-tuning detail.

A likely next design is:

```text
retain(all candidates >= threshold)
+
retain(top_k minimum beam)
```

That would bound catastrophic early pruning while still reducing the search space.

## Progressive disclosure is also a cost policy

The model does not receive source code until a file survives earlier stages:

```text
directory stage
  path + direct child names

file stage
  path + filename + extension + size

line stage
  line + small neighboring context
```

This means context volume grows only for candidates that survive previous semantic gates.

The key hypothesis is not merely that System One is fast. It is that the harness can spend semantic judgment only where the current state justifies further disclosure.

## Result provenance

The final answer is not a bag of strings. It retains the path from coarse state to source evidence:

```text
RelevantDirectory
  -> RelevantFile
      -> RelevantLine
          -> CodeSnippet(path, line range, score, content)
```

That provenance is required for later evaluation, explainability, cache design, and any System Two handoff.

## Research hypotheses

### H6: Progressive semantic pruning can replace agent-driven browsing for localization

For tasks whose relevant code can be found through repository structure and local semantic evidence, repeated expand -> score -> prune transitions may locate useful source ranges without free-form planning.

### H7: Early high recall matters more than uniform precision

A stage-specific threshold schedule should outperform one global threshold because false-negative cost is asymmetric across the search tree.

### H8: Harness-controlled disclosure reduces unnecessary context

Reading source only after structural candidates survive should reduce model input compared with broad repository ingestion while retaining enough semantic signal to localize the implementation.

### H9: The same runtime abstraction can support action selection and relevance filtering

Kubernetes uses a grounded `Choice` frontier. Code localization uses independent `Noul` judgments. Both can share:

```text
StateSpaceGenerator
  -> CandidateSet
  -> DecisionPrimitive
  -> TransitionPolicy
  -> EvidenceRecorder
```

The important abstraction may therefore be broader than a state machine with a single decision type.

## Evidence contract

Every Code Locator run should preserve enough data to replay the localization surface without relying on GitHub Actions console retention.

The dedicated Code Locator artifact contains only this experiment:

```text
run-manifest.json
tests.log          # offline job
run.log
result.json
trace.jsonl
summary.md
```

The manifest records harness revision, subject repository and revision, workflow run identity, query, thresholds, batch size, and model.

The JSONL trace records candidate disclosure, model requests, score responses, threshold decisions, latency, token usage, and final results. Authorization data is never recorded.

Kubernetes evidence is intentionally excluded and is owned by the separate `system-one-k8s-experiment` workflow.

## Workflow experiment design

The dedicated [System One Code Locator workflow](../../../.github/workflows/system-one-code-locator.yml) has two roles.

First, deterministic fixture validation runs only when the Code Locator implementation, its research notes, or its workflow changes.

Second, a manual TypeSafe job runs the real System One model against a checked-out subject repository such as `BestNathan/nession`.

The subject repository, ref, query, thresholds, batch size, and model are workflow inputs so repeated runs can vary one parameter while preserving the rest in the manifest.

Artifacts are retained for 90 days. Each run should be treated as raw Code Locator research evidence, not as proof that the hypotheses are already true.

## Metrics available immediately

Without gold labels, the workflow can already measure operational behavior:

- candidates exposed and retained at each stage;
- pruning ratio by stage;
- total model calls;
- TypeSafe input/output tokens;
- end-to-end elapsed time;
- selected directories/files/source ranges;
- stability across repeated runs and threshold settings.

## Metrics requiring a benchmark dataset

Claims about localization quality require pre-registered expected evidence, for example:

```text
query
expected relevant files
expected relevant line ranges or symbols
allowed supporting files
```

That enables:

- relevant-file recall;
- relevant-file precision;
- range recall / overlap;
- false-prune stage attribution;
- cost per successfully localized task;
- comparison with ripgrep, embedding retrieval, LSP/index retrieval, and System Two browsing.

## Next experiments

1. Build a small gold dataset from real Nession changes and issue/PR history.
2. Compare threshold-only pruning with threshold + minimum beam retention.
3. Compare whole-tree directory scoring with recursively expanded directory frontiers.
4. Replace line candidates with syntax-aware symbols or blocks while retaining line provenance.
5. Add cache keys based on repository revision, goal, stage, and candidate content hash.
6. Compare System One localization against a System Two coding agent under the same gold tasks and evidence contract.
7. Test a System One -> System Two handoff where the fast locator supplies grounded code context to the reasoning model.

## Pilot evidence

- [Nession WebSocket localization pilot — 2026-09-23](nession-websocket-pilot-2026-09-23.md)

The first real run confirmed useful semantic localization, while also showing that threshold-only whole-tree search spends most of its cost at the line layer. This is the baseline for the next recursive-beam / symbol-level experiment.

## Reference implementation

See [System One Code Locator](../../../examples/system-one-code-locator/README.md).
