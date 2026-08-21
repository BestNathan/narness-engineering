# Narness

Narness is a "research + documentation + Claude Code tooling" project that articulates and puts into practice the idea of **harness engineering**.

## Core idea

When code, hooks, or scripts can constrain an AI agent's behavior, prefer them over prompts. An agent will very likely not follow prompts; scripts and hooks let the agent *discover* that its implementation is wrong and guide it toward correct behavior, thereby guaranteeing correctness on long-running tasks.

The constraint ladder: L0 prompts → L1 project conventions → L2 Skill → L3 Hook → L4 script validation → L5 compile-time. The goal is to sink constraints from L0–L2 down to L3–L5.

## Project conventions (must follow)

1. **Script naming**: every script this project provides starts with `narness-`. The plugin ships `narness-rust-fmt.sh`, `narness-rust-check.sh`, `narness-rust-clippy.sh`, `narness-rust-test-unit.sh`, `narness-rust-test-integration.sh`, `narness-rust-test-e2e.sh`, `narness-rust-test.sh`, `narness-rust-invariants.sh`, `narness-rust-test-discipline.sh`, plus the `narness-rust-changed-packages.sh` helper (maps changed files → changed crates).
2. **Single-responsibility scripts**: each validation script does exactly one thing. "Full-gate" god scripts that bundle fmt/lint/test together are forbidden — split each check into its own `narness-rust-*.sh`.
3. **Thin hook entrypoint**: the hook script (`post-edit-gate.sh`) only "judges the trigger condition + delegates to a single-responsibility script"; it does not inline validation logic.
4. **Feed failures back to the LLM**: on failure, scripts must write diagnostics to stderr (a PostToolUse hook exit code 2 injects stderr into the LLM context), so the agent can see its own mistakes and fix them.
5. **Develop directly on `main`**: this project commits straight to `main` — no feature branches or pull requests. Commit working changes to `main` as they land.

## Checkpoint taxonomy

A harness is a sequence of checkpoints — each asks one yes/no question and is backed by one single-responsibility script. When you add or extend a check, pick the right checkpoint and follow its script-design rule.

| Checkpoint | Question to answer | Script design |
|---|---|---|
| Format | conforms to the fixed style? | `--check` (gate) vs auto-fix (hook); fix style in config, not prompts |
| Compile / type-check | compiles? | the fastest full check; the after-edit hook's default |
| Lint | written badly (compiles but shouldn't)? | escalate warnings to errors; sink to a source-level forbid |
| Invariants | obeys project rules a linter can't express? | grep scan; only for the linter's gaps, never to duplicate it |
| Test | does the right thing? | full gate; localizable failure output |
| Coverage | tested *enough*? | numeric threshold; feed uncovered lines back |
| Test discipline | changed source has a test? | VCS diff → map to a matching test file |
| Dependency audit | vulnerable deps? | audit the lockfile; slow tier only (pre-commit/CI) |

Every script obeys the same six rules: one script = one checkpoint; a deterministic verdict via exit code (`0` pass / `1` fail / `2` hook-feedback); diagnostics to stderr; failure output states where / why / how-to-fix; a fast form for the hook and a full form for the gate; sink the check to its lowest reachable level (prefer compile-time over script, tool-native over grep).

## Changed vs full scope (增量 vs 全量)

Lint and unit/integration test are scope-aware. `--scope=changed` runs only the crates changed since the last push (the **crate** is the unit of change, not the file); `--scope=full` runs the whole workspace. e2e is always full — it has no changed form. `--coverage` (opt-in) enforces the coverage threshold; without it the tests just run. Client-side git hooks run `--scope=changed` (fast); CI runs `--scope=full --coverage`. When the changed set can't be determined, or a workspace-level file changed (`Cargo.lock`, root `Cargo.toml`, `rust-toolchain.toml`), it fails safe to full — a gate never under-checks.

## Structure

- `plugins/narness/` — the harness-engineering plugin (skill + PostToolUse hook + `narness-rust-*` / `narness-git-*` scripts + git hooks + per-tool config templates)
- `cli/` — the narness environment checker (npm package)
- `.claude-plugin/marketplace.json` — the outer marketplace

## Initial scope

Rust only, pure theory with no example projects. Later extensions: other languages (narness-python, etc.) as references + scripts inside this plugin, example projects.
