# Benchmark Revision 2 — Frozen

Benchmark Revision 2 is the active formal benchmark.

```text
experiment:         nession-terminal-session-reconnect-2026-09
revision:           2
definition SHA:     194bf5dc1a28f4e4c10491d7326891ba157d325b
definition branch:  research/ai-native-benchmark-r2
formal runs seen:   0

Treatment A: 0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664
Treatment B: 8fb6e8707f2dc967a900e227bb899b0c75336d2e
Treatment C: 3e544761d5b89dc09a631533659dca4862f9e559

Hidden oracle: 70d8074e7c50f3865771fabd714e811ae440e09d
Tasks: T01–T24
```

## What changed from Revision 1

No task, treatment, fixture, oracle, or gold semantic scope changed.

Revision 2 additionally freezes the completed scorer implementation because scoring semantics are part of the benchmark contract.

The scorer now contains the pre-registered metric surfaces required by the analysis plan, including:

```text
navigation_events_before_first_edit
search_calls_before_first_edit
files_read_before_first_edit
important_artifacts_missed_count
out_of_scope_edit_count
validation_failures
```

## Frozen paths

Revision 2 freezes:

```text
tasks/README.md
runner/manifests/
runner/fixtures/
runner/mutations/
runner/treatments.json
runner/oracle.json
runner/gold.json
scripts/score-ai-native-run.py
```

Any change to those surfaces after reportable outcomes are visible creates Benchmark Revision 3.

Instrumentation/orchestration mechanics may still evolve before execution-profile freeze if they do not change these frozen benchmark semantics.
