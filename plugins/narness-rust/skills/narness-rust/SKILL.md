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

## Toolchain pinning

Every `narness-rust-*.sh` gate is only a *hard* constraint if it is **deterministic**: the same code must produce the same verdict on every machine — the developer's, CI's, and the agent's. The most common way a gate "lies" is toolchain version drift: local `rustfmt` / `clippy` disagrees with CI's, so a check passes here and fails there (or both pass but produce different output).

Pin the toolchain in the repo with `rust-toolchain.toml`:

```toml
[toolchain]
channel = "1.89.0"
profile = "minimal"
components = ["rustfmt", "clippy"]
```

Rules:

- Pin a **specific version** (a stable release, or a dated nightly like `nightly-2026-08-01`) — never a rolling "latest", which changes over time and reintroduces drift.
- List every component the scripts need (`rustfmt`, `clippy`) so each environment installs them for the pinned channel.
- Keep tool config **stable-only** unless the whole team pins the same dated nightly: nightly-only options silently no-op on stable, making the gate nondeterministic.

This is the shared prerequisite behind all three harness references; each reference notes only what is specific to its own tool.

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
| `scripts/narness-rust-fmt.sh [DIR]` | format check: cargo fmt --all -- --check |
| `scripts/narness-rust-check.sh [DIR]` | compile check: cargo check |
| `scripts/narness-rust-clippy.sh [DIR]` | lint check: cargo clippy -D warnings |
| `scripts/narness-rust-test-unit.sh [DIR]` | unit tests + ≥95% coverage (pre-push) |
| `scripts/narness-rust-test-integration.sh [DIR]` | integration tests + ≥80% coverage (CI) |
| `scripts/narness-rust-test-e2e.sh [DIR]` | e2e scenarios, no coverage (CI) |
| `scripts/narness-rust-test.sh [DIR]` | full suite: cargo test (dependency-free) |
| `scripts/narness-rust-invariants.sh [DIR]` | invariants: ban unwrap/expect/panic!/unsafe without comment |
| `scripts/narness-rust-test-discipline.sh [DIR]` | test discipline: a changed .rs must have a test |

## References (harness design)

The harness design behind each validation script — how to sink a constraint and how to feed failures back to the LLM:

| Doc | Topic |
|---|---|
| `references/fmt-harness.md` | format harness: the `cargo fmt --all -- --check` gate — config-as-code, stable/nightly options, escape hatches, macro blind spots, editor vs gate |
| `references/lint-harness.md` | lint harness: rule design, three strictness tiers (general/medium/strictest), `clippy.toml` vs lint levels, custom rules (ban async-trait) |
| `references/test-harness.md` | test harness: three tiers (unit 95% / integration 80% / e2e 补位) + test discipline + layered triggering |

## Test discipline

- Write tests before the implementation
- A changed .rs under src/ must have a corresponding test file
- Unit tests (95% coverage) gate every push; integration (80%) and e2e (补位) run in CI
- Run narness-rust-fmt.sh / narness-rust-clippy.sh / narness-rust-test-unit.sh as needed before pushing

## Common anti-patterns and their hard constraints

| Anti-pattern | Hard constraint |
|---|---|
| unwrap() everywhere | clippy::unwrap_used + narness-rust-invariants.sh |
| bare panic! | clippy::panic + thiserror/anyhow |
| forgetting tests | narness-rust-test-discipline.sh + hook |
| format drift | cargo fmt --all -- --check gate |
