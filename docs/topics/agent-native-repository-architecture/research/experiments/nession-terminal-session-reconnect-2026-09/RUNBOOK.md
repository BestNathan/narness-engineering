# Experiment Runbook

This is the operational path from the frozen benchmark to the final research report.

## 1. Run the three non-reportable pilots

Use a machine with an authenticated Codex CLI and clean local checkouts of Narness Engineering and Nession.

```bash
./scripts/run-ai-native-codex-pilots.sh /path/to/nession
```

The command performs preflight, executes T05/A, T08/B, and T20/C with fresh ephemeral sessions, scores the traces, validates instrumentation, freezes the execution profile, and generates the pre-registered 216-run schedule.

It writes:

```text
runner/execution-profile-r1.json
runner/formal-schedule-r1.json
```

Review and commit those two generated metadata files before formal collection.

## 2. Run formal collection

```bash
python3 scripts/run-ai-native-formal.py \
  --source-repo /path/to/nession \
  --schedule docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/formal-schedule-r1.json \
  --execution-profile docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/execution-profile-r1.json \
  --runs-root /path/to/formal-runs
```

The orchestrator validates benchmark/analysis integrity before model spending, enforces the frozen execution-tool bytes, runs the balanced schedule, scores every run, and writes a tamper-evident `seal.json` for every admissible outcome. Existing runs are never skipped merely because `run.json` says they are sealed; their artifact hashes are re-verified first.

Failed tasks remain in the dataset when the run itself is admissible.

### Progress and interruption recovery

Inspect a long-running collection without mutating it:

```bash
python3 scripts/inspect-ai-native-formal-progress.py \
  --runs-root /path/to/formal-runs \
  --schedule docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/formal-schedule-r1.json \
  --execution-profile docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/execution-profile-r1.json \
  --benchmark-lock docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/BENCHMARK-LOCK.json
```

The inspector distinguishes `sealed`, `pending`, `incomplete`, and `tampered` entries. A tampered sealed run is always a hard error.

If execution was interrupted before a run was sealed, restart the selected schedule range with:

```bash
python3 scripts/run-ai-native-formal.py ... --recover-incomplete
```

The incomplete directory is moved under `_incomplete/` with a `recovery.json` forensic record before the scheduled run is restarted. Existing valid seals are re-verified and skipped; they are never overwritten.


## 3. Review failed runs

Every failed admissible run receives one primary R1–R12 failure code.

```bash
python3 scripts/review-ai-native-run.py \
  --run-dir /path/to/formal-runs/Txx-A-01 \
  --primary R5 \
  --notes 'Missed the stale-generation invariant.'
```

Secondary codes may be supplied with repeated `--secondary` arguments.

## 4. Generate interim analysis

At any time, including before all runs are complete:

```bash
python3 scripts/finalize-ai-native-research.py \
  --runs-root /path/to/formal-runs \
  --output-dir /path/to/research-results \
  --allow-incomplete
```

This produces raw run data, treatment summaries, paired effects, failure taxonomy, completeness metadata, and a report draft.

## 5. Complete H1–H5 review

Copy:

```text
conclusion-r1.template.json
```

to a working conclusion file. Fill exactly one classification for H1–H5:

```text
Supported
Partially supported
Not supported
Inconclusive
```

Each hypothesis requires a rationale. Architecture decisions must be marked `graduate`, `keep-experimental`, or `reject` with evidence-based rationale.

Validate it:

```bash
python3 scripts/validate-ai-native-conclusion.py \
  --conclusions /path/to/conclusion-r1.json
```

## 6. Finalize the research artifact

```bash
python3 scripts/finalize-ai-native-research.py \
  --runs-root /path/to/formal-runs \
  --output-dir /path/to/research-results \
  --conclusions /path/to/conclusion-r1.json
```

Without `--allow-incomplete`, finalization fails when the pre-registered formal schedule is missing/incomplete, a treatment lacks all 24 tasks, any failed admissible run lacks taxonomy review, or H1–H5 conclusions are not supplied.

Primary generated artifacts:

```text
raw-runs.csv
summary.json
summary.md
paired-effects.json
paired-effects.md
failure-summary.json
failure-summary.md
research-completeness.json
collection-manifest.json
research-report.md
```

## Frozen boundaries

```text
benchmark semantics  -> BENCHMARK-LOCK.json
analysis semantics   -> ANALYSIS-LOCK.json
execution mechanics  -> execution-profile-r1.json (after pilots)
formal order         -> formal-schedule-r1.json (after pilots)
```

Do not change a frozen boundary after observing reportable outcomes. Create a new revision instead.

## Tamper-evident research data

Each admissible formal run has a `seal.json` containing SHA-256 digests for the run record, score, trace, final diff, and other execution artifacts.

Before final analysis, `scripts/verify-ai-native-collection.py` checks every scheduled run against its seal and the pre-registered schedule/profile, then emits:

```text
collection-manifest.json
```

The collection manifest contains the schedule/profile/benchmark hashes, every verified run-seal hash, optional review hashes, and one deterministic collection digest.

Changing an already sealed trace, score, run record, prompt, diff, or other sealed artifact therefore causes final collection verification to fail instead of silently changing the study data.
