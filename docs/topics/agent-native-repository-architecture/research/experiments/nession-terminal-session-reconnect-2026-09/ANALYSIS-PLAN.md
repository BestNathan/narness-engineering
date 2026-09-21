# Pre-Registered Analysis Plan — Revision 1

> Status: frozen in principle before any reportable formal run.
>
> This document defines how revision-1 results will be summarized and interpreted.
> It exists to prevent post-hoc metric selection after A/B/C outcomes are visible.

## Unit of analysis

The primary unit is the **task**, not the individual run.

The preferred design has three fresh repetitions for every task/treatment cell:

```text
24 tasks × 3 treatments × 3 repetitions = 216 runs
```

For each numeric metric, repetitions are reduced to a per-task/treatment median.
For boolean outcomes, repetitions are reduced to a per-task success proportion.

Treatment effects are then computed as **paired within-task deltas**.

This prevents easy tasks from dominating an aggregate merely because they are fast
and keeps the comparison aligned with the experiment's matched-task design.

## Pre-registered contrasts

```text
A vs B  semantic addressability / resolver effect
B vs C  code-shape and locality effect after semantic indexing
A vs C  complete agent-native treatment effect
```

No treatment ranking is inferred from an unmatched global average alone.

## Task strata

The frozen analysis strata are machine-readable in `analysis-strata.json`.

```text
bug_fix           T01–T06
feature           T07–T12
regression_repair T13–T18
refactor          T19–T22
evidence          T23–T24
```

Overall effects are primary. Stratum results are diagnostic and must be reported
even when they disagree with the overall result.

## Metric direction

Higher is better:

```text
task_success
first_hit_correct
navigation_precision
navigation_recall
mutation_checks_ok
```

Lower is better:

```text
irrelevant_files_read
files_read
search_calls
navigation_events_before_first_edit
time_to_first_relevant_artifact_ms
time_to_first_edit_ms
input_tokens
repair_loops
validation_failures
out_of_scope_edit_count
agent_duration_ms
```

Runner wall time is reported but is secondary because dependency/setup and hidden
verification add noise unrelated to coding-agent productivity.

## Primary metrics by hypothesis

### H1 — Retrieval precision

Primary:

```text
navigation_precision
irrelevant_files_read
```

Secondary:

```text
first_hit_correct
search_result_false_positive_rate
search_calls_before_first_edit
```

### H2 — Retrieval recall

Primary:

```text
navigation_recall
important_artifacts_missed_count
```

Secondary:

```text
task_success on cross-capability tasks
```

### H3 — Context acquisition efficiency

Primary:

```text
input_tokens
navigation_events_before_first_edit
time_to_first_edit_ms
```

Secondary:

```text
files_read
search_calls
time_to_first_relevant_artifact_ms
```

### H4 — Change quality

Primary:

```text
task_success
repair_loops
validation_failures
```

Secondary:

```text
out_of_scope_edit_count
acceptance_ok
verification_ok
mutation_checks_ok
```

### H5 — End-to-end productivity

Primary:

```text
task_success
agent_duration_ms
input_tokens
```

A treatment is not considered productively better merely because it is faster if
correctness materially decreases.

## Effect estimation

For every metric and contrast:

1. reduce repetitions within each task/treatment;
2. compute paired task-level deltas;
3. report median paired delta;
4. report the fraction of tasks improved / unchanged / worsened;
5. bootstrap **tasks as clusters** with 10,000 resamples;
6. report a 95% bootstrap interval for the paired median delta.

Bootstrap seed:

```text
20260921
```

The raw task-level values and every admissible run remain published.

No missing measurement is imputed.

## Minimum practically important differences

These thresholds are interpretation guards, not substitutes for raw data.

```text
task_success                 5 percentage points absolute
first_hit_correct            10 percentage points absolute
navigation_precision         0.10 absolute
navigation_recall            0.05 absolute
irrelevant_files_read        20% relative reduction
navigation events pre-edit   15% relative reduction
input_tokens                 15% relative reduction
repair_loops                 20% relative reduction
agent_duration_ms            15% relative reduction
```

For count/time/token metrics whose control median is zero, absolute paired values
are reported and the relative threshold is not used.

## Hypothesis classification

Each H1–H5 receives exactly one final label:

```text
Supported
Partially supported
Not supported
Inconclusive
```

### Supported

Primary metrics point in the hypothesized direction, at least one primary metric
meets its practical-effect threshold, the bootstrap interval does not indicate a
material effect in the opposite direction, and task-success degradation is less
than 5 percentage points unless task success itself is the hypothesized gain.

### Partially supported

There is a material benefit in some primary metrics or task strata, but results
are mixed across primary metrics, confidence intervals span both trivial and
meaningful effects, or the benefit is limited to a task class.

### Not supported

Primary metrics show no practically important benefit, or the treatment produces
a practically important regression in correctness / evidence closure that offsets
navigation or cost gains.

### Inconclusive

Too few admissible matched task cells remain, instrumentation is missing for a
primary metric, execution drift invalidates a contrast, or uncertainty is too
large to distinguish meaningful benefit from meaningful harm.

## Treatment-specific interpretation

A→B is the principal evidence for whether a semantic resolver/index improves
agent retrieval without changing code shape.

B→C is the principal evidence for whether behavior-oriented physical locality
adds value after semantic addressing is already present.

A→C is the complete-system effect, but it must not be used to attribute the gain
to semantic indexing or code shape when A→B and B→C disagree.

## Multiple metrics and exploratory analysis

The study is architectural and multi-metric. It does not use a single
p-value-based winner criterion.

Bootstrap intervals are descriptive uncertainty estimates. We will not search
across metrics for the smallest p-value or retroactively redefine a primary
metric.

Exploratory analyses are allowed only when explicitly marked **post hoc** and may
not change the pre-registered H1–H5 classification rules.

## Failure and timeout handling

A run that is validly executed but fails the task remains in the dataset.

A hard agent timeout is a benchmark outcome, not a reason to exclude the run.
Metrics unavailable because execution was interrupted remain missing and are not
imputed.

Infrastructure failures, trace corruption, hidden-oracle leakage, treatment SHA
mismatch, execution-profile drift, or cross-treatment session contamination make
a run inadmissible.

## Reporting requirement

The final research report must include:

```text
all admissible run counts
all task success outcomes
paired task-level treatment effects
95% task-cluster bootstrap intervals
task-class strata
failure taxonomy
treatment construction cost
negative/regressive results
limitations
H1–H5 classifications
architecture graduation decisions
```

The study is allowed to conclude that semantic indexing helps while structural
reorganization does not, that both help, that neither helps, or that the evidence
is inconclusive.
