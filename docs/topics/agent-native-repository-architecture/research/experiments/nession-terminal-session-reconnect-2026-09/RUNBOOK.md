# Experiment Runbook

This is the operational path from the frozen benchmark to the final research report.

## 1. Run the three non-reportable pilots

Use a trusted machine with a clean Nession checkout and a **stored authenticated
Codex session**. The preflight executes `codex login status` and rejects
`OPENAI_API_KEY` / `CODEX_ACCESS_TOKEN` when exported into the experiment
process environment; the coding agent must not inherit authentication secrets.

### Local path

```bash
git switch --detach d01117beb44e57c24cb6b73ae8c4c9f89100e825
bash ./scripts/run-ai-native-codex-pilots.sh /path/to/nession
```

### Trusted self-hosted GitHub Actions path

A second entry point is:

```text
.github/workflows/ai-native-codex-pilots-self-hosted.yml
```

It runs only on a self-hosted runner carrying the `ai-native-research` label.
The runner must already have Codex authenticated in its credential store and must
have a clean local Nession checkout. Dispatch the workflow with the absolute
`nession_path`. Select `main` when dispatching the repaired workflow; it
explicitly checks out the frozen R4 SHA rather than executing the selected branch.

The workflow deliberately:

```text
uses persist-credentials: false for actions/checkout
rejects OPENAI_API_KEY
rejects CODEX_ACCESS_TOKEN
checks codex login status
uses the normal benchmark preflight
uploads pilot traces + generated freeze metadata as a non-reportable artifact
```

This path is intended for a trusted private runner, not a public or untrusted CI
executor.


### Validate and promote using the R4 registration checkout

The execution commit `d01117beb44e57c24cb6b73ae8c4c9f89100e825` still
contains the earlier R3 registration lock. Its own handoff validator therefore
cannot authorize R4 evidence. Run pilots at that exact execution commit, then
validate/promote using the separate, pinned registration checkout
`88d08dd95b69a217f9433b84b35179663ace4e09`. Both self-hosted workflows use
that checkout under `pilot-control` after pilot execution. Never overlay the
registration files onto the pilot checkout before running pilots.

After downloading/unzipping the workflow artifact, use a separate checkout:

```bash
git clone https://github.com/BestNathan/narness-engineering.git /path/to/formal-control
cd /path/to/formal-control
git switch -c research/ai-native-formal-execution-r1 88d08dd95b69a217f9433b84b35179663ace4e09
python3 scripts/promote-ai-native-pilot-handoff.py \
  --handoff-dir /path/to/pilot-handoff
```

The promoter first validates the handoff. It requires all three run records and
the execution profile to identify R4, checks the isolated checkout and permission
profile, compares result-producing tool hashes with R4, revalidates the pilot
traces and artifact hashes, and verifies profile/schedule/formal-plan identity.
Task semantic success is not required; instrumentation acceptance is required.

Review the generated metadata, then commit it:

```bash
EXP=docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09
for name in execution-profile-r1.json formal-schedule-r1.json formal-plan-r1.lock.json PILOT-FREEZE.json; do
  python3 -m json.tool "$EXP/runner/$name"
done
# Commit only after reviewing the displayed metadata and validation report.
git add "$EXP/runner/execution-profile-r1.json" \
  "$EXP/runner/formal-schedule-r1.json" \
  "$EXP/runner/formal-plan-r1.lock.json" \
  "$EXP/runner/PILOT-FREEZE.json"
git commit -m "research: freeze pilot-derived formal execution plan r1"
```

The first three files are required by the collection-start gate. The fourth
records promotion provenance. The formal branch descends from R4 via the pinned
registration commit; the result-producing execution tools remain byte-identical
to R4 and are checked against the pilot profile. Keep the pilot handoff in durable
storage. Never synthesize a profile or treat a replay/selftest as pilot evidence.

For local pilots, assemble `pilot-handoff` outside the execution checkout by
copying the three generated JSON files into it and the complete pilot output
directory into `pilot-handoff/pilot-runs`, then follow the same promotion steps.
The optional workflow metadata file is not needed for local execution.

### Runner readiness

