# Narness

Narness is a "research + documentation + Claude Code tooling" project that articulates and puts into practice an engineering philosophy:

> When code, hooks, or scripts can constrain an AI agent's behavior, prefer them over prompts. An agent will very likely not follow prompts; scripts and hooks let the agent discover that its implementation is wrong and guide it toward correct behavior, thereby guaranteeing correctness on long-running tasks.

## The harness

A **harness** is everything that surrounds an AI agent and constrains what it does. The same rule can be implemented in two ways:

- **Soft implementation** (软实现) — the rule lives in text the agent reads (a prompt, `CLAUDE.md`, a skill). It shapes intent, but the agent can ignore it.
- **Hard implementation** (硬实现) — the rule lives in code that runs on an event (a hook, a script, a CI step). It fires whether or not the agent cooperates, returns a deterministic verdict, and feeds failure back so the agent has to fix it.

Harness engineering is the practice of **sinking** a rule from a soft implementation toward a hard one. A prompt is soft; a script or hook is hard — an agent will very likely not follow the prompt, but it cannot escape the hook.

### Layers

The harness isn't a single thing — it's nested layers around the model. Moving outward, each layer guards a later decision point, and each can be built soft (text) or hard (code):

```text
model
  └─ ReAct loop              think → act → observe — the runtime the harness hooks into
       ├─ inner harness      soft   Prompt · Skill · CLAUDE.md · AGENTS.md
       │                     hard   Tool hooks (PreToolUse / PostToolUse) — fire on every tool call
       └─ outer harness      hard   git hooks · GitHub Actions / CI · code review — fire on commit/push/merge
```

| Layer | Soft | Hard | Fires | Escapable |
|---|---|---|---|---|
| Inner — context | prompt, `CLAUDE.md`, skill | — | when the agent reads it | yes |
| Inner — tool call | — | tool hook | on every tool call | no |
| Outer — VCS / CI | — | git hook, CI step | at commit / push / merge | no |

The outer hooks are the last line of defense, but they fire late. The inner tool hooks give the same hard guarantee with a tight loop: the moment the agent's edit is wrong, a `PostToolUse` hook fails and its diagnostic is injected back into the agent's context. The two hard layers work together — fast inner feedback, thorough outer gating.

This layer map is the *topology*; the **constraint ladder** (L0 prompts → L5 compile-time) is the *strength* axis behind it. Narness ships plugins that populate the hard layers with code.

### Building harness logic on hooks

The tool-hook layer isn't a single check — it's a set of distinct decision points, one per [hook event](https://code.claude.com/docs/en/hooks). Each event is a place to mount harness logic, from "block this call" to "feed this failure back to the agent":

| Hook event | Harness logic it realizes |
|---|---|
| `PreToolUse` | block or rewrite a dangerous / out-of-scope tool call before it runs |
| `PostToolUse` | validate an edit the moment it lands; feed the failure back to the agent |
| `Stop` | don't let the agent declare "done" until the gate passes |
| `UserPromptSubmit` | gate or inject user input before it reaches the model |
| `SessionStart` | inject ground truth / env at session start |
| `PreCompact` | re-inject constraints so they survive context compaction |
| `PermissionRequest` | automated allow/deny policy for tool use |

Two events carry most of the weight: `PreToolUse` (block) and `PostToolUse` (feedback — a failing hook's stderr is injected back into the agent's context). The rest extend the same principle to the other moments of the agent lifecycle. See [Claude Code hooks](docs/reference/claude-code-hooks.md) for the full event table and the exit-code contract.

## Harness checkpoints

A harness is built from a small set of checkpoints — each one a yes/no question answered by one single-responsibility script:

| Checkpoint | Guards against | Script design |
|---|---|---|
| Format | style drift, diff noise | check-only gate; auto-fix on the hook tier; rules fixed in config |
| Compile / type-check | broken builds | fastest check; immediate after-edit feedback |
| Lint | code smells | warnings escalated to errors; sunk to `forbid` at compile time |
| Invariants | project-specific rule violations | grep scan for what the linter can't express |
| Test | wrong behavior | three tiers — unit (pre-push), integration + e2e (CI) — each a deterministic gate with localizable failures |
| Coverage | untested critical paths | per-tier numeric threshold (unit ≥95%, integration ≥80%); uncovered lines fed back |
| Test discipline | silently missing tests | VCS diff → test-file mapping |
| Dependency audit | vulnerable dependencies | lockfile audit on the slow tier |

See [harness checkpoints](docs/theory/harness-checkpoints.md) for the design rubric behind each.

## Layout

- `docs/theory/` — theory and research docs
- `docs/reference/` — harness-engineering references for specific tools
- `plugins/narness-rust/` — the Rust harness-engineering plugin (skill + hook + scripts)
- `cli/` — the narness environment checker (npm package)
- `.claude-plugin/marketplace.json` — marketplace definition

## Quick start

Install the `narness-rust` plugin after adding the marketplace:

```bash
claude plugin marketplace add <this repo's URL>
claude plugin install narness-rust
```

## Theory docs

- [Why not just prompts](docs/theory/why-not-prompts.md)
- [The constraint ladder](docs/theory/constraint-ladder.md)
- [Decision guide](docs/theory/decision-guide.md)
- [Correctness of long-running tasks](docs/theory/long-running-correctness.md)
- [Harness checkpoints](docs/theory/harness-checkpoints.md) (the checkpoint taxonomy + script-design rubric)
- [Tool checkpoints](docs/theory/tool-checkpoints.md) (what each tool can enforce: git, GitHub, GitLab, Claude Code, Codex)
- [Command interception](docs/theory/command-interception.md) (replacing and normalizing agent commands via config + the narness CLI)

## Reference docs

- [Rust test harness engineering](docs/reference/rust-test-harness.md) (nextest + llvm-cov + LLM feedback)
- [Git hooks](docs/reference/git-hooks.md) (harness execution at commit/push time)
- [Claude Code hooks](docs/reference/claude-code-hooks.md) (harness execution at agent tool-call time)
- [Codex hooks](docs/reference/codex-hooks.md) (harness execution in the OpenAI Codex CLI)

## Environment check

`cli/` is an npm package. Put a `.narness.toml` in the project root declaring the agent's runtime requirements, then check them with `npx narness`:

```toml
[[checks]]
type = "version"
name = "node"
min = "22"

[[checks]]
type = "exists"
name = "rg"
```

```bash
npx narness           # human report (failures include fix suggestions)
npx narness --json    # structured output (for hooks/CI)
```
