# Instrumentation Pilot Plan

> Active execution: direct Claude Code pre-pilot R6. Follow
> [EXECUTION-PREPILOT-R6.md](EXECUTION-PREPILOT-R6.md) for client installation,
> environment variables, pilots, isolation, and promotion. The Codex R4 and
> containerized Claude R5 instructions below are historical and must not be used
> for the new execution profile. Formal collection, analysis, and publication
> procedures still apply after R6 freeze.

> Non-reportable. These runs validate measurement plumbing only.

Benchmark revision 2 and Analysis revision 2 are frozen. The remaining gate before formal A/B/C collection
is to prove that a real coding-agent harness produces complete, scoreable traces.

## Pilot matrix

Use one fresh Claude Code CLI process per run through the GitHub-hosted R6
workflow:

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
agent:              Claude Code CLI
model:              repository variable CLAUDE_MODEL (explicit ID)
reasoning effort:   high
session:            ephemeral / fresh
permission profile: claude-direct-narness-r6
approval:           dontAsk
network in agent:   provider-direct (Anthropic endpoint only)
user/project config: ignored
hooks/MCP/subagents/web: disabled
dependency setup:   cd web && npm ci
```

Do not change the profile between P1/P2/P3.

The Claude Code `stream-json` stream is retained as `claude.raw.jsonl` and
translated by `scripts/narness-claude-adapter.py` into the benchmark's structured
`trace.jsonl`.

## Hosted workflow

Run the **AI Native Claude Code Pilots** workflow from the repository Actions
tab with `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, and an explicit
`CLAUDE_MODEL`. It executes T05/A, T08/B, and T20/C, scores each run, validates
the handoff, and uploads all evidence as a non-reportable artifact.

## Pilot acceptance

All three pilots must satisfy:

```text
fresh standalone single-ref checkout created (no remote or object alternates)
setup succeeded
fixture applied if required
agent completed without harness failure
trace.jsonl present and parseable
raw Claude Code JSONL preserved as `claude.raw.jsonl`
at least one navigation event captured
at least one edit event captured
exactly one usage event captured for the one ephemeral Claude Code turn
hidden acceptance ran after agent exit
build/lint verification completed
score.json generated
gold classification completed
no hidden oracle visible before agent exit
standalone checkout destroyed after run
```

Task success itself is **not** required for a pilot to validate instrumentation.

However, if a metric is missing because the adapter cannot observe the relevant
Claude Code event, repair the adapter before formal collection. Adapter changes during
pilot stage must not alter benchmark semantics.

## Freeze after pilot

When P1/P2/P3 pass instrumentation acceptance, freeze an execution profile with:

```text
Claude Code CLI version
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
record, score, structured trace, raw Claude Code JSONL, final diff, Git status, and
agent logs, plus the common Narness harness commit. Those per-pilot hashes are
collapsed into one `pilot_set_digest_sha256`.

This means the formal plan is not merely derived from "some pilots". It is
cryptographically bound to the exact non-reportable evidence that established
the execution profile. Re-running or editing a pilot requires a newly generated
execution profile/formal plan before formal collection.


## Hosted pilot gate

The active pilot path is the manually dispatched GitHub Actions workflow
`.github/workflows/ai-native-claude-pilots.yml`; its local shell entry point is
implementation detail, not an execution instruction.

Before spending model budget, the script runs
`scripts/preflight-ai-native-codex-pilots.py` and rejects:

- dirty tracked state in either repository;
- missing frozen treatment/oracle commits;
- benchmark-integrity failure;
- missing Git/Node/npm/Claude Code executables;
- pre-existing pilot output directories.

After all three pilots pass, the workflow writes:

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
requires one ephemeral Claude Code task to produce exactly one completed-turn usage
record. Pilot validation and formal sealing reject zero or multiple usage events
instead of silently changing token-accounting semantics.

If a future Claude Code CLI version emits multiple completed-turn usage records for one
task, do not patch the scorer in place after data collection begins. Resolve the
instrumentation semantics before formal collection or create a new benchmark
revision.
