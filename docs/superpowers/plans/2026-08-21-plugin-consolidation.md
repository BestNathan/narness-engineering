# Plugin Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse `plugins/narness-rust/`, `plugins/narness-git/`, `docs/theory/`, and `docs/reference/` into a single `plugins/narness/` plugin with one `narness` skill whose `SKILL.md` is the entry point and whose flat `references/` holds all 14 supporting files.

**Architecture:** Move files with `git mv` (preserves history), fix every `plugins/narness-rust/` / `plugins/narness-git/` path reference to `plugins/narness/`, rewrite `SKILL.md` as the single design-philosophy entry point, merge the two duplicate-topic pairs (`git-hooks`, `rust-test`) into single files, then delete the emptied source trees and verify no stale path remains.

**Tech Stack:** git (mv/status/grep), bash (verification), markdown (SKILL.md + references). No code compiles or runs; every task's "test" is a `grep`/`find`/`git status` assertion.

**Spec:** `docs/superpowers/specs/2026-08-21-plugin-consolidation-design.md`

---

## File structure (post-move)

```
plugins/narness/
  .claude-plugin/plugin.json          # name "narness" (rewritten)
  hooks/hooks.json                     # moved verbatim
  hooks/scripts/post-edit-gate.sh      # moved verbatim
  scripts/                             # 12 files, moved verbatim (names keep -rust-/-git-)
  githooks/                            # pre-commit, commit-msg, pre-push (moved; paths edited)
  config/                              # 10 files, moved verbatim (ci.yml/e2e.yml/pre-commit paths edited)
  skills/narness/
    SKILL.md                           # rewritten
    references/                        # 14 flat files
```

Move map (all via `git mv`):

- `plugins/narness-rust/hooks/hooks.json` → `plugins/narness/hooks/hooks.json`
- `plugins/narness-rust/hooks/scripts/post-edit-gate.sh` → `plugins/narness/hooks/scripts/post-edit-gate.sh`
- `plugins/narness-rust/scripts/*.sh` (10 files) → `plugins/narness/scripts/*.sh`
- `plugins/narness-git/scripts/narness-git-commit-msg.sh` → `plugins/narness/scripts/narness-git-commit-msg.sh`
- `plugins/narness-git/scripts/narness-git-install.sh` → `plugins/narness/scripts/narness-git-install.sh`
- `plugins/narness-rust/config/*` (10 files) → `plugins/narness/config/*`
- `plugins/narness-git/githooks/*` (3 files) → `plugins/narness/githooks/*`
- `docs/theory/*.md` (7 files) → `plugins/narness/skills/narness/references/*.md`
- `docs/reference/claude-code-hooks.md` → `plugins/narness/skills/narness/references/claude-code-hooks.md`
- `docs/reference/codex-hooks.md` → `plugins/narness/skills/narness/references/codex-hooks.md`
- `plugins/narness-rust/skills/narness-rust/references/fmt-harness.md` → `.../references/rust-fmt.md`
- `plugins/narness-rust/skills/narness-rust/references/lint-harness.md` → `.../references/rust-lint.md`
- `plugins/narness-rust/skills/narness-rust/references/tool-config.md` → `.../references/rust-tool-config.md`

Merged (two source files → one target, done in Tasks 5–6):

- `git-hooks.md` ← `plugins/narness-git/skills/narness-git/references/git-hook-layering.md` + `docs/reference/git-hooks.md`
- `rust-test.md` ← `plugins/narness-rust/skills/narness-rust/references/test-harness.md` + `docs/reference/rust-test-harness.md`

Deleted (not moved): `plugins/narness-rust/.claude-plugin/plugin.json`, `plugins/narness-git/.claude-plugin/plugin.json`, both old `SKILL.md` files.

---

## Task 1: Scaffold the plugin dir and move the machinery (scripts, hooks, githooks, config)

**Files:** create `plugins/narness/`, then `git mv` everything that moves verbatim.

