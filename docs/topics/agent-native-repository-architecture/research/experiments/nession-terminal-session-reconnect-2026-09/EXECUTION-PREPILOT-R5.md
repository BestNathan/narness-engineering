# Execution Pre-Pilot Revision 5: Claude Code

Status: registered execution candidate `8bab203034f97345541783c32c9e646d923b40a7`
on `research/ai-native-execution-prepilot-r5`. Local validation passed; GitHub CI
is pending publication. No real pilot or formal observation is claimed by
synthetic tests or by this document.

## Scope and frozen semantics

The requested execution agent is now Claude Code, replacing Codex before any
reportable collection. Benchmark R2 (`194bf5dc1a28f4e4c10491d7326891ba157d325b`),
Analysis R2 (`357c38c9b10a3eb668b15aead703a5f5200b2858`), all 24 task definitions,
A/B/C treatment SHAs, hidden oracle, gold scope, scorer, hypotheses, and analysis
implementation remain unchanged. Do not combine Codex and Claude observations
in one execution profile or formal dataset. R4 remains historical.

The same non-reportable pilots remain T05/A, T08/B, and T20/C. They must validate
instrumentation; task semantic success is not required. Formal collection is
still 24 tasks x 3 treatments x 3 repetitions = 216 runs.

## Configuration

Configure repository Actions settings, not source files or issue comments:

| Setting | Kind | Requirement |
|---|---|---|
| `ANTHROPIC_API_KEY` | Actions secret | Required; used only by the gateway |
| `CLAUDE_MODEL` | Actions variable | Required explicit model ID; moving aliases such as `sonnet` are rejected |
| `ANTHROPIC_BASE_URL` | Actions variable | Optional HTTPS Anthropic Messages-compatible base URL; defaults to `https://api.anthropic.com` |

A custom gateway must accept the configured model, streaming Messages requests,
and Claude Code's API headers. An OpenAI-only Chat Completions endpoint is not
compatible. URLs must not contain credentials or query parameters. The gateway
forwards the key as `x-api-key` and a Bearer authorization header; credentials
never enter the coding-agent container or its traces.

Claude Code is pinned to npm version `2.1.278` in the runtime Dockerfile. Effort is
`high`, the task limit is 100 agentic turns, and the runner's existing wall-clock
limit remains authoritative. Changing CLI version, model, tool availability,
container policy, or adapter requires new pilots and a newly frozen profile.

## Hosted execution

Run `AI Native Claude Code Pilots` from main. It uses `ubuntu-24.04` GitHub-hosted
runners; a self-hosted runner and stored Codex login are no longer required.
The workflow also triggers when its definition or the active execution lock is
updated. A run missing configuration fails with an actionable message; configure
the settings and rerun the workflow.

The controller checks out the exact execution SHA from the R5 registration lock
into a separate `execution` checkout. Execution never runs from the moving main
branch. Post-pilot handoff validation runs from the controller containing the
registration lock, avoiding the stale-lock problem inside self-referential
execution snapshots.

The old Codex workflow jobs are disabled. Previously queued runs retain their
old workflow definitions and should be canceled in Actions; they are not valid
R5 evidence and must never be promoted into the Claude profile.

## Isolation and provenance

Each agent gets a standalone single-ref subject repository, retaining R4's Git
object isolation. The Docker container mounts only this subject checkout; it has
no Narness checkout, hidden oracle, result directory, host home, credential store,
Docker socket, or source repository mount. Its root filesystem is read-only,
capabilities are dropped, and writable temporary/home directories are ephemeral.
The process runs as the host user with a fresh Claude session.

A separate gateway container holds the real API credential. The agent receives
only a placeholder key and the internal gateway address. The Docker network is
internal; host firewall rules deny agent-to-host access and allow forwarding
only to the gateway's port. The gateway allows only Messages/count_tokens paths,
only the chosen model, and a fixed HTTPS upstream. No arbitrary HTTP forwarding
or request/response logging is provided. Claude's tools can call this same model
gateway, so the policy is explicitly `internal-model-proxy`, not a claim that
all networking is impossible.

The only enabled tools are Bash, Read, Edit, Write, Glob, and Grep. User/project
settings, hooks, skills, external MCP servers, subagents, and web tools are
disabled. The normal model system prompt and subject repository content remain
part of the Claude execution treatment; no hidden research instructions are
mounted into the agent container.

The profile binds the exact CLI version, agent/gateway image IDs, upstream URL,
model, effort, turn limit, adapter and command-mapper hashes, runtime Dockerfile,
gateway implementation, raw pilot streams, and existing execution-tool hashes.
Formal readiness and run sealing reject drift. The handoff includes a compressed
Docker image archive; load this same image for formal collection rather than
rebuilding a tag and assuming it is identical. The image contains no API key.
The host runtime versions must also match the profile; hosted pilot success does
not waive the formal environment gate.

## Trace mapping

`claude.raw.jsonl` and `claude.stderr.log` preserve the native execution output.
The adapter matches tool_use/tool_result IDs, deduplicates repeated assistant
envelopes, and rejects unmatched results, subagent activity, incomplete streams,
error terminal results, missing usage, and multiple terminal results.

Read/Edit/Write/Grep/Glob produce the existing navigation/edit events. Bash uses
the existing command classifier, whose bytes are additionally frozen. A failed
Bash tool result maps to a nonzero validation status; successful results map to
zero. This is a success/failure observation, not a claim that Claude exposes the
exact shell exit number.

Only the final result's cumulative usage becomes a benchmark usage event. Input
tokens include uncached input + cache reads + cache creation. Cached tokens count
cache reads. Output tokens use Claude's reported total. Claude does not expose a
separate reasoning-token counter here; the trace records its unavailability and
does not fabricate an estimate. No scorer changes are made. Synthetic fixtures
prove mapping behavior only; real pilots must establish actual stream coverage.

## Freeze and promotion

After all three pilots validate, the execution checkout generates:

- `runner/execution-profile-r1.json`
- `runner/formal-schedule-r1.json`
- `runner/formal-plan-r1.lock.json`

Download the handoff and use a clean controller checkout containing the active R5
registration (and unchanged R5 result-producing tools):

```bash
python3 scripts/promote-ai-native-pilot-handoff.py --handoff-dir /path/to/handoff
```

Review and commit those three files plus generated `runner/PILOT-FREEZE.json` on
a formal-execution branch before starting any reportable run. Retain the original
pilot evidence and runtime image archive. Do not manually author the generated
profile, reuse a Codex profile, or count a synthetic replay as a real pilot.

Formal collection uses the existing `run-ai-native-formal.py` entrypoint. It now
selects the adapter and verifies the runtime according to the committed agent
profile. Start the isolated gateway/network with the same policy as the workflow,
load the archived image, and set `NARNESS_CLAUDE_IMAGE`, `NARNESS_CLAUDE_NETWORK`,
`NARNESS_CLAUDE_PROXY`, and `NARNESS_CLAUDE_UPSTREAM` for the harness. Keep the real
API key only in the gateway. The collection-start gate must pass before spending
formal model budget.

## Primary references

- https://code.claude.com/docs/en/cli-reference
- https://code.claude.com/docs/en/headless

These document print mode, stream-json, settings/tool controls, and nonpersistent
sessions. CLI flag availability is checked against the pinned installed runtime
in the hosted workflow. A real pilot is still required to validate provider and
stream compatibility.
