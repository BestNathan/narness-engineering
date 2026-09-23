# Experiment Runbook

> Active execution: direct Claude Code pre-pilot R9. Follow
> [EXECUTION-PREPILOT-R9.md](EXECUTION-PREPILOT-R9.md) for client installation,
> environment variables, pilots, isolation, and promotion. The Codex R4 and
> containerized Claude R5 instructions below are historical and must not be used
> for the new execution profile. Formal collection, analysis, and publication
> procedures still apply after R9 freeze.

This is the operational path from the frozen benchmark to the final research report.

The previous R1 formal artifact is incident evidence only. Do not pass it as a recovery artifact for the new R2 plan. After fresh R9 pilots and promotion, dispatch sequences 1–216 with the previous-artifact inputs empty.

## 1. Run the three non-reportable pilots on GitHub-hosted Actions

The active R9 path is `.github/workflows/ai-native-claude-pilots.yml`. It uses a
GitHub-hosted `ubuntu-24.04` machine, checks out the exact execution SHA recorded
in `EXECUTION-PREPILOT-LOCK.json`, installs the pinned Claude Code CLI, and runs
T05/A, T08/B, and T20/C in fresh isolated subject checkouts. There is no active
self-hosted-runner or local execution path for R9; the old Codex workflows remain
disabled historical records only.

Configure the repository once:

```text
Actions secret: ANTHROPIC_API_KEY
Actions variable: CLAUDE_MODEL (an explicit model ID, not sonnet/opus/haiku/default)
Actions variable: ANTHROPIC_BASE_URL (optional; defaults to https://api.anthropic.com)
```

Dispatch **AI Native Claude Code Pilots** from the Actions tab. The workflow
retains a non-reportable handoff artifact containing the three traces and the
generated `execution-profile-r2.json`, `formal-schedule-r2.json`, and
`formal-plan-r2.lock.json`. It validates the handoff against the registered R9
controller before the job can succeed.

After reviewing the artifact, dispatch **AI Native Claude Pilot Promotion** with
the source run ID and exact artifact name. That hosted workflow validates the
handoff, writes `PILOT-FREEZE-r2.json`, and opens a draft pull request containing
the four required freeze files. Merge that pull request before formal collection;
no local checkout is needed for promotion.

The active formal path is `.github/workflows/ai-native-claude-formal.yml`. It is
manual, requires the committed R9 profile/schedule/formal-plan lock, installs the
same pinned client on `ubuntu-24.04`, runs the registered schedule, verifies run
seals, and uploads the formal collection artifact. The default dispatch covers all
216 entries; sequence inputs allow a documented partial/recovery run.

The first three generated files are the hard collection-start gate. The fourth
records promotion provenance. Never synthesize a profile or promote replay/selftest
evidence. Keep the source pilot artifact in Actions retention until the formal
plan has been reviewed.

The command-level details, isolation policy, and promotion checks are specified
in [EXECUTION-PREPILOT-R9.md](EXECUTION-PREPILOT-R9.md). The pilot workflow
writes:

```text
runner/execution-profile-r2.json
runner/formal-schedule-r2.json
runner/formal-plan-r2.lock.json
```

Review and merge the hosted promotion pull request before formal collection.
`formal-plan-r2.lock.json` freezes the exact profile and schedule bytes.

The execution profile embeds a `pilot_set_digest_sha256` plus per-pilot artifact
hashes. Keep the pilot directories until the profile has been reviewed; afterward
the committed profile is the provenance record that binds the formal plan to the
exact pilot evidence.

## 2. Dispatch formal collection on GitHub-hosted Actions

Use `.github/workflows/ai-native-claude-formal.yml` after the promotion PR is
merged. Its default inputs execute all 216 pre-registered entries on a fresh
GitHub-hosted `ubuntu-24.04` job. The workflow installs the same pinned Claude
Code client, runs the readiness gate before model spending, verifies every seal,
and uploads the collection artifact. Sequence inputs are available only for a
documented partial/recovery run; a partial artifact is not a complete study.

The orchestrator validates benchmark/analysis integrity before model spending, enforces the frozen execution-tool bytes, runs the balanced schedule, scores every run, and writes a tamper-evident `seal.json` for every admissible outcome. Existing runs are never skipped merely because `run.json` says they are sealed; their artifact hashes are re-verified first.

