# Adopting Narness in a Repository

This guide turns the AI Workspace architecture into a concrete adoption sequence. The runnable reference is [examples/rust-workspace](../examples/rust-workspace/README.md).

## 1. Write the Workspace Contract

Create a small root `AGENTS.md` or `CLAUDE.md`.

Keep only project purpose, global invariants, safety boundaries, repository structure, routing, and completion/evidence expectations.

Do not put detailed test, release, deployment, or review procedures in the root file.

## 2. Separate rules, procedures, and decisions

```text
Standing rules -> AGENTS / CLAUDE
Procedures     -> Skills
Decisions      -> ADR / design notes
```

When a root instruction becomes a multi-step runbook, move it into a Skill.

## 3. Package repeated procedures as Skills

A minimal Skill:

```text
.agents/skills/validate-change/
├── SKILL.md
└── references/
    └── evidence.md
```

Add `scripts/` only for repeated deterministic operations. Add `assets/` only for stable templates.

Write a precise description. Skill metadata is the selection interface.

## 4. Identify soft constraints worth sinking

For every repeatedly violated rule, ask:

1. Is this only guidance?
2. Can a hook detect it immediately?
3. Can a deterministic script prove it?
4. Can a compiler, linter, schema, or policy engine express it natively?
5. Must Git or CI block it?

```text
Prompt -> Convention -> Skill -> Agent Hook -> Script
       -> Native Rule -> Git Gate -> CI / Ruleset
```

## 5. Create single-responsibility executable primitives

Good:

```text
narness-rust-fmt.sh
narness-rust-check.sh
narness-rust-clippy.sh
narness-rust-test-unit.sh
```

Avoid monolithic "run everything" scripts. Failure output must be actionable and deterministic.

## 6. Mount fast feedback close to the edit

Agent hooks should run only cheap checks that help immediate self-correction.

For Rust, Narness ships a Claude Code `PostToolUse` hook that delegates to `narness-rust-check.sh`.

## 7. Add Git lifecycle gates

Use pre-commit for fast mechanical checks, commit-msg for commit policy, and pre-push for focused proof.

```bash
bash plugins/narness/scripts/narness-git-install.sh
```

Client hooks are early feedback, not repository authority.

## 8. Define evidence by change surface

Start with a table, not a complex DSL.

| Surface | Required evidence |
|---|---|
| Rust library logic | format, check, unit, integration |
| Public protocol | contract + integration |
| UI | typecheck + snapshot + interaction proof |
| Deployment | manifest validation + health proof |
| Documentation | docs sanity |

## 9. Make CI authoritative

```text
format --------+
lint ----------+
unit ----------+
integration ---+--> required
security ------+
architecture --+
```

Configure repository rules against only the stable `required` status.

Use [plugins/narness/config/ci.yml](../plugins/narness/config/ci.yml) as a starting template.

## 10. Keep local proof smaller than CI proof

- Local: smallest sufficient proof.
- CI: authoritative proof.
- Release: artifact and runtime proof.

## 11. Declare runtime prerequisites

```toml
[[checks]]
type = "version"
name = "cargo"
min = "1.85"

[[checks]]
type = "exists"
name = "rg"
```

Then run `npx narness`.

## 12. Verify the adoption

For a Rust repository:

```bash
bash plugins/narness/scripts/narness-rust-fmt.sh
bash plugins/narness/scripts/narness-rust-check.sh
bash plugins/narness/scripts/narness-rust-clippy.sh --scope=full
bash plugins/narness/scripts/narness-rust-test-unit.sh --scope=full
bash plugins/narness/scripts/narness-rust-test-integration.sh --scope=full
```

## 13. Grow only after observing a failure

When an agent repeatedly violates a rule:

1. record the failure;
2. identify the invariant;
3. choose the lowest practical enforcement layer;
4. add the narrowest deterministic proof;
5. mount it at the earliest useful lifecycle point;
6. keep CI as the final backstop.

That feedback loop is harness engineering.