A queued Actions job with `runner_id=0` has not begun pilot execution. Bring an
eligible trusted runner online with both `self-hosted` and `ai-native-research`
labels, or use the local path above. The runner account must have a working
`codex login status`, Git, Python, Node/npm, and a clean Nession checkout containing
the frozen treatment/oracle commits. Do not export `OPENAI_API_KEY` or
`CODEX_ACCESS_TOKEN` into the experiment process.

Do not launch duplicate pilot jobs. A queued run keeps its original workflow
version; after an entrypoint repair, cancel the obsolete queued run in Actions
before using the repaired manual workflow. If an old run already generated real
evidence but failed only at the R3 handoff check, retain its artifact and validate
it with the R4 registration checkout before deciding whether pilots must rerun.

The command performs preflight, executes T05/A, T08/B, and T20/C with fresh ephemeral sessions, scores the traces, validates instrumentation, freezes the execution profile, and generates the pre-registered 216-run schedule.

It writes:

```text
runner/execution-profile-r1.json
runner/formal-schedule-r1.json
runner/formal-plan-r1.lock.json
```

Review and commit all three generated metadata files before formal collection. `formal-plan-r1.lock.json` freezes the exact profile and schedule bytes.

The execution profile embeds a `pilot_set_digest_sha256` plus per-pilot artifact
hashes. Keep the pilot directories until the profile has been reviewed; afterward
the committed profile is the provenance record that binds the formal plan to the
exact pilot evidence.

## 2. Run formal collection

```bash
python3 scripts/run-ai-native-formal.py \
  --source-repo /path/to/nession \
  --schedule docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/formal-schedule-r1.json \
  --execution-profile docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/execution-profile-r1.json \
  --formal-plan-lock docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/formal-plan-r1.lock.json \
  --runs-root /path/to/formal-runs
```

The orchestrator validates benchmark/analysis integrity before model spending, enforces the frozen execution-tool bytes, runs the balanced schedule, scores every run, and writes a tamper-evident `seal.json` for every admissible outcome. Existing runs are never skipped merely because `run.json` says they are sealed; their artifact hashes are re-verified first.

Before the first reportable run, the orchestrator also creates:

```text
/formal-runs/_collection/collection-start.json
```

The collection-start lock requires the execution profile, formal schedule, and formal-plan lock to already be Git-tracked and byte-identical to the current Narness HEAD. It freezes that Narness commit, local runtime/tool versions, Codex CLI version, metadata hashes, and result-producing tool hashes. Resuming the same collection from a different harness commit or execution environment is rejected.

Failed tasks remain in the dataset when the run itself is admissible.

### Progress and interruption recovery

Inspect a long-running collection without mutating it:

```bash
python3 scripts/inspect-ai-native-formal-progress.py \
  --runs-root /path/to/formal-runs \
  --schedule docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/formal-schedule-r1.json \
  --execution-profile docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/execution-profile-r1.json \
  --benchmark-lock docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/BENCHMARK-LOCK.json \
  --formal-plan-lock docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/runner/formal-plan-r1.lock.json
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
conclusion-r2.template.json
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
  --conclusions /path/to/conclusion-r2.json
```

## 6. Finalize the research artifact

```bash
python3 scripts/finalize-ai-native-research.py \
  --runs-root /path/to/formal-runs \
  --output-dir /path/to/research-results \
  --conclusions /path/to/conclusion-r2.json
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
execution mechanics  -> execution-profile-r1.json (after pilots)
formal order         -> formal-schedule-r1.json (after pilots)
execution + order    -> formal-plan-r1.lock.json (after pilots)
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
  --output /path/to/archives/nession-ai-native-r2.zip
```

Retain both the archive and its generated `.manifest.json` sidecar in durable
storage. See `DATA-RETENTION.md`.

## 8. Publish the completed study back into Narness

```bash
python3 scripts/publish-ai-native-research.py \
  --runs-root /path/to/formal-runs \
  --results-dir /path/to/research-results \
  --conclusions /path/to/conclusion-r2.json \
  --raw-archive-manifest /path/to/archives/nession-ai-native-r2.zip.manifest.json
```

The default destination is:

```text
docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09/published/benchmark-r2-analysis-r2/
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

Every formal run is one fresh ephemeral Codex task and must emit exactly one
`usage` event. This keeps token accounting unambiguous under the frozen scorer.
A run with zero or multiple usage events is instrumentation-invalid and cannot be
sealed for final analysis.