- [ ] **Step 1: Create the target directory tree**

```bash
mkdir -p plugins/narness/hooks/scripts \
         plugins/narness/scripts \
         plugins/narness/githooks \
         plugins/narness/config \
         plugins/narness/skills/narness/references
```

- [ ] **Step 2: Move the hook layer**

```bash
git mv plugins/narness-rust/hooks/hooks.json plugins/narness/hooks/hooks.json
git mv plugins/narness-rust/hooks/scripts/post-edit-gate.sh plugins/narness/hooks/scripts/post-edit-gate.sh
```

- [ ] **Step 3: Move all scripts**

```bash
for s in fmt check clippy test-unit test-integration test-e2e test invariants test-discipline changed-packages; do
  git mv "plugins/narness-rust/scripts/narness-rust-$s.sh" "plugins/narness/scripts/narness-rust-$s.sh"
done
git mv plugins/narness-git/scripts/narness-git-commit-msg.sh plugins/narness/scripts/narness-git-commit-msg.sh
git mv plugins/narness-git/scripts/narness-git-install.sh plugins/narness/scripts/narness-git-install.sh
```

- [ ] **Step 4: Move githooks**

```bash
git mv plugins/narness-git/githooks/pre-commit plugins/narness/githooks/pre-commit
git mv plugins/narness-git/githooks/commit-msg plugins/narness/githooks/commit-msg
git mv plugins/narness-git/githooks/pre-push plugins/narness/githooks/pre-push
```

- [ ] **Step 5: Move config templates**

```bash
for f in ci.yml clippy.toml deny.toml e2e.yml editorconfig nextest.toml pre-commit-config.yaml rust-toolchain.toml rustfmt.toml strict-lints.rs; do
  git mv "plugins/narness-rust/config/$f" "plugins/narness/config/$f"
done
```

- [ ] **Step 6: Verify the tree**

```bash
find plugins/narness -type f | sort
```

Expected: exactly 27 files — `hooks/hooks.json` (1) + `hooks/scripts/post-edit-gate.sh` (1) + `scripts/*.sh` (12) + `githooks/*` (3) + `config/*` (10). Confirm nothing remains under `plugins/narness-rust/scripts`, `plugins/narness-rust/hooks`, `plugins/narness-rust/config`, `plugins/narness-git/scripts`, or `plugins/narness-git/githooks`.

- [ ] **Step 7: Commit**

```bash
git add -A plugins/narness
git commit -m "refactor(plugins): move narness-rust + narness-git machinery into single narness plugin"
```

---

## Task 2: Move and rename the reference files

**Files:** move `docs/theory/*` (7) and `docs/reference/{claude-code-hooks,codex-hooks}.md`, and rename the three rust skill references.

- [ ] **Step 1: Move theory docs (names unchanged)**

```bash
for f in constraint-ladder harness-checkpoints tool-checkpoints command-interception decision-guide long-running-correctness why-not-prompts; do
  git mv "docs/theory/$f.md" "plugins/narness/skills/narness/references/$f.md"
done
```

- [ ] **Step 2: Move the two platform references (names unchanged)**

```bash
git mv docs/reference/claude-code-hooks.md plugins/narness/skills/narness/references/claude-code-hooks.md
git mv docs/reference/codex-hooks.md plugins/narness/skills/narness/references/codex-hooks.md
```

- [ ] **Step 3: Rename the three rust tool references**

```bash
git mv plugins/narness-rust/skills/narness-rust/references/fmt-harness.md   plugins/narness/skills/narness/references/rust-fmt.md
git mv plugins/narness-rust/skills/narness-rust/references/lint-harness.md  plugins/narness/skills/narness/references/rust-lint.md
git mv plugins/narness-rust/skills/narness-rust/references/tool-config.md   plugins/narness/skills/narness/references/rust-tool-config.md
```

- [ ] **Step 4: Verify**

