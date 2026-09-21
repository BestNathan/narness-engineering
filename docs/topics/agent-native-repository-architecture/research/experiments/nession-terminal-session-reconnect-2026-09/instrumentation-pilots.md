# Instrumentation Pilot Plan

> Non-reportable. These runs validate measurement plumbing only.

Benchmark revision 1 is frozen. The remaining gate before formal A/B/C collection
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
usage event captured
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
