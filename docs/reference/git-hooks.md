# Git hooks: harness execution at commit/push time

## 1. Mechanism

Git executes same-named scripts in the `.git/hooks/` directory around specific actions. These scripts are the **version-control layer** of constraints — they intercept code before it enters git history.

Hooks come in two kinds:

- **Client-side hooks**: triggered in the local repo (commit, push, etc.), used for pre-commit validation
- **Server-side hooks**: triggered on the remote (pre-receive, update, post-receive), used to enforce policy

Harness scripts mostly mount on **client-side hooks**, because the goal is "intercept bad code before the agent commits it".

## 2. Common client-side hooks

| Hook | Timing | Use | Non-zero exit effect |
|---|---|---|---|
| `pre-commit` | before `git commit`, before the commit-message editor opens | format, lint, fast tests | block the commit |
| `commit-msg` | after editing the message, before committing | validate commit-message format | block the commit |
| `pre-push` | before `git push` | full tests, heavier gates | block the push |
| `post-commit` | after the commit completes | notification, logging | doesn't block |
| `pre-rebase` | before `git rebase` | block dangerous rebases | block |
| `post-merge` / `post-checkout` | after merging/switching branches | trigger dependency updates | doesn't block |

For a harness, the most useful are `pre-commit` (fast checks) and `pre-push` (heavy checks).

## 3. Configuration

### 3.1 Write `.git/hooks/` directly

```bash
# .git/hooks/pre-commit
#!/usr/bin/env bash
set -euo pipefail
bash plugins/narness-rust/scripts/narness-rust-fmt.sh
bash plugins/narness-rust/scripts/narness-rust-clippy.sh
```

```bash
chmod +x .git/hooks/pre-commit
```

**Downside**: `.git/` isn't checked in, so it can't be shared; it's lost on a new machine / clone.

### 3.2 Point `core.hooksPath` at an in-repo directory

Put hooks in the repo (e.g. `.githooks/`) and point git at it:

```bash
git config core.hooksPath .githooks
```

**Upside**: hook scripts are checked in, shareable, code-reviewable.

### 3.3 The pre-commit framework

Declarative management via `.pre-commit-config.yaml` — cross-language, auto-installed:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: narness-rust-fmt
        name: cargo fmt --check
        entry: bash plugins/narness-rust/scripts/narness-rust-fmt.sh
        language: system
        files: '\.rs$'
      - id: narness-rust-clippy
        name: cargo clippy -D warnings
        entry: bash plugins/narness-rust/scripts/narness-rust-clippy.sh
        language: system
        files: '\.rs$'
```

**Upside**: manages hook installation automatically, supports `files` filtering (only fires on `.rs` changes), mature ecosystem.

## 4. Hook script conventions

1. **Exit code**: `0` = pass; **non-zero = block the commit/push**. This is git hooks' enforcement mechanism.
2. **stdout/stderr**: hook output is shown to the user (the committer), but is **not** fed back to any LLM — a git hook only "blocks", it doesn't "feed back".
3. **Performance**: pre-commit must be fast (runs on every commit); leave heavy checks to pre-push or CI.

## 5. Concrete example: layered mounting

**pre-commit (fast)** — only format and lint, done in seconds:

```bash
#!/usr/bin/env bash
# .githooks/pre-commit
set -euo pipefail
bash plugins/narness-rust/scripts/narness-rust-fmt.sh
bash plugins/narness-rust/scripts/narness-rust-clippy.sh
```

**pre-push (heavy)** — changed-scope unit tests:

```bash
#!/usr/bin/env bash
# .githooks/pre-push
set -euo pipefail
bash plugins/narness-rust/scripts/narness-rust-test-unit.sh --scope=changed
```

The full unit/integration suites with coverage (`--scope=full --coverage`) run in CI — the place allowed to run long. Client-side hooks stay changed-scope; CI stays full-scope. e2e runs in a dedicated, optional workflow.

## 6. Caveats

- **Bypass**: `git commit --no-verify` skips pre-commit. A git hook is a "constraint", not "physically unviolable" — only server-side hooks or CI are truly enforced.
- **Server-side hooks**: `pre-receive` validates on the remote, which the agent cannot bypass. This is git's strongest constraint (corresponding to L5's "physically impossible to violate").
- **Windows**: hook scripts run with sh by default; the shebang must be compatible, or use the pre-commit framework to dodge platform differences.

## 7. Position in the layered harness

A git hook is a "commit-level" constraint, coarser but "harder" than the agent's edit-level hooks (Claude Code / Codex) — it's executed by git, independent of the agent's goodwill. Layering:

```
After edit (CC/Codex hook) → pre-commit (git) → pre-push (git) → CI
  fine-grained immediate feedback   block bad code      full test gate      regression protection
```

A git hook's value: even if the agent ignores edit-level immediate feedback, bad code **never enters git history**.
