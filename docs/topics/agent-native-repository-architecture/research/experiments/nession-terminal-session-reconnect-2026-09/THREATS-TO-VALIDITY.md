# Pre-Registered Threats to Validity

> Status: recorded before reportable formal collection.
>
> These limitations must remain visible even if the final A/B/C result is strongly
> positive. They are not post-hoc explanations for an inconvenient outcome.

## 1. Provider/backend identity

The execution profile records:

```text
requested Codex model
reasoning effort
Codex CLI version
Narness adapter/harness hashes
run timestamp
```

but the current non-interactive Codex JSONL interface does not provide an
independently verifiable provider-side model build/revision identifier for each
turn.

Therefore:

> "same model" means the same requested model/configuration and observed CLI
> version, not proof that the provider served byte-identical model weights.

Mitigations:

- A/B/C are interleaved instead of run in large treatment batches;
- treatment position is Latin-square balanced within each task;
- task blocks are deterministically permuted per replication;
- timestamps and exact local execution profile are retained.

A material provider/backend change during collection remains a possible
confounder.

## 2. Single repository slice

The benchmark is deliberately deep rather than broad:

```text
repository: Nession
slice: terminal/session reconnect and recovery
language/domain: TypeScript/React + WebSocket/session runtime
```

The study can provide causal evidence for this slice but cannot establish that
the same effect size transfers to Rust, Go, data pipelines, kernel code, mobile
apps, or unrelated repository shapes.

Architecture graduation should distinguish:

```text
principle supported by one controlled study
!=
universal repository law
```

## 3. One coding-agent family/profile

Formal Revision 2 uses one frozen Codex execution profile.

The result may depend on:

- model family;
- reasoning effort;
- shell/tool behavior;
- context window;
- coding-agent loop implementation.

A repository representation that helps this profile may help other agents less,
more, or differently.

Replication across model/harness families is future work.

## 4. B measures an exposed resolver surface

Treatment B is not "metadata exists silently".

B and C receive the same short instruction that a deterministic semantic resolver
is available.

Therefore A→B measures:

```text
semantic index
+ deterministic resolver
+ explicit discoverability of that resolver
```

The instruction itself has a small context/token cost. That cost remains part of
the treatment rather than being subtracted away.

## 5. Hand-authored semantic metadata

The B/C semantic index is authored from domain understanding.

That creates two opposing risks:

```text
too good:
  metadata accidentally encodes task-specific answers

too bad:
  metadata is stale/incomplete and harms navigation
```

Mitigations:

- metadata was frozen before formal outcomes;
- Txx benchmark IDs are forbidden and machine-checked;
- B/C semantic fields are machine-checked for equivalence;
- stale/incorrect metadata has an explicit R11 failure category.

The experiment still does not estimate the ongoing human/agent maintenance cost
of semantic metadata across years of repository evolution.

## 6. C includes migration and compatibility structure

Treatment C relocates canonical ownership while leaving thin compatibility
projections at legacy paths.

This is realistic migration behavior, but it means C is not an idealized clean
greenfield unit layout.

The compatibility projections can either help by preserving familiar imports or
hurt by adding another visible path.

R12 exists specifically to record accidental complexity introduced by the
architecture treatment.

Up-front C migration cost is reported separately from per-task productivity.

## 7. Gold-set classification is a model of relevance

Navigation precision/recall depends on the frozen hidden gold classification.

A path categorized as irrelevant may occasionally provide useful context, and a
semantically important artifact may be absent from the gold model.

Mitigations:

- gold is frozen before reportable outcomes;
- raw traces are retained;
- end-to-end task/evidence success remains primary for H4/H5;
- gold-based retrieval metrics are not treated as correctness by themselves.

## 8. Shell instrumentation is best-effort

The Codex adapter reconstructs reads/searches/globs/resolver use from structured
Codex command events and conservative shell parsing.

It can miss navigation performed through an unrecognized command shape.

Pilot acceptance exists to detect obvious instrumentation gaps before the formal
profile is frozen.

Runs with ambiguous execution/token instrumentation are inadmissible rather than
silently scored.

## 9. Token accounting depends on one ephemeral turn

Each benchmark run is one fresh ephemeral Codex task.

Pilot validation and formal sealing require exactly one completed-turn usage
event. This avoids silently double-counting cumulative usage if CLI event behavior
changes.

If that invariant stops holding, collection must stop and instrumentation must be
revised before continuing.

## 10. Fresh-session evaluation

Every run begins from a fresh agent session.

This isolates repository representation, but it does not measure a long-lived
coding agent that has accumulated repository-specific context or memory.

The expected benefit of semantic addressing may be smaller for an agent with
perfect long-term repository memory, or larger if explicit semantic state improves
that memory.

## 11. Local machine/cache effects

Dependency installation occurs before the coding agent. OS filesystem caches,
Git object caches, and npm caches can still vary with run order.

Mitigations:

- primary timing uses agent duration rather than total runner wall time;
- treatment order rotates within each task;
- task blocks are permuted across replications;
- environment/tool versions are frozen at collection start.

Timing effects should be interpreted together with tokens, navigation, and
correctness rather than alone.

## 12. Hidden acceptance is incomplete reality

Hidden oracle/acceptance tests provide reproducible evidence, not proof of all
possible production behavior.

A run can pass the benchmark and still contain a defect outside the tested
behavioral boundary.

This is one reason the study reports "benchmark task success" rather than claiming
general software correctness.

## 13. Human failure review is not perfectly blinded

Treatment identity can be inferred from paths and resolver events.

The study therefore does not claim blinded failure adjudication.

Instead it pre-registers:

- one taxonomy;
- evidence-first review order;
- one primary causal code;
- rationale/evidence requirements;
- run-seal anchoring;
- review before aggregate failure-mode interpretation.

Failure taxonomy remains diagnostic rather than the primary hypothesis test.

## 14. Three repetitions estimate only limited stochasticity

Three repetitions per task/treatment improve robustness but do not characterize
the full output distribution of a stochastic coding model.

The analysis therefore:

- reduces runs within task/treatment;
- uses paired task-level effects;
- bootstraps tasks as clusters;
- publishes raw runs and uncertainty;
- permits an Inconclusive result.

## 15. Task authorship and benchmark overfitting

Tasks come from one selected reconnect domain and are designed by researchers who
understand the repository.

Even with hidden gold and acceptance, the task mix reflects those design choices.

Future replication should include independently authored task sets and additional
repositories.

## Interpretation rule

The final report must distinguish:

```text
internal evidence:
  whether A/B/C changed measured behavior in this frozen study

external claim:
  how broadly the result should generalize
```

A strong internal result does not erase external-validity limits.

Likewise, a null result in this one slice does not prove that semantic addressing
or behavioral locality can never help elsewhere.
