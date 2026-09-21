# Nession Terminal / Session Reconnect Experiment

> Status: Benchmark Revision 2 and Analysis Revision 2 frozen. Real Codex instrumentation pilots are the remaining gate before reportable formal collection.

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
Benchmark Revision 2
  definition SHA
  194bf5dc1a28f4e4c10491d7326891ba157d325b

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
3 non-reportable Codex pilots
          ↓
execution-profile-r1.json
formal-schedule-r1.json
formal-plan-r1.lock.json
          ↓
commit + collection-start lock
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
published/benchmark-r2-analysis-r2/
publication-manifest.json
```

## Current gate

The next action requires a local machine with an authenticated Codex CLI and clean Narness/Nession checkouts:

```bash
./scripts/run-ai-native-codex-pilots.sh /path/to/nession
```

The three pilot cells are:

```text
T05 / A
T08 / B
T20 / C
```

Pilot task success itself is not required. Complete, trustworthy instrumentation is required. The active execution handoff is `research/ai-native-execution-prepilot-r3@1519adcb31bc66d5741e4cd0e67e54c79b19eef1`.

## Key documents

- [Protocol](protocol.md)
- [Runbook](RUNBOOK.md)
- [Instrumentation pilots](instrumentation-pilots.md)
- [Execution Pre-Pilot Revision 3](EXECUTION-PREPILOT-R3.md)
- [Benchmark Revision 2](REVISION-2-FROZEN.md)
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
runner/execution-profile-r1.json
runner/formal-schedule-r1.json
runner/formal-plan-r1.lock.json
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

- changing benchmark semantics creates Benchmark Revision 3;
- changing analysis semantics creates Analysis Revision 3;
- changing profile/schedule/formal-plan bytes invalidates the current formal plan;
- changing the harness commit used by the collection invalidates the collection-start lock;
- changing sealed run artifacts fails run/collection verification.

The point is not to make the experiment immutable forever. The point is to make every revision explicit and auditable.
