# Narness

Narness is research + tooling for **harness engineering** — constraining AI agents with code, hooks and scripts instead of prompts.

## Core idea

> When code, hooks, or scripts can constrain an AI agent's behavior, prefer them over prompts. An agent will very likely not follow prompts; scripts and hooks let the agent *discover* that its implementation is wrong and guide it toward correct behavior.

A rule can be implemented two ways:

- **Soft** (软实现) — text the agent reads (a prompt, `CLAUDE.md`, a skill). It shapes intent, but the agent can ignore it.
- **Hard** (硬实现) — code that runs on an event (a hook, a script, a CI step). It fires whether or not the agent cooperates, returns a deterministic verdict, and feeds the failure back so the agent has to fix it.

Harness engineering is the practice of **sinking** a rule from soft toward hard: a prompt is soft, a hook or script is hard.

## The problem, and how the harness solves it

**The problem:** on long-running, autonomous tasks an agent will very likely not follow prompts — a rule written only as text is a rule that will silently break.

**The solution:** express the rule as code that runs on an event, at the strongest level it can reach — the **constraint ladder**:

| Level | Means | Strength |
|---|---|---|
| L0 Prompts | verbal / doc requirements | weakest |
| L1 Project conventions | `CLAUDE.md` / `AGENTS.md` | weak |
| L2 Skill | a skill the agent invokes | weak-medium |
| L3 Hook | a tool hook / git hook | medium-strong |
| L4 Scripts | `narness-*.sh` validation scripts | strong |
| L5 Compile-time | `#![forbid]`, `-D warnings`, dependency removal | strongest |

The goal is to sink every rule from L0–L2 down to L3–L5. The harness runs on two surfaces:

- **Inner** — tool hooks (`PreToolUse` / `PostToolUse`) fire on every tool call and *feed failures back* into the agent's context the moment an edit is wrong — a tight, self-correcting loop.
- **Outer** — git hooks and CI *block* at commit / push / merge, so bad code never enters history even if the agent ignores every edit-time warning.

A harness is a sequence of **checkpoints**, each a yes/no question backed by one single-responsibility script: format, compile, lint, invariants, test, coverage, test discipline, and dependency audit.

## Tools

| Path | What it is |
|---|---|
| `plugins/narness/` | the harness-engineering plugin — a `narness` skill (design philosophy + reference index), a `PostToolUse` hook, validation scripts, git hooks, and copyable per-tool config templates |
| `cli/` | `narness`, an npm environment checker for an agent's runtime prerequisites |

## Usage

**Install the plugin:**

```bash
claude plugin marketplace add <this repo's URL>
claude plugin install narness
```

**Adopt the Rust harness in a project** — the plugin ships copyable config templates (`rustfmt.toml`, `clippy.toml`, `deny.toml`, …) and a git-hook installer; the skill's `rust-tool-config.md` reference maps each tool to its checkpoint and copy target.

**Check an agent's environment** — declare requirements in `.narness.toml`:

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
npx narness --json    # structured output (for hooks / CI)
```

## Documentation

The `narness` skill is the single entry point: [SKILL.md](plugins/narness/skills/narness/SKILL.md) states the design philosophy and indexes every reference — theory, per-tool, per-platform — in a flat [references/](plugins/narness/skills/narness/references/) directory.