Before the first reportable run, the orchestrator also creates:

```text
/formal-runs/_collection/collection-start.json
```

The collection-start lock requires the execution profile, formal schedule, and formal-plan lock to already be Git-tracked and byte-identical to the current Narness HEAD. It freezes that Narness commit, hosted runtime/tool versions, Claude Code version, metadata hashes, and result-producing tool hashes. Resuming the same collection from a different harness commit or execution environment is rejected.

Failed tasks remain in the dataset when the run itself is admissible.

### Progress and interruption recovery

Inspect a long-running collection without mutating it:

```bash
python3 scripts/inspect-ai-native-formal-progress.py \
  --runs-root /path/to/formal-runs \
  --schedule docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/formal-schedule-r2.json \
  --execution-profile docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/execution-profile-r2.json \
  --benchmark-lock docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/BENCHMARK-LOCK.json \
  --formal-plan-lock docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/formal-plan-r2.lock.json
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
  --notes 'Missed the stale-generation invariant.' \
  --evidence 'trace.jsonl: invariant was never inspected' \
  --evidence 'acceptance: stale-generation case failed'
```

Secondary codes may be supplied with repeated `--secondary` arguments. Failed reviews require a non-empty rationale and at least one evidence reference, and are content-bound to the run's `seal.json`. Follow `FAILURE-REVIEW-PROTOCOL.md` and complete causal reviews before using aggregate A/B/C results to explain failure-mode differences.

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
conclusion-r3.template.json
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
  --conclusions /path/to/conclusion-r3.json
```

## 6. Finalize the research artifact

```bash
python3 scripts/finalize-ai-native-research.py \
  --runs-root /path/to/formal-runs \
  --output-dir /path/to/research-results \
  --conclusions /path/to/conclusion-r3.json
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
collection-start.json (under the run collection)
research-report.md
research-artifact-manifest.json
```

## Frozen boundaries

```text
benchmark semantics  -> BENCHMARK-LOCK.json
analysis semantics   -> ANALYSIS-LOCK.json
execution mechanics  -> execution-profile-r2.json (after pilots)
formal order         -> formal-schedule-r2.json (after pilots)
execution + order    -> formal-plan-r2.lock.json (after pilots)
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

## Final artifact identity

The finalizer writes `research-artifact-manifest.json` after generating the research outputs. It records SHA-256 identities for the frozen benchmark/analysis inputs, execution metadata, collection manifest, core analysis/reporting tools, conclusion file when supplied, and generated result files.

Its `artifact_set_digest_sha256` is a compact content identity for the assembled research artifact. It is a tamper-evident content digest, not a digital signature.


## 7. Archive the sealed raw collection

After strict finalization succeeds:

```bash
python3 scripts/archive-ai-native-raw-runs.py \
  --runs-root /path/to/formal-runs \
  --collection-manifest /path/to/research-results/collection-manifest.json \
  --output /path/to/archives/nession-ai-native-r3.zip
```

Retain both the archive and its generated `.manifest.json` sidecar in durable
storage. See `DATA-RETENTION.md`.

## 8. Publish the completed study back into Narness

```bash
python3 scripts/publish-ai-native-research.py \
  --runs-root /path/to/formal-runs \
  --results-dir /path/to/research-results \
  --conclusions /path/to/conclusion-r3.json \
  --raw-archive-manifest /path/to/archives/nession-ai-native-r3.zip.manifest.json
```

The default destination is:

```text
docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/published/benchmark-r3-analysis-r2/
```

Publication refuses incomplete results. It copies the reviewed report, raw tabular
measurements, paired effects, failure taxonomy, conclusion, collection identity,
collection-start lock, and frozen profile/schedule/formal-plan inputs into one
Git-friendly bundle.

It intentionally does **not** duplicate every raw trace/diff into Git. The
published `collection-manifest.json` retains every run-seal identity, and the
full sealed run collection should be retained separately according to the raw-data
retention policy.

The generated `publication-manifest.json` content-addresses the published file
set and records the source research-artifact digest. Review the bundle, then
commit it as the permanent Narness research record.


## Usage-event invariant

Every formal run is one fresh ephemeral Claude Code task and must emit exactly one
`usage` event. This keeps token accounting unambiguous under the frozen scorer.
A run with zero or multiple usage events is instrumentation-invalid and cannot be
sealed for final analysis.
