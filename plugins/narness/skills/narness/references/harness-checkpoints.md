# Harness checkpoints and evidence design

## What a checkpoint is

A checkpoint is a narrow proof obligation, not merely a command.

```text
Checkpoint
=
Invariant
+ Scope
+ Evidence
+ Executor
+ Failure Feedback
```

- **Invariant** — what must remain true.
- **Scope** — where the proof applies.
- **Evidence** — what observation demonstrates the invariant.
- **Executor** — the deterministic mechanism that obtains the evidence.
- **Failure feedback** — where, why, and how to fix a failed proof.

Executable checkpoint scripts remain single-responsibility: one script should answer one narrow yes/no question.

## Checkpoint taxonomy

| Checkpoint | Invariant / question | Typical evidence | Executor |
|---|---|---|---|
| Format | source conforms to fixed style | zero format diff | formatter check mode |
| Compile / type-check | source is structurally valid | successful type-check | compiler |
| Lint / static analysis | code avoids disallowed patterns | clean lint result | linter |
| Invariants | project-specific machine-checkable rule holds | zero violations | focused scan/policy |
| Test | behavior is correct for the selected surface | passing focused tests | test runner |
| Coverage | selected behavior is exercised sufficiently | threshold result | coverage tool |
| Test discipline | changed behavior has an owning test | source-to-test mapping | VCS-aware script |
| Dependency / security | supply-chain policy holds | clean audit | package audit |
| Environment | required runtime tools exist | declared checks pass | environment checker |
| Contract | public boundary remains compatible | contract/snapshot proof | protocol/schema test |
| UI / visual | user-visible behavior is correct | snapshot/screenshot/interaction | UI test tooling |
| Deployment | deployable/runtime state is valid | manifest + health proof | policy/live check |

The exact taxonomy is repository-specific. Add a checkpoint when it expresses a distinct invariant, not merely because another command exists.

## Script-design rubric

1. **Single responsibility** — one executable primitive answers one checkpoint.
2. **Deterministic verdict** — exit code communicates pass/fail.
3. **Diagnostics to stderr** — failures must be visible to hooks and humans.
4. **Localizable and actionable** — report where, why, and how to fix.
5. **Lifecycle-aware scope** — cheap local form, authoritative server-side form.
6. **Sink as low as possible** — native tool over custom scan, language rule over script where appropriate.
7. **Evidence before ceremony** — run a check because it proves an affected invariant, not because "we always run everything."

## Evidence selection

Evidence should follow the changed behavioral surface.

| Surface | Typical evidence |
|---|---|
| Pure logic | focused unit test |
| Public API / protocol | contract + integration |
| UI | typecheck + snapshot/screenshot/interaction |
| Model-visible content | transcript or schema snapshot |
| Database | migration + invariant/compatibility |
| Concurrency | deterministic lifecycle regression |
| CLI | executable smoke + argument contract |
| Deployment | manifest/policy + health proof |
| Docs | docs/link sanity |
| Release | artifact/package/live proof |

## Local proof vs authoritative proof

### Edit time

Run cheap feedback that helps immediate correction.

### Pre-commit

Run fast mechanical checks and local invariants.

### Pre-push

Run the **smallest sufficient proof** for the outgoing diff.

### CI

Run **authoritative proof** for repository acceptance. Full relevant scope, coverage, security, and platform matrices belong here.

### Release

Add artifact and runtime proof.

## Why not one big gate?

A monolithic "run everything" command hides which invariant failed, makes feedback slow, encourages bypass, and prevents lifecycle-specific scope.

Decomposition makes proof:

- localizable;
- composable;
- reusable across agent hooks, Git hooks, and CI;
- cheap enough to run at the earliest useful moment.

## Sink-path examples

| Checkpoint | Typical sink path |
|---|---|
| Format | formatter check -> Git/CI |
| Compile | compiler -> agent hook -> CI |
| Lint | linter script -> source-level forbid |
| Invariant | focused script -> native policy where possible |
| Unit test | focused runner -> pre-push -> CI |
| Contract | contract script -> CI required evidence |
| Dependency audit | package tool -> CI |
| Repository language | text scan -> CI repository gate |

See [tool-checkpoints.md](tool-checkpoints.md) for tool ownership and [git-hooks.md](git-hooks.md) for lifecycle mounting.