```bash
ls plugins/narness/skills/narness/references/
```

Expected: 12 files (7 theory + claude-code-hooks + codex-hooks + rust-fmt + rust-lint + rust-tool-config). The two merge targets (`git-hooks.md`, `rust-test.md`) are created in Tasks 5–6.

- [ ] **Step 5: Commit**

```bash
git add -A plugins/narness/skills/narness/references
git commit -m "refactor(skill): move theory + platform + rust references into narness skill"
```

---

## Task 3: Fix path references in the moved machinery

Every occurrence of `plugins/narness-rust/` or `plugins/narness-git/` in the moved *scripts/config/githooks* must become `plugins/narness/`. Script *names* (`narness-rust-fmt.sh`) are left untouched.

**Files:** `plugins/narness/githooks/pre-commit`, `pre-push`, `commit-msg`, `plugins/narness/scripts/narness-git-install.sh`, `plugins/narness/config/ci.yml`, `e2e.yml`, `pre-commit-config.yaml`.

- [ ] **Step 1: githooks — update the two script-dir fallbacks**

In `plugins/narness/githooks/pre-commit` and `pre-push`, change:

```
narness="${NARNESS_RUST_SCRIPTS:-$root/plugins/narness-rust/scripts}"
```
to
```
narness="${NARNESS_RUST_SCRIPTS:-$root/plugins/narness/scripts}"
```

In `plugins/narness/githooks/commit-msg`, change:

```
narness="${NARNESS_GIT_SCRIPTS:-$root/plugins/narness-git/scripts}"
```
to
```
narness="${NARNESS_GIT_SCRIPTS:-$root/plugins/narness/scripts}"
```

- [ ] **Step 2: install script — update the githooks source dir**

In `plugins/narness/scripts/narness-git-install.sh`, change:

```
SOURCE_GITHOOKS="${NARNESS_GIT_GITHOOKS:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/githooks}"
```
to (no textual change needed — `..` from `scripts/` already resolves to `plugins/narness/githooks`). Verify with `grep -n 'SOURCE_GITHOOKS' plugins/narness/scripts/narness-git-install.sh` that the path computes to `plugins/narness/githooks`, and that no `narness-git/` string remains in the file.

- [ ] **Step 3: config templates — update CI/e2e/pre-commit run paths**

In `plugins/narness/config/ci.yml` (5 lines), `plugins/narness/config/e2e.yml` (1 line), and `plugins/narness/config/pre-commit-config.yaml` (4 lines), replace every `plugins/narness-rust/scripts/` with `plugins/narness/scripts/`.

Use a single sed across the three files:

```bash
sed -i '' 's#plugins/narness-rust/scripts/#plugins/narness/scripts/#g' \
  plugins/narness/config/ci.yml \
  plugins/narness/config/e2e.yml \
  plugins/narness/config/pre-commit-config.yaml
```

- [ ] **Step 4: Verify no stale path remains in the machinery**

```bash
grep -rn 'plugins/narness-rust/\|plugins/narness-git/' plugins/narness/hooks plugins/narness/scripts plugins/narness/githooks plugins/narness/config || echo "CLEAN"
```

Expected: `CLEAN`.

- [ ] **Step 5: Commit**

```bash
git add -A plugins/narness
git commit -m "refactor(plugins): point hooks/config at plugins/narness/scripts"
```

---

## Task 4: Rewrite SKILL.md as the single entry point

