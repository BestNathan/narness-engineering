# Results

> Status: Benchmark Revision 2 and Analysis Revision 2 frozen; no reportable formal runs yet.

This file will hold aggregate A/B/C measurements after runs are collected.

Required comparisons:

```text
A vs B — semantic resolution effect
B vs C — structural/locality effect after semantic indexing
A vs C — complete treatment effect
```

Report raw component metrics before any composite productivity metric. Primary inference follows `ANALYSIS-PLAN.md`: repetitions are reduced within each task, then A/B/C are compared using paired task-level effects and 10,000 task-cluster bootstrap resamples.

Minimum summary:

| Metric | A | B | C | A→B | B→C | A→C |
|---|---:|---:|---:|---:|---:|---:|
| Task success rate | — | — | — | — | — | — |
| First-hit target accuracy | — | — | — | — | — | — |
| Navigation precision | — | — | — | — | — | — |
| Navigation recall | — | — | — | — | — | — |
| Median irrelevant files read | — | — | — | — | — | — |
| Median files read | — | — | — | — | — | — |
| Median search calls | — | — | — | — | — | — |
| Median context tokens | — | — | — | — | — | — |
| Median repair loops | — | — | — | — | — | — |
| Median evidence closure time | — | — | — | — | — | — |

Do not fill missing metrics with estimates.

## Generated analysis artifacts

After formal collection:

```bash
python3 scripts/aggregate-ai-native-results.py \
  --runs-root /path/to/formal-runs \
  --output-dir /path/to/results

python3 scripts/analyze-ai-native-effects.py \
  --raw-runs /path/to/results/raw-runs.csv \
  --strata docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/analysis-strata.json \
  --output-dir /path/to/results
```

Expected outputs:

```text
raw-runs.csv
summary.json
summary.md
paired-effects.json
paired-effects.md
```

`paired-effects.*` is the primary treatment-effect view. Positive oriented effects always mean the second treatment in a contrast performed better.
