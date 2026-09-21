# Analysis Revision 1 — Frozen

Formal outcome data has not been collected yet. The interpretation plan is now frozen before reportable runs.

```text
analysis revision:      1
definition SHA:         b7772c8f5ce63f55ddc311dd47bc880b7c8102a0
definition branch:      research/ai-native-analysis-r1
integrity run:          35591672455 — PASS
bootstrap samples:      10000
bootstrap seed:         20260921
```

Frozen analysis surfaces:

```text
ANALYSIS-PLAN.md
analysis-strata.json
scripts/aggregate-ai-native-results.py
scripts/analyze-ai-native-effects.py
```

## Primary analysis unit

The task is the primary unit. Three repetitions are reduced within each task/treatment cell, then treatment effects are paired within task.

```text
A → B  semantic addressability
B → C  structural locality beyond semantic metadata
A → C  complete treatment
```

Numeric repetitions use the median. Boolean outcomes use the task-level success proportion. Paired task deltas are summarized by their median and a 95% task-cluster bootstrap interval.

## Anti-post-hoc boundary

Changing primary metrics, task strata, practical-effect thresholds, paired reduction rules, bootstrap procedure, treatment attribution rules, or the paired-effects implementation creates analysis revision 2.

Presentation tooling may evolve without changing the analysis revision. The report generator therefore consumes, but does not redefine, the frozen analysis artifacts.
