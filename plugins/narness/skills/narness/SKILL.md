---
name: narness
description: "AI Workspace and harness engineering — design repository contracts, Skills, deterministic constraints, evidence, hooks, Git gates, and CI authority. Use when establishing an AI coding workspace or sinking a repeatedly violated rule into stronger enforcement."
---

# Narness — AI Workspace Engineering

Narness designs the repository around the agent rather than relying on the agent to remember a long prompt.

## The workspace model

```text
AI Workspace
=
Context Architecture
+ Capability Architecture
+ Constraint Architecture
+ Evidence Architecture
+ Lifecycle Orchestration
```

The goal is a workspace that progressively reveals the right context, exposes task procedures as capabilities, gives deterministic feedback during work, requires evidence appropriate to the change, and blocks unproven states from authoritative history.

## Progressive disclosure

Use four stages:

1. **Metadata** — Skill name and description are available for cheap selection.
2. **Procedure** — read the selected `SKILL.md` completely.
3. **Detail** — read only task-relevant references.
4. **Execution** — prefer deterministic scripts and assets for repeated operations.

> Load metadata broadly, instructions selectively, detail lazily, execution deterministically.

A Skill description is a routing interface. It must distinguish when the Skill applies and when it does not.

## Knowledge ownership

| Knowledge | Owner |
|---|---|
| Global standing rules | root AGENTS / CLAUDE |
| Scoped standing rules | subtree AGENTS / CLAUDE |
| Task procedures | Skills |
| Detailed task knowledge | Skill references |
| Repeated deterministic operations | scripts |
| Historical design reasoning | ADRs / design notes |
| Repository acceptance | CI / repository rules |

## Constraint ladder

| Level | Means | Primary role |
|---|---|---|
| L0 Prompt | natural-language request | intent |
| L1 AGENTS / convention | standing repository instruction | orientation |
| L2 Skill | on-demand procedure | capability |
| L3 Agent hook | event-driven feedback | teach |
| L4 Deterministic script | executable pass/fail | prove |
| L5 Language / tool-native rule | compiler, linter, schema, policy | prevent |
| L6 Git lifecycle gate | pre-commit / commit-msg / pre-push | check |
| L7 CI / repository ruleset | server-side required status | block |

See [references/constraint-ladder.md](references/constraint-ladder.md).

The goal is to place each invariant at the lowest practical layer that can express it correctly, not to force every rule into CI.

## Evidence-first checkpoints

A checkpoint is not just a command:

```text
Checkpoint
=
Invariant
+ Scope
+ Evidence
+ Executor
+ Failure Feedback
```

See [references/harness-checkpoints.md](references/harness-checkpoints.md).

Evidence should match the behavioral surface:

- pure logic -> focused unit evidence;
- public API/protocol -> contract + integration evidence;
- UI -> snapshot/screenshot/interaction proof;
- model-visible prompt/tool schema -> transcript/schema snapshot;
- database -> migration/invariant proof;
- concurrency -> deterministic lifecycle regression;
- deployment -> manifest/policy + health proof;
- release -> artifact and live proof.

## Lifecycle semantics

### Edit time

Run cheap corrective checks. Agent hooks teach by feeding failure diagnostics back into context.

### Git lifecycle

Run the smallest sufficient proof for the outgoing change. Client hooks are fast and bypassable.

### CI

Run authoritative proof. CI and repository rules are the source of truth for whether a state may enter shared history.

### Release

Add artifact, deployment, package, and live-system proof where applicable.

## Changed vs full scope

Rust lint and unit/integration tests are scope-aware:

- `--scope=changed` targets affected crates for fast local proof.
- `--scope=full` checks the whole workspace.
- e2e is always full and scenario-driven.
- `--coverage` enables coverage thresholds.
- unknown scope or root workspace changes fail safe to full.

The future evidence planner generalizes this from "changed crates" to "changed surfaces -> required evidence". The proposed `narness plan` interface is architectural direction and is not shipped yet.

## Config minimalism

Only set what differs from a tool's default. Every active config line should represent a deliberate override.

See [references/rust-tool-config.md](references/rust-tool-config.md).

## Steps to sink a constraint

1. **Observe** — identify a real failure or repeatedly violated rule.
2. **Name the invariant** — state what must remain true.
3. **Choose the layer** — find the lowest practical L3-L7 enforcement point.
4. **Choose evidence** — define what proves the invariant.
5. **Implement one deterministic primitive** — keep it single-responsibility.
6. **Mount it** — agent hook, Git hook, CI, or native tool as appropriate.
7. **Fail actionable** — diagnostics must say where, why, and how to fix.

## Reference index

| Topic | Reference |
|---|---|
| Why not just prompts | [references/why-not-prompts.md](references/why-not-prompts.md) |
| Constraint ladder | [references/constraint-ladder.md](references/constraint-ladder.md) |
| Checkpoints and evidence | [references/harness-checkpoints.md](references/harness-checkpoints.md) |
| Tool enforcement map | [references/tool-checkpoints.md](references/tool-checkpoints.md) |
| Command interception | [references/command-interception.md](references/command-interception.md) |
| Decision guide | [references/decision-guide.md](references/decision-guide.md) |
| Long-running correctness | [references/long-running-correctness.md](references/long-running-correctness.md) |
| Claude Code hooks | [references/claude-code-hooks.md](references/claude-code-hooks.md) |
| Codex hooks | [references/codex-hooks.md](references/codex-hooks.md) |
| Git hooks | [references/git-hooks.md](references/git-hooks.md) |
| Rust format | [references/rust-fmt.md](references/rust-fmt.md) |
| Rust lint | [references/rust-lint.md](references/rust-lint.md) |
| Rust test | [references/rust-test.md](references/rust-test.md) |
| Rust tool config | [references/rust-tool-config.md](references/rust-tool-config.md) |

## Shipped scripts

All plugin scripts live in `../../scripts/` and start with `narness-`.

| Script | Purpose |
|---|---|
| `narness-rust-fmt.sh [DIR]` | format check |
| `narness-rust-check.sh [DIR]` | compile check |
| `narness-rust-clippy.sh [DIR] [--scope=changed\|full]` | lint check |
| `narness-rust-test-unit.sh [DIR] [--scope=changed\|full] [--coverage]` | unit evidence |
| `narness-rust-test-integration.sh [DIR] [--scope=changed\|full] [--coverage]` | integration evidence |
| `narness-rust-test-e2e.sh [DIR]` | full scenario evidence |
| `narness-rust-invariants.sh [DIR]` | project invariants |
| `narness-rust-test-discipline.sh [DIR]` | changed source has test evidence |
| `narness-rust-changed-packages.sh [DIR]` | changed crate resolver |
| `narness-git-commit-msg.sh <msg-file>` | commit-message gate |
| `narness-git-install.sh [REPO]` | install Git lifecycle hooks |

## Anti-patterns

| Anti-pattern | Better workspace mechanism |
|---|---|
| "The agent will remember" | deterministic hook or gate |
| Giant root instruction file | root router + scoped instructions + Skills |
| Skill that contains every detail | progressive references |
| CI-only validation logic | reusable executable primitive |
| One god validation script | single-responsibility checkpoints |
| Full suite after every edit | lifecycle-aware evidence |
| Local hook treated as authority | server-side required CI |
| Running many tests without rationale | change-surface evidence selection |
