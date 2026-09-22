# Execution Pre-Pilot Revision 6: Direct Claude Code

Status: active execution candidate. This revision changes the coding agent from
Codex to an installed Claude Code client before any real or reportable pilot.
Benchmark R2 and Analysis R2 remain unchanged. R5's container and model-gateway
path is historical and must not be mixed with R6 evidence.

All active execution is hosted in GitHub Actions. The workflow uses a disposable
GitHub-hosted `ubuntu-24.04` machine; no self-hosted runner or local Claude Code
process is part of the R6 protocol.

## Required environment

Set these repository-level GitHub Actions values before dispatching
`.github/workflows/ai-native-claude-pilots.yml`:

```text
ANTHROPIC_API_KEY     required repository secret
ANTHROPIC_BASE_URL    optional repository variable; defaults to official endpoint
CLAUDE_MODEL          required explicit model ID; aliases are rejected
NARNESS_CLAUDE_BIN   not set in hosted workflow; defaults to claude
```

Do not paste the API key into source files, issue comments, logs, prompts, or
chat. The adapter passes the selected Anthropic credential only to the Claude
child process and never includes its value in trace metadata. Codex credentials
are rejected for this path.

## Hosted client installation

The workflow installs the pinned CLI on every fresh GitHub-hosted job:

```bash
npm install --global @anthropic-ai/claude-code@2.1.278
claude --version
```

The pilot preflight calls `claude --version` and verifies the configured base URL
and credential before spending model budget. A moving CLI or model version is not
accepted after the R6 profile is frozen.

## Pilot workflow

Dispatch **AI Native Claude Code Pilots** manually. The workflow checks out the
R6 execution SHA from `EXECUTION-PREPILOT-LOCK.json`, checks out
`BestNathan/nession` as a clean subject repository, and injects the secret only
into the pilot step.

The command runs T05/A, T08/B, and T20/C in fresh standalone single-ref subject
checkouts. It uses Claude Code print mode with `stream-json`, disables session
persistence, project/user settings, hooks, skills, web tools, MCP servers, and
subagents, and allows only Bash, Read, Edit, Write, Glob, and Grep. `Bash(*)` is
permitted because the subject checkout is the isolated execution workspace; the
harness and hidden evaluation files are outside it.

The child process receives a scrubbed environment containing ordinary runtime
variables plus `ANTHROPIC_BASE_URL` and the selected credential variable. All
`NARNESS_*` paths are removed. The raw native stream is retained as
`claude.raw.jsonl`; the adapter translates tool calls into the existing trace
contract and emits one cumulative usage event from the terminal result.

## Freeze and formal gate

After the three real pilots pass, the workflow generates the same three required
files:

```text
runner/execution-profile-r1.json
runner/formal-schedule-r1.json
runner/formal-plan-r1.lock.json
```

The profile binds the installed Claude version and resolved binary, exact model,
base URL, credential variable name, direct execution mode, adapter and command
mapper hashes, runner/scorer/sealing tools, and the three pilot artifact sets.
The formal readiness gate rechecks the installed client and base URL. Changing
the client, model, endpoint, adapter, or execution policy requires a new pilot
profile; do not silently continue an existing formal collection.

Review the handoff artifact, then dispatch **AI Native Claude Pilot Promotion**.
That hosted workflow validates the evidence and opens a draft PR containing the
three generated files plus `runner/PILOT-FREEZE.json`; merge that PR before any
216-run collection. Synthetic adapter tests are protocol tests only and cannot be
promoted as pilot evidence.
