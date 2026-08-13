---
name: narness-rust
description: "Guide to applying harness engineering in Rust projects — constrain an AI agent with cargo/clippy/hooks/scripts instead of prompts. Use when establishing constraints for a Rust project, or when sinking a rule that keeps failing under prompt-only constraint into code."
---

# Narness Rust — Rust harness engineering

Sink constraints on an AI agent from "prompts" down to "code, hooks, scripts", guaranteeing correctness on long-running tasks.

## Core idea

When code, hooks, or scripts can constrain an agent, prefer them over prompts. Prompts are soft constraints an agent may ignore; scripts are hard constraints an agent cannot escape.

## The constraint ladder (Rust mapping)

| Level | Means | Strength |
|---|---|---|
| L0 Prompts | verbal/doc requirements | weakest |
| L1 Project conventions | CLAUDE.md | weak |
| L2 Skill | this skill | weak-medium |
| L3 Hook | PostToolUse validation | medium-strong |
| L4 Scripts | narness-rust-*.sh / narness-rust-invariants.sh | strong |
| L5 Compile-time | clippy -D warnings, #![forbid] | strongest |

## When to use this skill

- When establishing harness constraints for a Rust project
- When the agent repeatedly violates the same kind of constraint (e.g. always writing unwrap, always forgetting tests)
- When sinking a rule that "fails under prompt-only constraint" into code

## Steps to sink a constraint

1. Identify: which rule does the agent repeatedly violate?
2. Locate the level: which of L3–L5 does this rule best fit?
3. Implement:
   - L3 → configure a PostToolUse hook to run a validation script
   - L4 → call a validation script under scripts/
   - L5 → add a clippy lint / `#![forbid(...)]` / trait bound

## Available scripts

| Script | Purpose |
|---|---|
| `scripts/narness-rust-fmt.sh [DIR]` | format check: cargo fmt --check |
| `scripts/narness-rust-check.sh [DIR]` | compile check: cargo check |
| `scripts/narness-rust-clippy.sh [DIR]` | lint check: cargo clippy -D warnings |
| `scripts/narness-rust-test.sh [DIR]` | tests: cargo test |
| `scripts/narness-rust-invariants.sh [DIR]` | invariants: ban unwrap/expect/panic!/unsafe without comment |
| `scripts/narness-rust-test-discipline.sh [DIR]` | test discipline: a changed .rs must have a test |

## References (harness design)

The harness design behind each validation script — how to sink a constraint and how to feed failures back to the LLM:

| Doc | Topic |
|---|---|
| `references/fmt-harness.md` | format harness: single-responsibility gate design for rustfmt / `cargo fmt --check` |
| `references/lint-harness.md` | lint harness: how clippy `-D warnings` sinks to L5 `#![forbid]` |
| `references/test-harness.md` | test harness: cargo test + test discipline + layered coverage triggering |

## Test discipline

- Write tests before the implementation
- A changed .rs under src/ must have a corresponding test file
- Run narness-rust-fmt.sh / narness-rust-clippy.sh / narness-rust-test.sh as needed before committing

## Common anti-patterns and their hard constraints

| Anti-pattern | Hard constraint |
|---|---|
| unwrap() everywhere | clippy::unwrap_used + narness-rust-invariants.sh |
| bare panic! | clippy::panic + thiserror/anyhow |
| forgetting tests | narness-rust-test-discipline.sh + hook |
| format drift | cargo fmt --check gate |
