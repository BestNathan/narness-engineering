# Treatment B — Semantic Index

> Status: Implemented scaffold, validation running.
>
> Nession branch: `research/ai-native-repo-b-semantic-index`
>
> Head after initial implementation: `8fb6e8707f2dc967a900e227bb899b0c75336d2e`
>
> Research PR: `BestNathan/nession#889`

## Independent variable

Treatment B keeps source topology materially unchanged and adds a machine-queryable semantic layer.

It introduces:

```text
.ai-native/
  capabilities.json
  resolve.mjs
  README.md
```

The index defines stable capability identities for the selected reconnect slice:

```text
capability://web/transport/reconnect
capability://terminal/session/visibility-wake
capability://terminal/session/attach-state
capability://terminal/session/reattach
capability://terminal/session/route-recovery
capability://terminal/session/runtime-projection
```

Each capability records stable ID, description, aliases, physical owners, dependencies, consumers, owned state, invariants, and evidence/tests.

## Resolver

```bash
node .ai-native/resolve.mjs "late attach success after route switch"
node .ai-native/resolve.mjs capability://terminal/session/reattach
node .ai-native/resolve.mjs --list
```

The resolver deliberately uses deterministic lexical scoring rather than embeddings. This prevents the experiment from conflating the benefit of stable semantic metadata with the quality of a separate retrieval model.

## What B does not change

Treatment B does not intentionally alter runtime behavior, production source paths, implementation decomposition, abstraction depth, behavior locality, or test semantics.

This makes A vs B primarily a test of addressability and explicit semantic relationships.

## Experimental instruction

Formal B runs may be told only that the resolver is available and how to invoke it. The task prompt itself remains byte-equivalent to Treatment A.

The agent is not given the expected capability, owner paths, gold set, fixture mutation, or acceptance implementation.

## Risks

### Metadata as an answer key

If capability descriptions or aliases are written around benchmark task wording, B becomes a hidden task-answer map.

Mitigation: metadata describes stable domain concepts; no Txx references appear in the index; entries are defined before formal runs; future task additions must not retroactively rewrite the index for task-specific advantage.

### Stale index

A semantic index that disagrees with code may increase errors. Treatment B intentionally exposes that as a real cost. Index maintenance and staleness should be recorded in the final threats-to-validity and maintenance-cost analysis.

## Intended comparison

```text
A vs B

same code shape
same task
same model
same harness

difference:
semantic identity + ownership/dependency/invariant/evidence index
```

Primary expected effects:

```text
first-hit accuracy ↑
irrelevant reads ↓
grep/glob calls ↓
missed affected units ↓
context acquisition ↓
```

No end-to-end benefit is assumed until measured.
