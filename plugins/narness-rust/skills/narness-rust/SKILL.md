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
- List every component the scripts need (`rustfmt`, `clippy`, `llvm-tools-preview`) so each environment installs them for the pinned channel — `llvm-tools-preview` is easy to miss but `cargo llvm-cov` (the coverage gate) requires it.
- Keep tool config **stable-only**: nightly-only options silently no-op on stable, making the gate nondeterministic. The shipped `config/` defaults to a **pinned stable** channel — strictness comes from the code-quality rules (`#![forbid]` restriction lints, `-D warnings`, `deny.toml`), which are all stable.

This is the shared prerequisite behind all three harness references; each reference notes only what is specific to its own tool.

## Recommended tool configs

Every harness tool has one config surface — a file it auto-reads, or a flag the script already passes. The `config/` directory ships copyable templates for each (rustfmt.toml, clippy.toml, strict-lints.rs, nextest.toml, deny.toml, rust-toolchain.toml, .editorconfig, pre-commit, CI), and the consolidated map lives in [references/tool-config.md](references/tool-config.md).

The configs ship in **strict mode** — the strongest *code-quality* control, not the newest toolchain: a pinned stable channel (stable operation), `#![forbid]` levels in `config/strict-lints.rs`, and `deny.toml` with everything denied. The defaults are **not arbitrary** — they encode the exact numbers the `narness-rust-*.sh` scripts were written against (coverage ≥95% / ≥80%, `-D warnings`, `--all -- --check`). Copy, then adapt the genuinely project-specific bits (disallowed lists, license allow-list) to your policy.

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
| `scripts/narness-rust-clippy.sh [DIR] [--scope=changed\|full]` | lint check: cargo clippy -D warnings |
| `scripts/narness-rust-test-unit.sh [DIR] [--scope=changed\|full] [--coverage]` | unit tests; `--coverage` = enforce ≥95% |
| `scripts/narness-rust-test-integration.sh [DIR] [--scope=changed\|full] [--coverage]` | integration tests; `--coverage` = enforce ≥80% |
| `scripts/narness-rust-test-e2e.sh [DIR]` | e2e scenarios, always full, no coverage (dedicated optional workflow) |
| `scripts/narness-rust-test.sh [DIR]` | full suite: cargo test --workspace |
| `scripts/narness-rust-invariants.sh [DIR]` | invariants: ban unwrap/expect/panic!/unsafe without comment |
| `scripts/narness-rust-test-discipline.sh [DIR]` | test discipline: a changed .rs must have a test |
| `scripts/narness-rust-changed-packages.sh [DIR]` | helper: emit the packages changed since the last push (backing `--scope=changed`) |

## Changed vs full scope

Lint and test are **scope-aware**: they can run against only the crates you changed, or the whole workspace. Two orthogonal flags control it:

| Flag | Values | Meaning | On |
|---|---|---|---|
| `--scope` | `changed` \| `full` (default `full`) | which crates to operate on | clippy / test-unit / test-integration |
| `--coverage` | present \| absent (default absent) | enforce the coverage threshold via llvm-cov | test-unit (≥95%) / test-integration (≥80%) |

- `--scope=changed` maps every compile-relevant file changed since the last push (committed-ahead + staged + unstaged + untracked) to its owning workspace member, then lints/tests only those crates (`-p <crate>`). The unit of "changed" is the **crate** — Cargo's compilation unit — not the file: change one file in `crates/foo` and the whole `foo` crate is linted/tested.
- `--scope=full` runs `--workspace` across the whole workspace — the CI / long-running form, and the safe default.
- e2e has **no** `--scope` and **no** `--coverage`: e2e is scenario-driven, always full, never line-measured, and runs in a dedicated **optional** workflow (not a merge blocker).
- `--coverage` is opt-in so the push path stays fast (run-only), while CI passes it to enforce the threshold. Default (absent) = run the tests without measuring coverage.

**Fail-safe fallback:** when the changed set can't be determined (no upstream/base) or a workspace-level file changed (`Cargo.lock`, root `Cargo.toml`, `rust-toolchain.toml`), `--scope=changed` silently runs **full** rather than risk skipping a crate that should have been checked.

## References (harness design)

The harness design behind each validation script — how to sink a constraint and how to feed failures back to the LLM:

| Doc | Topic |
|---|---|
| `references/fmt-harness.md` | format harness: the `cargo fmt --all -- --check` gate — config-as-code, stable/nightly options, escape hatches, macro blind spots, editor vs gate |
| `references/lint-harness.md` | lint harness: rule design, three strictness tiers (general/medium/strictest), `clippy.toml` vs lint levels, custom rules (ban async-trait) |
| `references/test-harness.md` | test harness: three tiers (unit 95% / integration 80% / e2e 补位) + test discipline + layered triggering |
| `references/tool-config.md` | recommended config for every harness tool: rustfmt.toml / clippy.toml / nextest.toml / deny.toml / rust-toolchain.toml / .editorconfig / pre-commit / CI |

## Test discipline

- Write tests before the implementation
- A changed .rs under src/ must have a corresponding test file
- pre-push runs unit tests on the changed crates (`--scope=changed`, run-only); CI runs the full unit/integration suites with coverage (`--scope=full --coverage`); e2e (补位) runs in its own dedicated, optional workflow
- Run narness-rust-fmt.sh / narness-rust-clippy.sh / narness-rust-test-unit.sh as needed before pushing

## Common anti-patterns and their hard constraints

| Anti-pattern | Hard constraint |
|---|---|
| unwrap() everywhere | clippy::unwrap_used + narness-rust-invariants.sh |
| bare panic! | clippy::panic + thiserror/anyhow |
| forgetting tests | narness-rust-test-discipline.sh + hook |
| format drift | cargo fmt --all -- --check gate |
