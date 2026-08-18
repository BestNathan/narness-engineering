---
name: narness-git
description: "Guide to mounting harness checkpoints on git hooks — pre-commit, pre-push, commit-msg — to block bad code from entering git history. Use when wiring narness validation scripts into git's commit/push lifecycle, or when a constraint must be enforced at the version-control layer rather than only at edit time."
---

# Narness Git — the version-control layer of the harness

Sink constraints from "the agent's goodwill at edit time" to "git's deterministic block at commit/push time".

## Core idea

Edit-time hooks (Claude Code / Codex) and git hooks are two *different* surfaces, and the difference is the whole point:

| Surface | Runs | Power | Failure effect |
|---|---|---|---|
| Claude Code / Codex hook | after each edit | **feed back** | exit `2` injects stderr into the agent's context |
| git hook | at commit / push | **block** | non-zero exit stops the commit; output goes to the committer |

A git hook never feeds anything back to an LLM — it only blocks. That is not a weakness; it is the layer's job. Git hooks are the *backstop*: even if the agent ignores every after-edit warning, bad code still never enters git history, because git — not the agent — refuses to accept it.

## The constraint ladder (git mapping)

| Level | Means | Strength |
|---|---|---|
| L0 Prompts | verbal/doc requirements | weakest |
| L1 Project conventions | CLAUDE.md | weak |
| L2 Skill | this skill | weak-medium |
| L3 Edit-time hook | Claude Code / Codex PostToolUse | medium-strong — feeds back |
| L4 git hook | pre-commit / pre-push / commit-msg | strong — deterministic block |
| L5 Server-side hook | pre-receive on the remote | strongest — cannot be bypassed |

## When to use this skill

- When wiring narness validation scripts into git's commit/push lifecycle
- When a rule keeps failing at edit time and needs a commit-time backstop
- When a commit/push-level checkpoint (message format, full tests, coverage) has no edit-time equivalent

## Checkpoint → hook point mapping

Each checkpoint mounts on the earliest git hook that can still enforce it — cheap checks at `pre-commit`, heavy checks at `pre-push`:

| Checkpoint | Hook point | Script mounted | Why there |
|---|---|---|---|
| Format | pre-commit | `narness-rust-fmt.sh` | cheapest; catch drift before it is committed |
| Lint | pre-commit | `narness-rust-clippy.sh --scope=changed` | fast; `-D warnings` on the changed crates only |
| Invariants | pre-commit | `narness-rust-invariants.sh` | grep scan, fast |
| Commit-message format | commit-msg | `narness-git-commit-msg.sh` | the message, not the code |
| Unit tests | pre-push | `narness-rust-test-unit.sh --scope=changed` | changed crates only; the full suite is CI's job |
| Full tests + coverage | CI | `test-unit --scope=full --coverage` + `test-integration --scope=full --coverage` | whole workspace, thresholds enforced |
| e2e | CI | `narness-rust-test-e2e.sh` | always full; dep-heavy scenarios |
| Dependency audit | pre-push / CI | `cargo audit` | lockfile, slow tier |

**Changed vs full scope.** Lint and unit/integration test run *changed-scope* at the client-side hooks (fast, only the crates touched since the last push) and *full-scope* in CI (the place allowed to run long). e2e is always full — it has no changed form. The `--scope=changed`/`--scope=full` and `--coverage` flags are what let the same single-responsibility script serve both; the thin hooks just pass the right flag for their moment.

The thin git-hook entrypoints (`githooks/pre-commit`, `commit-msg`, `pre-push`) hold no validation logic — they only resolve the repo and delegate to these single-responsibility scripts, exactly as `post-edit-gate.sh` does for the edit-time hook.

## Install

```bash
bash plugins/narness-git/scripts/narness-git-install.sh
```

This copies the three thin hooks into the repo's `.githooks/` and runs `git config core.hooksPath .githooks`, so the hooks are checked in, reviewable, and shared by every clone — not lost in the untracked `.git/hooks/`.

## The bypass caveat

`git commit --no-verify` (and `--no-verify` on push) skips every client-side hook. A git hook is a *constraint*, not a *law of physics* — the agent can hop over it. The unbypassable backstop is a **server-side `pre-receive`** hook or CI on the remote, which the agent cannot skip. Layer client-side hooks for speed, server-side/CI for certainty.

## Common anti-patterns and their hard constraints

| Anti-pattern | Hard constraint |
|---|---|
| "the agent will remember to format before committing" | pre-commit → `narness-rust-fmt.sh` |
| WIP / unformatted commit messages | commit-msg → `narness-git-commit-msg.sh` |
| pushing broken or untested code | pre-push → `narness-rust-test-unit.sh --scope=changed` |
| editing `.git/hooks/` directly (lost on clone) | `narness-git-install.sh` → `core.hooksPath .githooks` |
| treating a git hook as unbypassable | server-side `pre-receive` or CI |

## Reference

`references/git-hook-layering.md` — the full layering model (edit → commit → push → CI), the block-vs-feedback contract, `core.hooksPath` sharing, the pre-commit framework alternative, and the server-side backstop.
