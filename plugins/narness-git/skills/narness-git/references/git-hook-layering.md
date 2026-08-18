# Git hook layering — the version-control constraint surface

## 1. Where git hooks sit

A harness is a sequence of checkpoints mounted across moments. Git hooks own the **commit** and **push** moments — the last client-side line before code enters shared history:

```
edit time (CC/Codex hook) → commit time (git pre-commit / commit-msg)
  → push time (git pre-push) → CI / server-side
    feed back                    block                 block              enforce
```

Each step rightward is *harder to bypass* and *coarser/slower to fix*. Mount each checkpoint at the earliest moment whose tool can still enforce it.

## 2. The block-vs-feedback contract

This is the single most important thing to get right about git hooks, because it is the *opposite* of edit-time hooks:

| | Claude Code / Codex hook | git hook |
|---|---|---|
| exit-code meaning | `2` = fail, inject stderr into the agent's context | non-zero = block the commit/push |
| output | stderr → fed back to the LLM | stdout/stderr → shown to the committer only |
| who fixes it | the agent, on its next turn | whoever runs the commit (human or agent), by re-running after fixing |

Consequence: a git hook **cannot teach**. It cannot explain a mistake to the agent mid-task; it can only refuse. So git-hook diagnostics must be *self-contained* — a human or agent reading the blocked commit's output must know where / why / how-to-fix without any surrounding context. The single-responsibility scripts already print `where / why / how-to-fix` to stderr; the git hook just lets that text reach the committer.

## 3. The thin entrypoint pattern

Git hooks follow the same "thin entrypoint" convention as edit-time hooks: judge the trigger, delegate to a single-responsibility script, never inline validation.

```bash
#!/usr/bin/env bash
# .githooks/pre-commit — thin entrypoint, no validation logic
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
narness="${NARNESS_RUST_SCRIPTS:-$root/plugins/narness-rust/scripts}"
bash "$narness/narness-rust-fmt.sh" "$root"
bash "$narness/narness-rust-clippy.sh" "$root"
```

Why `git rev-parse --show-toplevel`: git runs hooks from the top of the working tree, but resolving the root explicitly keeps the path robust under submodules and unusual invocations. The `NARNESS_RUST_SCRIPTS` env override lets a consuming repo vendor narness-rust at a non-default path.

## 4. Checkpoint placement

### pre-commit — the fast gate (runs on every commit)

- Format (`fmt --check`, whole workspace), lint (`clippy -D warnings --scope=changed`), invariants (grep), test discipline (diff → test mapping).
- Must be *fast* — seconds, not minutes. A slow check here makes commits painful and teaches the agent to reach for `--no-verify`.
- Lint runs **changed-scope**: only the crates touched since the last push, so a commit never pays workspace-wide clippy. The whole-workspace lint runs in CI.
- Whole-crate for Rust (`cargo fmt --all`); staged-files-only is a JS/TS optimization (lint-staged / husky), not the Rust default.

### commit-msg — the message gate

- Conventional-commit prefix, no WIP / fixup! / squash! markers, subject ≤ 72 chars.
- The one git-native checkpoint: it checks *the commit*, not *the code*. It has no edit-time equivalent, so it lives only here.

### pre-push — the changed-scope gate (runs on every push)

- Changed-scope unit tests (`narness-rust-test-unit.sh --scope=changed`, run-only), dependency audit.
- The fast checks already passed at pre-commit; pre-push adds only the changed crates' unit tests, so the push path stays seconds even in a large workspace.
- The full unit/integration suites with coverage, plus e2e, run in CI — the place allowed to run long. Client-side hooks stay changed-scope; CI stays full-scope.

### CI — the full-scope gate

- `clippy --scope=full`, `test-unit --scope=full --coverage`, `test-integration --scope=full --coverage`, `test-e2e` (always full), as separate jobs.
- This is the only place the coverage thresholds are enforced (`--coverage`) and the only place the whole workspace is re-checked. It backstops the client-side changed-scope hooks, which are fast *and* skippable via `--no-verify`.

## 5. Sharing hooks: core.hooksPath

`.git/hooks/` is not tracked, so hooks written there are lost on clone. Instead:

```bash
git config core.hooksPath .githooks
```

puts the hooks in an in-repo directory — checked in, reviewable, shared. `narness-git-install.sh` does the copy + config in one step. Verify with `git config --list --local | grep hooksPath`.

## 6. The bypass and the backstop

`git commit --no-verify` / `git push --no-verify` skip client hooks entirely. Client hooks are therefore a *deterrent plus fast feedback*, not a guarantee. The guarantee is one step further right:

- **Server-side `pre-receive`** — runs on the remote, cannot be skipped by the agent. Enforce universal policy (no secrets, tests green, signed commits) here.
- **CI merge gates** — required status checks block the merge on the platform.

Rule of thumb: enforce *what must be universally true* server-side or in CI; use client hooks for *fast, cheap, early* checks that make the agent's life easy.

## 7. Alternatives and adjacent tools

- **pre-commit framework** (`.pre-commit-config.yaml`) — declarative, cross-language, auto-installs hooks and supports `files:` filtering. A good choice when the team already uses it; otherwise `core.hooksPath` is simpler and dependency-free.
- **husky / lint-staged** — JS/TS staged-files-only; a JS analog, not a Rust default.
- **gitleaks / trufflehog** — secret scanning on `pre-commit`; mount when the repo handles credentials.

## 8. Platform caveat

Git runs hook scripts with the shebang's interpreter. Keep the shebang `#!/usr/bin/env bash` and the body POSIX-friendly enough for macOS/Linux; Windows needs the pre-commit framework or a Git Bash environment.
