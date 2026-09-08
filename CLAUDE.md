# Narness

Narness is an AI Workspace Engineering project. It researches and implements repository-level structures that help AI coding agents understand a codebase progressively, discover task procedures on demand, receive deterministic feedback, produce evidence, and keep unproven states out of authoritative history.

Read [docs/architecture.md](docs/architecture.md) before changing the workspace model.

## Core principles

1. **Prefer hard constraints over prompt-only constraints.** If code, hooks, scripts, a compiler, Git, or CI can enforce a rule, sink the rule into that layer.
2. **Treat root instructions as a contract and router.** Keep global invariants here. Put task procedures in Skills and detailed design reasoning in docs.
3. **Keep discovery cheap.** Skill names and descriptions should make selection precise. Load the selected Skill fully, then load only references required by the task.
4. **Keep executable primitives single-responsibility.** Validation logic belongs in scripts or tool-native configuration. Hooks and CI orchestrate those primitives; they do not duplicate their logic.
5. **Require evidence that matches the behavioral surface.** A code change is complete only when the proof is appropriate for what changed.
6. **Fail loud and actionable.** Deterministic checks must return non-zero on failure and explain where, why, and how to fix the problem.
7. **Use English for repository-authored content.** Documentation, source comments, configuration comments, Skill content, examples, and scripts must not contain Chinese text.

## Constraint ladder

```text
L0 Prompt
L1 AGENTS / project convention
L2 Skill
L3 Agent hook
L4 Deterministic script
L5 Language / tool-native rule
L6 Git lifecycle gate
L7 Server-side CI / repository ruleset
```

The goal is to place each rule at the lowest practical level that can express it correctly.

## Knowledge ownership

| Knowledge | Owner |
|---|---|
| Global invariants and routing | root `CLAUDE.md` / `AGENTS.md` |
| Subtree-specific standing rules | scoped `AGENTS.md` / `CLAUDE.md` |
| Task procedures | Skills |
| Detailed task knowledge | Skill references |
| Deterministic repeated operations | scripts |
| Historical design reasoning | architecture docs, ADRs, design notes |
| Authoritative repository acceptance | CI and repository rules |

## Checkpoint model

```text
Checkpoint = invariant + scope + evidence + executor + failure feedback
```

Each executable validation script still answers one narrow yes/no question. Do not introduce a god script that bundles format, lint, test, and policy checks together.

## Script conventions

1. Every script provided by this project starts with `narness-`.
2. Each validation script has one responsibility.
3. Hook entrypoints are thin: evaluate the trigger, then delegate.
4. Failures write actionable diagnostics to stderr.
5. Prefer a tool-native rule over a custom scan, and a language-native rule over a script where possible.
6. Fast local forms may use changed scope; authoritative CI forms use the required full scope.

## Local proof vs repository authority

Local execution should seek the **smallest sufficient proof** for the outgoing change. CI should provide **authoritative proof** for repository acceptance.

- Edit time: format, compile/type-check, cheap invariants.
- Pre-commit: changed-scope fast checks and commit policy.
- Pre-push: focused tests for the outgoing diff.
- Pull request / push CI: authoritative checks, full relevant matrix, security, coverage, and architecture invariants.
- Release: artifact verification and deployment or live proof where applicable.

Client hooks are bypassable. Never treat them as repository authority.

## Repository language gate

Run this before committing documentation or comment-heavy changes:

```bash
bash scripts/narness-repo-english.sh
```

The CI workflow also runs this gate.

## Repository structure

- `docs/architecture.md` — canonical AI Workspace architecture.
- `docs/adoption.md` — step-by-step adoption guide.
- `examples/rust-workspace/` — runnable reference workspace.
- `plugins/narness/` — Claude plugin, Skill, references, hooks, scripts, Git hooks, and config templates.
- `cli/` — environment checker.
- `narness-policy/` — policy engine prototype.
- `scripts/` — repository-specific deterministic checks.

## Development workflow

This repository currently develops directly on `main`. Preserve unrelated changes and commit coherent, working changes as they land.

Before claiming a non-trivial change is complete, run evidence that matches the changed surface. At minimum:

```bash
bash scripts/narness-repo-english.sh
(cd cli && npm test)
cargo test --manifest-path narness-policy/Cargo.toml
cargo test --manifest-path examples/rust-workspace/Cargo.toml
```

Do not run unrelated expensive checks merely for ceremony.

## Current scope

The shipped language harness is Rust-first. The AI Workspace model is language-independent. Future language support should reuse the same contracts, evidence model, lifecycle semantics, and single-responsibility execution pattern.
