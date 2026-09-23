# Nession Terminal / Session Reconnect Experiment

> Status: Benchmark Revision 3 and Analysis Revision 2 frozen. Real Claude Code R9 instrumentation pilots on GitHub-hosted Actions are the remaining gate before reportable formal collection.

The R1 formal attempt [35731390660](https://github.com/BestNathan/narness-engineering/actions/runs/35731390660) stopped on a scoring instrumentation defect. Its original freeze files and partial artifact are retained for audit. The active R2 freeze files must be generated from fresh R9 pilots; restart formal collection at sequence 1 after their promotion PR is merged.

## Research question

Does an AI coding agent become more productive when the repository evolves from:

```text
A — baseline source organization
        ↓
B — deterministic semantic capability index
        ↓
C — semantic index + behavior-localized canonical ownership
```

while keeping the model, task set, harness policy, verification surface, and hidden acceptance fixed?

## Frozen identities

```text
Benchmark Revision 3
  definition SHA
  bb56a330c90755d9c149bff64aaeb3a841d8015c

Analysis Revision 2
  definition SHA
  357c38c9b10a3eb668b15aead703a5f5200b2858

Treatment A
  0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664

Treatment B
  8fb6e8707f2dc967a900e227bb899b0c75336d2e

Treatment C
  3e544761d5b89dc09a631533659dca4862f9e559

Hidden oracle
  70d8074e7c50f3865771fabd714e811ae440e09d
```

Revision 1 benchmark/analysis records remain in the repository as pre-data audit history.

## Experiment size

Preferred formal design:

```text
24 tasks
× 3 treatments
× 3 fresh repetitions
= 216 formal runs
```

The formal schedule uses a balanced cyclic Latin-square treatment order within each task and a deterministic SHA-256 task-block permutation per replication (seed `20260921`).

Task strata:

```text
T01–T06   bug fixes
T07–T12   features
T13–T18   regression repair
T19–T22   refactors
T23–T24   evidence / mutation-oriented tasks
```

## State machine

```text
Frozen benchmark + analysis
          ↓
3 non-reportable Claude Code R9 pilots on GitHub-hosted Actions
          ↓
execution-profile-r2.json
formal-schedule-r2.json
formal-plan-r2.lock.json
          ↓
promotion PR merged + collection-start lock
          ↓
216 reportable formal runs
          ↓
per-run seal.json
          ↓
failure review R1–R12
          ↓
collection-manifest.json
          ↓
paired task-level analysis
          ↓
H1–H5 reviewed conclusion
          ↓
research-report.md
research-artifact-manifest.json
          ↓
deterministic sealed raw archive
          ↓
published/benchmark-r3-analysis-r2/
publication-manifest.json
```

## Current gate

The next action is a manually dispatched GitHub-hosted Claude Code workflow.
Configure the `ANTHROPIC_API_KEY` secret plus `CLAUDE_MODEL` and (if needed)
`ANTHROPIC_BASE_URL` repository variables, then dispatch
`.github/workflows/ai-native-claude-pilots.yml`.

The three pilot cells are:

```text
T05 / A
T08 / B
T20 / C
```

Pilot task success itself is not required. Complete, trustworthy instrumentation is required. The active execution handoff is the registered direct Claude Code R9 lock in `EXECUTION-PREPILOT-LOCK.json`.

## Key documents

- [Protocol](protocol.md)
- [Runbook](RUNBOOK.md)
- [Instrumentation pilots](instrumentation-pilots.md)
- [Execution Pre-Pilot Revision 9](EXECUTION-PREPILOT-R9.md)
- [Benchmark Revision 3](REVISION-3-FROZEN.md)
- [Analysis Revision 2](ANALYSIS-REVISION-2-FROZEN.md)
- [Pre-registered analysis plan](ANALYSIS-PLAN.md)
- [Failure review protocol](FAILURE-REVIEW-PROTOCOL.md)
- [Raw data retention policy](DATA-RETENTION.md)
- [Pre-registered threats to validity](THREATS-TO-VALIDITY.md)
- [Results placeholder](results.md)
- [Conclusion contract](conclusion.md)
- [Treatment construction cost](treatments/construction-cost.md)
- [Treatment freeze](treatments/FROZEN.md)
- [Next phase](next-phase.md)

## Machine-readable locks

```text
BENCHMARK-LOCK.json
ANALYSIS-LOCK.json
EXECUTION-PREPILOT-LOCK.json
analysis-strata.json
runner/treatments.json
runner/gold.json
runner/oracle.json
```

After the real pilots, these are joined by:

```text
runner/execution-profile-r2.json
runner/formal-schedule-r2.json
runner/formal-plan-r2.lock.json
```

## Research integrity

The study intentionally separates:

```text
benchmark semantics
analysis semantics
execution mechanics
formal run order
raw run evidence
human failure review
final interpretation
```

Each layer has an explicit lock or content identity.

A formal run is admissible only after frozen prompt/treatment/fixture/oracle/metric identities are verified. Its artifacts are content-addressed by `seal.json`.

The complete collection is verified against the pre-registered schedule and formal plan, and final research artifacts receive their own content digest.

Negative, mixed, or inconclusive results are valid outcomes.

## Do not mutate after formal collection starts

Once reportable formal collection begins:

- changing benchmark semantics creates Benchmark Revision 4;
- changing analysis semantics creates Analysis Revision 3;
- changing profile/schedule/formal-plan bytes invalidates the current formal plan;
- changing the harness commit used by the collection invalidates the collection-start lock;
- changing sealed run artifacts fails run/collection verification.

The point is not to make the experiment immutable forever. The point is to make every revision explicit and auditable.
