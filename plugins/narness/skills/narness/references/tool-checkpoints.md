# Tool checkpoints: what each tool can enforce

## 1. Positioning

A checkpoint in the abstract ([harness-checkpoints.md](harness-checkpoints.md)) needs an **enforcement surface** — a concrete tool mechanism that actually runs it and blocks or feeds back. This document catalogs the surfaces, tool by tool: git, GitHub, GitLab, Claude Code, Codex, and the surrounding dev-toolchain.

The organizing question is not "which rule should exist" but **"which tool owns this moment"** — edit time, save time, commit time, review time, build time. Each tool owns a moment, and enforces checkpoints at that moment with a characteristic strength and granularity.

## 2. The moments and their owners

| Moment | Owning tool | Enforcement style | Ladder level |
|---|---|---|---|
| Edit time | Claude Code / Codex hooks | block + feed back to the agent | L3 |
| Save time | editor / format-on-save | auto-fix | L2/L3 |
| Commit time | git `pre-commit` / `commit-msg` | block the commit | L4 |
| Push time | git `pre-push` | block the push | L4 |
| Review time | GitHub / GitLab merge gates | block the merge | L4/L5 |
| CI time | GitHub Actions / GitLab CI | block the merge, regressions | L4/L5 |
| Continuous | secret scanning, dependabot, audit | alert / auto-fix / deny | L4 |

The rule that connects them: the **further right** a checkpoint sits, the harder it is to bypass but the coarser and slower its feedback; the **further left**, the softer but finer and more immediate. The goal is to mount each checkpoint at the earliest moment whose tool can still enforce it.

## 3. git (client-side)

| Checkpoint | Mount | What it guards against |
|---|---|---|
| Format / lint / fast tests | `pre-commit` | bad code entering history |
| Commit-message format (conventional commits, ticket id, length) | `commit-msg` | undisciplined history, broken tooling that parses messages |
| Full tests / coverage / build | `pre-push` | broken or under-tested state leaving the machine |
| Secret scan (gitleaks / trufflehog) | `pre-commit` | credentials committed by accident |
| No-WIP / no-merge-conflict marker | `pre-commit` | half-finished work landing on shared branches |
| Large / generated file guard | `pre-commit` | blobs that don't belong in git |

Design notes: `pre-commit` must be fast (it runs on every commit); heavy checks go on `pre-push`. Share hooks in-repo via `core.hooksPath`. **Caveat**: `--no-verify` bypasses all client hooks — the true backstop is server-side or CI.

## 4. git (server-side)

| Checkpoint | Mount | What it guards against |
|---|---|---|
| Any policy (format, tests, no-secret, signed commits) | `pre-receive` / `update` | the agent bypassing client hooks — enforced on the remote, cannot be skipped |

Server-side hooks are git's strongest lever (a "physical" constraint): the check runs on the remote, independent of the agent's local state. Use them to enforce what must be universally true.

## 5. GitHub

| Checkpoint | Mechanism | What it guards against |
|---|---|---|
| CI must pass before merge | required status checks / rulesets | broken code reaching the default branch |
| N reviewers must approve | branch protection · required reviews | unreviewed change |
| Specific owners must approve | CODEOWNERS | changes to critical paths without the right reviewer |
| No direct push | branch protection · restrict push | edits that skip review entirely |
| Signed commits / linear history | branch protection | provenance loss, messy history |
| Dependency vulnerabilities | Dependabot alerts + security updates | known-vulnerable deps lingering |
| Secrets in the repo | secret scanning + push protection | credentials leaked at push time |
| Merge hygiene | PR templates, linked issues, auto-merge rules | incomplete context on a PR |

Design note: GitHub enforcement is **asynchronous and review-shaped** — it blocks at merge, not at edit. It's the right place for "who approves" and "does CI pass", the wrong place for "is this line formatted" (too late, too coarse).

## 6. GitLab

| Checkpoint | Mechanism | What it guards against |
|---|---|---|
| Pipeline must be green | protected branches · required pipeline | broken code merging |
| N approvers / specific approvers | merge request approval rules · code owners | unreviewed change |
| No direct push | protected branches (allowed-to-push list) | edits skipping MR |
| SAST / secret detection / dependency & container scanning | built-in security templates in CI | vulns and secrets |
| Merge hygiene | MR templates, approval policies | incomplete context |

