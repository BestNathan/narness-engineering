---
name: narness
description: "Harness engineering — constrain AI agents with code, hooks and scripts instead of prompts. Use when establishing constraints for any project, or when sinking a rule that keeps failing under prompt-only constraint into code."
---

# Narness — harness engineering

Sink constraints on an AI agent from "prompts" down to "code, hooks, scripts", guaranteeing correctness on long-running tasks.

## Core idea

When code, hooks, or scripts can constrain an agent, prefer them over prompts. Prompts are soft constraints an agent may ignore; scripts are hard constraints an agent cannot escape. See [references/why-not-prompts.md](references/why-not-prompts.md).

## The constraint ladder

| Level | Means | Strength |
|---|---|---|
| L0 Prompts | verbal/doc requirements | weakest |
| L1 Project conventions | CLAUDE.md / AGENTS.md | weak |
| L2 Skill | this skill | weak-medium |
| L3 Hook | edit-time hook (feeds back) / git hook (blocks) | medium-strong |
| L4 Scripts | `narness-*.sh` validation scripts | strong |
| L5 Compile-time | `#![forbid]`, `-D warnings`, dependency removal | strongest |

Full treatment: [references/constraint-ladder.md](references/constraint-ladder.md).

## Harness checkpoints

A harness is a sequence of checkpoints — each asks one yes/no question and is backed by one single-responsibility script. Eight checkpoints: Format, Compile, Lint, Invariants, Test, Coverage, Test discipline, Dependency audit. See [references/harness-checkpoints.md](references/harness-checkpoints.md).

## The two surfaces

Edit-time hooks (Claude Code / Codex) **feed back** a failure into the agent's context; git hooks and CI **block**. A git hook cannot teach — it only refuses — so its diagnostics must be self-contained. See [references/claude-code-hooks.md](references/claude-code-hooks.md), [references/codex-hooks.md](references/codex-hooks.md), [references/git-hooks.md](references/git-hooks.md).

## Changed vs full scope

Lint and unit/integration test are scope-aware: `--scope=changed` runs only the crates changed since the last push (the crate is the unit of change), `--scope=full` runs the whole workspace; `--coverage` toggles the coverage threshold. When the changed set can't be determined, it fails safe to full — a gate never under-checks. See [references/rust-test.md](references/rust-test.md).

## Config minimalism

Only set what differs from a tool's default; comment out the rest. Every *active* config line is a deliberate override; every commented line is a documented default. See [references/rust-tool-config.md](references/rust-tool-config.md).

## Steps to sink a constraint

1. **Identify** — which rule does the agent repeatedly violate?
2. **Locate the level** — which of L3–L5 does this rule best fit?
3. **Implement** — L3 configure a hook → L4 call a validation script → L5 add a lint / `#![forbid]` / trait bound.

## Index

| Topic | Reference |
|---|---|
| Why not just prompts | [references/why-not-prompts.md](references/why-not-prompts.md) |
| The constraint ladder | [references/constraint-ladder.md](references/constraint-ladder.md) |
| Checkpoints + script design | [references/harness-checkpoints.md](references/harness-checkpoints.md) |
| What each tool can enforce | [references/tool-checkpoints.md](references/tool-checkpoints.md) |
| Command interception | [references/command-interception.md](references/command-interception.md) |
| When to sink a constraint | [references/decision-guide.md](references/decision-guide.md) |
| Long-running correctness | [references/long-running-correctness.md](references/long-running-correctness.md) |
| Claude Code hooks | [references/claude-code-hooks.md](references/claude-code-hooks.md) |
| Codex hooks | [references/codex-hooks.md](references/codex-hooks.md) |
| Git hooks | [references/git-hooks.md](references/git-hooks.md) |
| Rust: format harness | [references/rust-fmt.md](references/rust-fmt.md) |
| Rust: lint harness | [references/rust-lint.md](references/rust-lint.md) |
| Rust: test harness | [references/rust-test.md](references/rust-test.md) |
| Rust: recommended tool configs | [references/rust-tool-config.md](references/rust-tool-config.md) |

## Scripts

All scripts live in `../../scripts/` and start with `narness-`. Rust gates keep the `narness-rust-*` name; the git hook machinery keeps `narness-git-*`.

| Script | Purpose |
|---|---|
| `narness-rust-fmt.sh [DIR]` | format check: `cargo fmt --all -- --check` |
| `narness-rust-check.sh [DIR]` | compile check: `cargo check` |
| `narness-rust-clippy.sh [DIR] [--scope=changed\|full]` | lint check: `cargo clippy -D warnings` |
| `narness-rust-test-unit.sh [DIR] [--scope=changed\|full] [--coverage]` | unit tests; `--coverage` = enforce ≥95% |
| `narness-rust-test-integration.sh [DIR] [--scope=changed\|full] [--coverage]` | integration tests; `--coverage` = enforce ≥80% |
| `narness-rust-test-e2e.sh [DIR]` | e2e scenarios, always full, no coverage |
| `narness-rust-test.sh [DIR]` | full suite: `cargo test --workspace` |
| `narness-rust-invariants.sh [DIR]` | invariants: ban unwrap/expect/panic!/unsafe without comment |
| `narness-rust-test-discipline.sh [DIR]` | test discipline: a changed .rs must have a test |
| `narness-rust-changed-packages.sh [DIR]` | helper: crates changed since last push (backs `--scope=changed`) |
| `narness-git-commit-msg.sh <msg-file>` | commit-message format gate |
| `narness-git-install.sh [REPO]` | install the three git hooks + `core.hooksPath` |

## Config templates

Copyable per-tool config templates live in `../../config/` (rustfmt.toml, clippy.toml, deny.toml, nextest.toml, rust-toolchain.toml, strict-lints.rs, .editorconfig, pre-commit, CI). The map is in [references/rust-tool-config.md](references/rust-tool-config.md).

## Common anti-patterns and their hard constraints

| Anti-pattern | Hard constraint |
|---|---|
| `unwrap()` everywhere | `clippy::unwrap_used` + `narness-rust-invariants.sh` |
| bare `panic!` | `clippy::panic` + thiserror/anyhow |
| forgetting tests | `narness-rust-test-discipline.sh` + hook |
| format drift | `cargo fmt --all -- --check` gate |
| "the agent will remember to format before committing" | pre-commit → `narness-rust-fmt.sh` |
| pushing broken or untested code | pre-push → `narness-rust-test-unit.sh --scope=changed` |
| treating a git hook as unbypassable | server-side `pre-receive` or CI |
