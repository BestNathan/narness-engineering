# Analysis Revision 2 — Frozen

Analysis revision 2 is the active pre-registered analysis implementation for formal collection.

```text
analysis revision:      2
definition SHA:         357c38c9b10a3eb668b15aead703a5f5200b2858
definition branch:      research/ai-native-analysis-r2
formal runs observed:   0
bootstrap samples:      10000
bootstrap seed:         20260921
```

## Why revision 2 exists

Revision 1 froze the intended analysis plan correctly, but the paired-effects implementation omitted some metrics declared by that plan.

The most important omission was:

```text
important_artifacts_missed_count
```

which is a primary H2 retrieval-recall metric.

Other omitted pre-registered evidence surfaces included:

```text
search_result_false_positive_rate
search_calls_before_first_edit
acceptance_ok
verification_ok
mutation_checks_ok
```

The gap was found before any reportable formal run. Revision 2 therefore changes no hypothesis, treatment, task, threshold, or observed conclusion. It only makes the frozen implementation complete with respect to the already-declared plan.

## Frozen analysis surfaces

```text
ANALYSIS-PLAN.md
analysis-strata.json
scripts/aggregate-ai-native-results.py
scripts/analyze-ai-native-effects.py
```

Any further change to those analysis semantics or implementation after formal outcomes are visible creates analysis revision 3.