Design note: GitLab folds security scanning into the pipeline (SAST/DAST/dependency/container scanning are CI jobs), so the security checkpoints live at CI time rather than as a separate product — same moments, owned by the pipeline.

## 7. Claude Code

| Checkpoint | Mechanism | What it guards against |
|---|---|---|
| Block dangerous commands | `PreToolUse` (e.g. `rm -rf /`, force-push) | destructive actions |
| Validate after edit, feed back | `PostToolUse` (compile/lint/format) | errors while they're still small |
| Don't stop until tests pass | `Stop` hook | the agent declaring done prematurely |
| Gate / inject user input | `UserPromptSubmit` | bad or under-specified prompts |
| Automated permission policy | `PermissionRequest` hook + `settings.json` allow/deny rules | tools used beyond a declared scope |
| Inject context / env at start | `SessionStart` | missing ground truth |

Design note: Claude Code's defining power is the **feedback path** — a `PostToolUse` hook that exits `2` injects its stderr into the agent's context, so the agent *sees* and fixes its own mistake. This is the finest-grained and most immediate surface in the whole ladder.

## 8. Codex

| Checkpoint | Mechanism | What it guards against |
|---|---|---|
| Block / rewrite a tool call | `PreToolUse` (`permissionDecision: deny`) | dangerous commands |
| Validate after edit, feed back | `PostToolUse` (`additionalContext`) | errors while small |
| Block end-of-session | `Stop` (`decision: block`) | premature "done" |
| Automated approval | approval policies in `config.toml` | out-of-scope tool use |

Design note: same moments as Claude Code, different feedback contract — Codex injects context via **stdout JSON** (not exit-2 + stderr), and its hook interception is narrower (only Bash / apply_patch / MCP). The validation logic (`narness-rust-*.sh`) is reusable across both; only the thin adapter layer differs.

## 9. Surrounding dev-toolchain

| Tool | Checkpoint | What it guards against |
|---|---|---|
| pre-commit framework | declarative multi-language hooks, auto-installed, `files` filtering | per-repo hook drift |
| husky / lint-staged | run checks on *staged files only* (JS/TS) | slow whole-repo checks, unstaged churn |
| editorconfig / format-on-save | editor-level formatting | style drift before it reaches a gate |
| language toolchain (formatter, linter, type-checker, test runner, coverage) | the code-quality checkpoints | the catalog in [harness-checkpoints.md](harness-checkpoints.md) |
| gitleaks / trufflehog | secret detection in history and diffs | leaked credentials |
| cargo-audit / npm audit / osv-scanner / snyk / dependabot | dependency vulnerability audit | known-vulnerable deps |
| hadolint / trivy | container image + Dockerfile lint/scan | insecure images |
| terraform fmt/validate, tflint, checkov | IaC syntax + policy | misconfigured infrastructure |
| commitizen / commitlint / husky commit-msg | conventional commit discipline | messages that break changelog/semver tooling |

## 10. Choosing the tool

The same checkpoint can often be enforced by several tools. Choose by two questions:

1. **Which moment is cheapest to fix at?** Mount the checkpoint at the earliest moment whose tool can still enforce it — a compile error is cheapest to fix at edit time (agent hook), a "did the right reviewer approve" is only answerable at review time (platform).
2. **How hard must it be?** If it must be unbypassable, the client-side hook is not enough (`--no-verify`); sink it to server-side or CI.

Sink order, left (soft, fine, immediate) to right (hard, coarse, final):

```
edit-time hook (agent) → commit-time hook (git) → push-time hook (git)
  → review gate (GitHub/GitLab) → CI merge gate → server-side / compile-time
```

## 11. Mapping back to the constraint ladder

| Tool | Ladder level | Enforcement style | Strengths / limits |
|---|---|---|---|
| Claude Code / Codex hooks | L3 | block + feed back | finest, most immediate; the agent can still choose not to fix |
| Editor / format-on-save | L2–L3 | auto-fix | judgment-free; only formatting-class rules |
| git client hooks | L4 | block commit/push | deterministic; bypassable via `--no-verify` |
| GitHub / GitLab merge gates | L4–L5 | block merge | hard, review-shaped; coarse, asynchronous |
| CI (Actions / GitLab CI) | L4–L5 | block merge | hard, regression-proof; slow, batch feedback |
| git server-side hooks | L5 | enforce on remote | cannot be bypassed; only universal policy |
