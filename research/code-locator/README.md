# System One Code Locator — Archived Narness Snapshot

> Status: Archived in Narness. Active implementation and ongoing research have moved to [BestNathan/system-one-code-explore](https://github.com/BestNathan/system-one-code-explore).

This directory is retained as historical evidence for the early Code Locator experiment that was merged into Narness in [PR #16](https://github.com/BestNathan/narness-engineering/pull/16).

It is **not** the current Code Locator implementation and should not be used as the starting point for new experiments.

## Why this snapshot remains

Code Locator began as a concrete test of the System One Progressive Action Spaces thesis:

~~~text
large environment
  -> bounded grounded frontier
  -> fast model judgment
  -> typed effect
  -> observation
  -> new state
~~~

The early prototype in this directory explored hierarchical repository localization and established the first reproducible fixtures, traces, and workflow evidence.

Later research moved well beyond this snapshot. The follow-up work in [PR #17](https://github.com/BestNathan/narness-engineering/pull/17) explored two-phase readers, independent file-local runtimes, explicit stop control, bounded decision views, canonical localization results, and multiple exploration algorithms. Additional benchmark branches were opened as PRs #21-#25.

Those branches are preserved as GitHub research history, but active development no longer happens in Narness.

## Converged findings retained by Narness

The durable conclusions are documented in the [System One Progressive Action Spaces topic](../../docs/topics/system-one-progressive-action-space/README.md). In short:

- keep each model decision over a small grounded action frontier;
- treat source reads as observations produced by typed effects;
- separate broad file discovery from file-local navigation;
- prefer independent file-local runtimes when raw observations would otherwise overwhelm one shared context;
- keep navigation action generation content-agnostic where possible;
- use `Choice` for mutually exclusive control flow and `Noul` for independent relevance/utility judgments;
- do not overload relevance thresholds as implicit stopping semantics;
- separate durable `RuntimeState` from bounded model-visible `DecisionView`;
- keep execution traces separate from canonical localization results.

## Historical scope of this directory

The code and documents here reflect the early merged prototype, roughly:

~~~text
repository
  -> directory relevance
  -> file relevance
  -> source-line relevance
  -> merged snippets
~~~

That design is useful as provenance, but it has been superseded as an active architecture.

Do not add new Code Locator algorithms, benchmark runs, or experiment logs here.

## Current implementation and research

Use the dedicated repository instead:

- [BestNathan/system-one-code-explore](https://github.com/BestNathan/system-one-code-explore)
- ongoing research: `docs/research/` in that repository

Narness may still absorb stable architectural conclusions from that work, but should not duplicate its implementation or experiment history.
