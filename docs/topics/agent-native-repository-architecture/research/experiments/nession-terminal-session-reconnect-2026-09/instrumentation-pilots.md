# Instrumentation Pilot Plan

> Non-reportable. These runs validate measurement plumbing only.

Benchmark revision 2 and Analysis revision 2 are frozen. The remaining gate before formal A/B/C collection
is to prove that a real coding-agent harness produces complete, scoreable traces.

## Pilot matrix

Use one fresh Codex CLI process per run:

| Pilot | Task | Treatment | Why |
|---|---|---|---|
| P1 | T05 | A | local transport bug; baseline grep/glob/read behavior |
| P2 | T08 | B | cross-capability feature; semantic resolver exposure |
| P3 | T20 | C | structural refactor; localized unit ownership |

This intentionally exercises all three treatment classes without producing
reportable experiment results.

## Fixed pilot execution profile

Candidate profile:

```text
agent:              Codex CLI
model:              gpt-5.6-sol
reasoning effort:   high
session:            ephemeral / fresh
sandbox:            workspace-write
approval:           never
network in agent:   disabled
user config:        ignored
exec policy rules:  ignored
dependency setup:   cd web && npm ci
```

Do not change the profile between P1/P2/P3.

The Codex non-interactive JSONL stream is translated by
`scripts/ai-native-codex-adapter.py` into the benchmark's structured
`trace.jsonl`.

## Example

From a checkout of `narness-engineering`, with a local checkout of Nession at
`../nession` and Codex already authenticated:

```bash
EXP=docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09

python3 scripts/ai-native-repo-experiment.py \
  --source-repo ../nession \
  --task "$EXP/runner/manifests/T05.json" \
  --treatments "$EXP/runner/treatments.json" \
  --treatment A \
  --attempt 1 \
  --setup-cmd 'cd web && npm ci' \
  --agent-cmd 'python3 /ABS/PATH/narness-engineering/scripts/ai-native-codex-adapter.py' \
  --output-dir ./research-runs
```

Then score the run:

```bash
python3 scripts/score-ai-native-run.py \
  --run-dir ./research-runs/T05-A-01 \
  --gold "$EXP/runner/gold.json" \
  --treatment A \
  --update-run-json
```

Repeat for:

```text
T08 / B
T20 / C
```

## Pilot acceptance

All three pilots must satisfy:

```text
fresh detached worktree created
setup succeeded
fixture applied if required
agent completed without harness failure
trace.jsonl present and parseable
raw Codex JSONL preserved
at least one navigation event captured
at least one edit event captured
exactly one usage event captured for the one ephemeral Codex turn
hidden acceptance ran after agent exit
build/lint verification completed
score.json generated
gold classification completed
no hidden oracle visible before agent exit
worktree destroyed after run
```

Task success itself is **not** required for a pilot to validate instrumentation.

However, if a metric is missing because the adapter cannot observe the relevant
Codex event, repair the adapter before formal collection. Adapter changes during
pilot stage must not alter benchmark semantics.

## Freeze after pilot

When P1/P2/P3 pass instrumentation acceptance, freeze an execution profile with:

```text
Codex CLI version
model
reasoning effort
adapter SHA
runner SHA
scorer SHA
Node/npm versions
OS/runtime environment
network policy
time/token limits
```

Only then may reportable runs begin.

The generated execution profile also content-addresses the exact three pilot
evidence sets. For each pilot it records SHA-256 identities for the prompt, run
record, score, structured trace, raw Codex JSONL, final diff, Git status, and
agent logs, plus the common Narness harness commit. Those per-pilot hashes are
collapsed into one `pilot_set_digest_sha256`.

This means the formal plan is not merely derived from "some pilots". It is
cryptographically bound to the exact non-reportable evidence that established
the execution profile. Re-running or editing a pilot requires a newly generated
execution profile/formal plan before formal collection.


## One-command pilot gate

The pilot path is now intentionally one command:

```bash
./scripts/run-ai-native-codex-pilots.sh /path/to/nession
```

Before spending model budget, the script runs
`scripts/preflight-ai-native-codex-pilots.py` and rejects:

- dirty tracked state in either repository;
- missing frozen treatment/oracle commits;
- benchmark-integrity failure;
- missing Git/Node/npm/Codex executables;
- pre-existing pilot output directories.

After all three pilots pass, the same command writes:

```text
runner/execution-profile-r1.json
runner/formal-schedule-r1.json
runner/formal-plan-r1.lock.json
```

The formal schedule contains 216 pre-registered entries
(24 tasks × 3 treatments × 3 repetitions).

Treatment position is Latin-square balanced within each task, while task blocks
are deterministically SHA-256-permuted with seed `20260921` independently for
each replication. The exact resulting order is stored in the schedule itself.

These three generated metadata files must be reviewed and committed before formal
collection. The formal-plan lock content-addresses the exact execution-profile and
schedule bytes so they cannot drift after pre-registration. Formal execution pins runner/adapter/scorer bytes from the pilot-
derived execution profile, so committing metadata afterward does not alter the
measured tooling.


## Usage-accounting guard

The formal scorer aggregates `usage` events. The execution profile therefore
requires one ephemeral Codex task to produce exactly one completed-turn usage
record. Pilot validation and formal sealing reject zero or multiple usage events
instead of silently changing token-accounting semantics.

If a future Codex CLI version emits multiple completed-turn usage records for one
task, do not patch the scorer in place after data collection begins. Resolve the
instrumentation semantics before formal collection or create a new benchmark
revision.