**Files:**
- Create: `plugins/narness/skills/narness/SKILL.md`
- Delete (via this task's commit, after content absorbed): `plugins/narness-rust/skills/narness-rust/SKILL.md`, `plugins/narness-git/skills/narness-git/SKILL.md`

- [ ] **Step 1: Write the full SKILL.md**

```markdown
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
```

- [ ] **Step 2: Delete the two superseded SKILL.md files**

```bash
git rm plugins/narness-rust/skills/narness-rust/SKILL.md
git rm plugins/narness-git/skills/narness-git/SKILL.md
```

- [ ] **Step 3: Verify frontmatter name and links**

```bash
head -3 plugins/narness/skills/narness/SKILL.md
```

Expected: `name: narness`.

- [ ] **Step 4: Commit**

```bash
git add -A plugins/narness/skills/narness/SKILL.md plugins/narness-rust plugins/narness-git
git commit -m "feat(skill): single narness SKILL.md as design-philosophy entry point"
```

---

## Task 5: Merge git-hooks.md

**Files:**
- Create: `plugins/narness/skills/narness/references/git-hooks.md`
- Delete: `plugins/narness-git/skills/narness-git/references/git-hook-layering.md` (already consumed), `docs/reference/git-hooks.md` (already consumed)

**Assembly:** Use `git-hook-layering.md` as the base (it is the richer, current doc). Renumber its sections to accommodate the fold-ins from `docs/reference/git-hooks.md`. Final section order:

1. **Where git hooks sit** — `git-hook-layering.md` §1 (unchanged).
2. **Client-side vs server-side, and the common client hooks** — NEW: the table from `docs/reference/git-hooks.md` §2 (pre-commit / commit-msg / pre-push / post-commit / pre-rebase / post-merge).
3. **The block-vs-feedback contract** — `git-hook-layering.md` §2 (unchanged).
4. **The thin entrypoint pattern** — `git-hook-layering.md` §3, with the code sample's `$root/plugins/narness-rust/scripts` → `$root/plugins/narness/scripts`.
5. **Checkpoint placement** — `git-hook-layering.md` §4 (unchanged).
6. **Sharing hooks: core.hooksPath** — `git-hook-layering.md` §5, plus fold in the "write `.git/hooks/` directly" and "pre-commit framework" methods from `docs/reference/git-hooks.md` §3.1/§3.3 (the framework yaml's `entry:` paths get `plugins/narness-rust/scripts` → `plugins/narness/scripts`).
7. **The bypass and the backstop** — `git-hook-layering.md` §6 (unchanged).
8. **Alternatives and adjacent tools** — `git-hook-layering.md` §7 (unchanged).
9. **Platform caveat** — `git-hook-layering.md` §8 (unchanged).

- [ ] **Step 1: Compose the file per the section map above**

Copy `git-hook-layering.md` into the new path, then apply the §2 insert, the §6 fold-ins, and the path substitutions. The unique fold-in content from `docs/reference/git-hooks.md` §2 (the client hooks table):

```markdown
## 2. Client-side vs server-side, and the common client hooks

Git runs same-named scripts around specific actions. **Client-side** hooks fire in the local repo (commit, push); **server-side** hooks fire on the remote (pre-receive, update, post-receive). Harness scripts mostly mount on client-side hooks — the goal is "intercept bad code before the agent commits it".

| Hook | Timing | Use | Non-zero exit effect |
|---|---|---|---|
| `pre-commit` | before `git commit` | format, lint, fast tests | block the commit |
| `commit-msg` | after editing the message | validate message format | block the commit |
| `pre-push` | before `git push` | full tests, heavier gates | block the push |
| `post-commit` | after the commit | notification, logging | doesn't block |
| `pre-rebase` | before `git rebase` | block dangerous rebases | block |
| `post-merge` / `post-checkout` | after merging/switching | trigger dependency updates | doesn't block |
```

And the `pre-commit` framework yaml (fold into §6), with paths already fixed:

```yaml
repos:
  - repo: local
    hooks:
      - id: narness-rust-fmt
        name: cargo fmt --check
        entry: bash plugins/narness/scripts/narness-rust-fmt.sh
        language: system
        files: '\.rs$'
```

- [ ] **Step 2: Fix every remaining path/name in the new file**

```bash
sed -i '' 's#plugins/narness-rust/scripts#plugins/narness/scripts#g; s#vendor narness-rust at#vendor narness at#g' \
  plugins/narness/skills/narness/references/git-hooks.md
grep -n 'narness-rust\|narness-git' plugins/narness/skills/narness/references/git-hooks.md
```

Expected: only intentional script *names* (`narness-rust-fmt.sh`, `narness-rust-clippy.sh`, `narness-rust-test-unit.sh`, `narness-rust-test-e2e.sh`, `narness-git-install.sh`) remain — no `plugins/narness-rust/` path.

- [ ] **Step 3: Delete the two consumed sources**

```bash
git rm plugins/narness-git/skills/narness-git/references/git-hook-layering.md
git rm docs/reference/git-hooks.md
```

- [ ] **Step 4: Commit**

```bash
git add -A plugins/narness/skills/narness/references/git-hooks.md
git commit -m "docs(skill): merge git-hooks + git-hook-layering into one reference"
```

---

## Task 6: Merge rust-test.md

**Files:**
- Create: `plugins/narness/skills/narness/references/rust-test.md`
- Delete: `plugins/narness-rust/skills/narness-rust/references/test-harness.md`, `docs/reference/rust-test-harness.md`

**Assembly:** Use `test-harness.md` as the base (it owns the three-tier design). Fold in the nextest and llvm-cov tool detail from `rust-test-harness.md`, which is the one thing `test-harness.md` defers on. Final section order:

1. **Positioning** — `test-harness.md` §1 (unchanged).
2. **The three-tier test design** — `test-harness.md` §2 (unchanged).
3. **What each tier covers (and why e2e is 补位)** — `test-harness.md` §3 (unchanged).
4. **Tools: cargo test / nextest / llvm-cov** — `test-harness.md` §4, with the deferred sentence "For the full nextest / llvm-cov design see `docs/reference/rust-test-harness.md`" **removed** (it is now this file).
5. **The nextest runner** — NEW: `rust-test-harness.md` §2 (why nextest, install/usage, `nextest.toml`, the single-responsibility wrapper).
6. **Coverage with llvm-cov** — NEW: `rust-test-harness.md` §3 (why coverage, install/usage, per-tier thresholds, secondary axes).
7. **Design: one single-responsibility script per tier** — `test-harness.md` §5 (unchanged).
8. **Coverage thresholds** — `test-harness.md` §6 (unchanged).
9. **Test efficiency: why tiering is fast** — `test-harness.md` §7 (unchanged).
10. **Layered triggering** — `test-harness.md` §8, with the e2e yaml's `bash plugins/narness-rust/scripts/narness-rust-test-e2e.sh` → `bash plugins/narness/scripts/narness-rust-test-e2e.sh`.
11. **Test discipline** — `test-harness.md` §9 (unchanged).
12. **Feeding failures back to the LLM** — `test-harness.md` §10 (unchanged).
13. **Sink path** — `test-harness.md` §11 (unchanged).
14. **Script mapping** — `test-harness.md` §12 (unchanged).

- [ ] **Step 1: Compose the file per the section map above**

Copy `test-harness.md` into the new path, remove the deferred sentence (the §4 line 53 sentence), insert §5–6 from `rust-test-harness.md` (its §2 nextest and §3 llvm-cov, renumbered), and fix the e2e yaml path.

- [ ] **Step 2: Fix the one path in the new file**

```bash
sed -i '' 's#plugins/narness-rust/scripts#plugins/narness/scripts#g' \
  plugins/narness/skills/narness/references/rust-test.md
grep -n 'docs/reference\|plugins/narness-rust/' plugins/narness/skills/narness/references/rust-test.md || echo "CLEAN"
```

Expected: `CLEAN` (no leftover cross-doc reference or stale path).

- [ ] **Step 3: Delete the two consumed sources**

```bash
git rm plugins/narness-rust/skills/narness-rust/references/test-harness.md
git rm docs/reference/rust-test-harness.md
```

- [ ] **Step 4: Commit**

```bash
git add -A plugins/narness/skills/narness/references/rust-test.md
git commit -m "docs(skill): merge test-harness + rust-test-harness into rust-test.md"
```

---

## Task 7: Fix remaining cross-links in the moved references

Three references still point at old filenames or a stale value. Fix them.

- [ ] **Step 1: rust-tool-config.md — fix the two cross-doc links and the lint link**

In `plugins/narness/skills/narness/references/rust-tool-config.md`:

- `docs/reference/rust-test-harness.md` → `rust-test.md` (two places: §5 llvm-cov and nextest bullets)
- `docs/reference/git-hooks.md` → `git-hooks.md` (one place, §5 EditorConfig/pre-commit/CI bullet)
- `[lint-harness.md](lint-harness.md)` → `[rust-lint.md](rust-lint.md)` (one place, §1)
- `[test-harness.md](test-harness.md)` → `[rust-test.md](rust-test.md)` (one place, §5)

```bash
sed -i '' \
  -e 's#docs/reference/rust-test-harness.md#rust-test.md#g' \
  -e 's#docs/reference/git-hooks.md#git-hooks.md#g' \
  -e 's#lint-harness.md#rust-lint.md#g' \
  -e 's#\[test-harness.md\](test-harness.md)#[rust-test.md](rust-test.md)#g' \
  plugins/narness/skills/narness/references/rust-tool-config.md
```

- [ ] **Step 2: rust-fmt.md — fix the lint link**

In `plugins/narness/skills/narness/references/rust-fmt.md`:

- `[lint-harness.md](lint-harness.md)` → `[rust-lint.md](rust-lint.md)` (one place, §12)

```bash
sed -i '' 's#lint-harness.md#rust-lint.md#g' \
  plugins/narness/skills/narness/references/rust-fmt.md
```

- [ ] **Step 3: rust-lint.md — fix the stale msrv example**

In `plugins/narness/skills/narness/references/rust-lint.md` §8, the `clippy.toml` example shows `msrv = "1.75"`, contradicting the shipped `config/clippy.toml` (`msrv = "1.85"`, the edition-2024 floor). Change `msrv = "1.75"` → `msrv = "1.85"`. Leave §9's "Rust 1.75" (a separate fact: the async-fn-in-trait stabilization version) untouched.

```bash
sed -i '' 's/msrv = "1.75"/msrv = "1.85"/' \
  plugins/narness/skills/narness/references/rust-lint.md
```

- [ ] **Step 4: Verify**

```bash
grep -rn 'docs/reference\|docs/theory\|lint-harness.md\|test-harness.md\|fmt-harness.md' plugins/narness/skills/narness/references || echo "CLEAN"
```

Expected: `CLEAN`.

- [ ] **Step 5: Commit**

```bash
git add -A plugins/narness/skills/narness/references
git commit -m "docs(skill): fix cross-links and stale msrv after consolidation"
```

---

## Task 8: Update marketplace.json, plugin.json, and CLAUDE.md

- [ ] **Step 1: Write the single plugin manifest**

Create `plugins/narness/.claude-plugin/plugin.json`:

```json
{
  "name": "narness",
  "description": "Harness engineering: constrain AI agents with code, hooks and scripts instead of prompts — skills, validation scripts, git hooks and per-tool configs",
  "version": "0.1.0",
  "author": { "name": "narness" },
  "license": "MIT",
  "keywords": ["harness", "hooks", "rust", "clippy", "git", "engineering"]
}
```

- [ ] **Step 2: Update marketplace.json to a single entry**

Replace the `plugins` array in `.claude-plugin/marketplace.json` with:

```json
  "plugins": [
    {
      "name": "narness",
      "description": "Harness engineering — skills, hooks and validation scripts",
      "version": "0.1.0",
      "source": "./plugins/narness",
      "author": { "name": "narness" }
    }
  ]
```

- [ ] **Step 3: Update CLAUDE.md §Structure and §1 script-naming prose**

In `CLAUDE.md`:

- Replace the two `plugins/narness-rust/` and `plugins/narness-git/` bullets and the `docs/theory/` and `docs/reference/` bullets with:

```markdown
- `plugins/narness/` — the harness-engineering plugin (skill + PostToolUse hook + `narness-rust-*` / `narness-git-*` scripts + git hooks + per-tool config templates)
- `cli/` — the narness environment checker (npm package)
- `.claude-plugin/marketplace.json` — the outer marketplace
```

- In §1, change "The Rust plugin ships" to "The plugin ships" (script names stay).

- [ ] **Step 4: Verify**

```bash
grep -rn 'plugins/narness-rust\|plugins/narness-git\|docs/theory\|docs/reference' .claude-plugin/marketplace.json plugins/narness/.claude-plugin/plugin.json CLAUDE.md || echo "CLEAN"
```

Expected: `CLEAN`.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/marketplace.json plugins/narness/.claude-plugin/plugin.json CLAUDE.md
git commit -m "docs: single narness plugin in marketplace + CLAUDE.md structure"
```

---

## Task 9: Delete emptied source trees and run the full verification

- [ ] **Step 1: Remove the last tracked files and confirm the source dirs are empty**

By this point every file in the four source trees has been moved (`git mv`) or consumed (`git rm`) in Tasks 1–6. The only tracked files left are the two old plugin manifests:

```bash
git rm plugins/narness-rust/.claude-plugin/plugin.json plugins/narness-git/.claude-plugin/plugin.json
```

Then confirm nothing else survived (the safety net — any unexpected file means the move map missed something):

```bash
find plugins/narness-rust plugins/narness-git docs/theory docs/reference -type f 2>/dev/null && echo "UNEXPECTED FILES REMAIN" || echo "source dirs empty"
```

Expected: `source dirs empty`. The empty directories vanish from git on their own (git tracks files, not dirs).

- [ ] **Step 2: Full stale-path scan**

```bash
grep -rn 'plugins/narness-rust\|plugins/narness-git\|docs/theory\|docs/reference' plugins docs cli .claude-plugin --include='*.md' --include='*.sh' --include='*.json' --include='*.yml' --include='*.yaml' --include='pre-commit' --include='pre-push' --include='commit-msg' 2>/dev/null | grep -v '^docs/superpowers' || echo "CLEAN"
```

Expected: `CLEAN` (nothing outside `docs/superpowers/`, whose historical plans/specs are allowed to mention the old layout).

- [ ] **Step 3: Structure assertion**

```bash
find plugins/narness -type f | sort
```

Expected: `.claude-plugin/plugin.json`, `hooks/hooks.json`, `hooks/scripts/post-edit-gate.sh`, 12 `scripts/*.sh`, 3 `githooks/*`, 10 `config/*`, `skills/narness/SKILL.md`, 14 `skills/narness/references/*.md`.

- [ ] **Step 4: Link-resolution spot check**

```bash
cd plugins/narness/skills/narness && for f in $(grep -o 'references/[a-z-]*\.md' SKILL.md | sort -u); do test -f "$f" || echo "BROKEN: $f"; done; echo "done"
```

Expected: `done` with no `BROKEN:` lines.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(plugins): remove emptied narness-rust/narness-git/docs trees"
```

---

## Self-review notes (for the implementer)

- Script *names* (`narness-rust-fmt.sh`, `narness-git-commit-msg.sh`, …) are **intentional** and must never be "cleaned up" by a path sed — only `plugins/narness-rust/` (with trailing slash and `plugins/` prefix) and `plugins/narness-git/` are path references.
- `docs/superpowers/` is out of scope; its historical docs may reference the old layout and that is fine.
- No task touches script bodies, hook bodies, or config-template *content* except the explicit path substitutions in Task 3 and the single `msrv` example fix in Task 7.
