# Benchmark Revision 3

Definition commit: `bb56a330c90755d9c149bff64aaeb3a841d8015c`.
Frozen branch: `research/ai-native-benchmark-r3`.

## Trigger and scope

Formal Actions run [35731390660](https://github.com/BestNathan/narness-engineering/actions/runs/35731390660) stopped at sequence 3 (T15/B). The trace read the gold primary file through an absolute isolated-checkout path, but the scorer classified it as irrelevant. The first-relevant-artifact metric was consequently absent and sealing failed.

The runner now records its isolated checkout root. The scorer uses that root to normalize read, search-result and edit paths lexically, without requiring the deleted checkout to exist. Outside-root paths remain outside the gold namespace. Raw traces are preserved.

This changes scoring and therefore supersedes Benchmark Revision 2 under its explicit freeze rule. Task manifests, fixtures, treatment SHAs, hidden oracle and gold are unchanged. Analysis Revision 2 is unchanged.

## Data disposition and restart

Keep the original R1 metadata and the [partial formal artifact](https://github.com/BestNathan/narness-engineering/actions/runs/35731390660/artifacts/10695629531) as incident evidence. Do not alter its sealed records or mix them into the new collection.

Fresh R9 pilots must produce the R2 execution profile, 216-entry schedule and formal-plan lock. Their promotion PR must be merged before a separate manual formal dispatch starts at sequence 1. No new model run is part of this amendment.
