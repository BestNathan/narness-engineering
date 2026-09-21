# Frozen Oracle — Experiment Revision 1

The hidden acceptance source is frozen at:

```text
repository: BestNathan/nession
branch:     research/ai-native-ci-base
SHA:        70d8074e7c50f3865771fabd714e811ae440e09d
```

This commit contains the finalized task-specific hidden acceptance surfaces for T01–T22.

T23/T24 use mutation-strength acceptance in addition to clean repository verification.

## Rule

Formal revision-1 runs MUST materialize hidden oracle source from this exact SHA.

The moving `research/ai-native-ci-base` branch name is not sufficient evidence of reproducibility. The SHA above is the benchmark oracle identity.

If any oracle semantics change after reportable runs begin, those runs belong to a new benchmark/experiment revision and must not be mixed with revision 1.
