# Narness

Narness is a "research + documentation + Claude Code tooling" project that articulates and puts into practice the idea of **harness engineering**.

## Core idea

When code, hooks, or scripts can constrain an AI agent's behavior, prefer them over prompts. An agent will very likely not follow prompts; scripts and hooks let the agent *discover* that its implementation is wrong and guide it toward correct behavior, thereby guaranteeing correctness on long-running tasks.

The constraint ladder: L0 prompts → L1 project conventions → L2 Skill → L3 Hook → L4 script validation → L5 compile-time. The goal is to sink constraints from L0–L2 down to L3–L5.

## Project conventions (must follow)

1. **Script naming**: every script this project provides starts with `narness-`. The Rust plugin ships `narness-rust-fmt.sh`, `narness-rust-check.sh`, `narness-rust-clippy.sh`, `narness-rust-test.sh`, `narness-rust-invariants.sh`, `narness-rust-test-discipline.sh`.
2. **Single-responsibility scripts**: each validation script does exactly one thing. "Full-gate" god scripts that bundle fmt/lint/test together are forbidden — split each check into its own `narness-rust-*.sh`.
3. **Thin hook entrypoint**: the hook script (`post-edit-gate.sh`) only "judges the trigger condition + delegates to a single-responsibility script"; it does not inline validation logic.
4. **Feed failures back to the LLM**: on failure, scripts must write diagnostics to stderr (a PostToolUse hook exit code 2 injects stderr into the LLM context), so the agent can see its own mistakes and fix them.

## Structure

- `plugins/narness-rust/` — Rust harness-engineering plugin (skill + PostToolUse hook + 6 `narness-rust-*.sh` scripts)
- `docs/theory/` — theory docs (constraint ladder, decision guide, etc.)
- `docs/reference/` — tool-practice references (e.g. the Rust test harness)
- `cli/` — the narness environment checker (npm package)
- `.claude-plugin/marketplace.json` — the outer marketplace

## Initial scope

Rust only, pure theory with no example projects. Later extensions: plugins for other languages (narness-python, etc.), example projects.
