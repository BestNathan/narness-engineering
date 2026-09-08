# AI Workspace Engineering Architecture

## Purpose

Narness defines **AI Workspace Engineering** as the design of a repository so that an AI coding agent can:

1. understand the workspace progressively;
2. discover task-specific procedures only when needed;
3. receive deterministic feedback while changing code;
4. derive the evidence required to prove a change;
5. reuse the same executable checks across local and server-side lifecycle stages;
6. prevent unproven states from entering authoritative repository history.

The architecture is agent-runtime agnostic. It can be consumed by Claude Code, Codex, other coding agents, humans, Git, and CI.

## The model

```text
AI Workspace
=
Context Architecture
+ Capability Architecture
+ Constraint Architecture
+ Evidence Architecture
+ Lifecycle Orchestration
```

## Three orthogonal axes

### Context disclosure

```text
Root instructions
  -> scoped instructions
  -> skill metadata
  -> selected SKILL.md
  -> task-relevant references
  -> deterministic scripts / assets
```

This axis answers: **what should the agent know now?**

Rules:

- Keep root instructions small.
- Put only global invariants and early safety boundaries at the root.
- Route subtree-specific rules to scoped instruction files.
- Treat Skill descriptions as routing interfaces.
- Read a selected Skill completely.
- Load only references needed by the current workflow.
- Prefer scripts for repeated deterministic operations.

> Load metadata broadly, instructions selectively, detail lazily, execution deterministically.

### Constraint sinking

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

This axis answers: **where should this rule be guaranteed?**

The correct target is the lowest practical layer that can express the invariant without distorting it.

### Task lifecycle

```text
Discover
  -> Understand
  -> Change
  -> Fast feedback
  -> Pre-push proof
  -> PR evidence
  -> Review
  -> Land
  -> Release
```

This axis answers: **when should the workspace intervene?**

## Workspace Contract

The root `AGENTS.md` or `CLAUDE.md` is a **Workspace Contract and router**, not an encyclopedia.

It should contain:

- project purpose;
- global invariants;
- safety and approval boundaries;
- repository structure;
- routing to scoped instructions;
- routing to common Skills;
- completion and evidence expectations.

Detailed tool tutorials, testing procedures, release runbooks, API references, and historical design discussion belong elsewhere.

## Knowledge Plane

| Class | Question | Typical owner |
|---|---|---|
| Standing rules | What must remain true? | AGENTS / CLAUDE / scoped instructions |
| Procedures | How is this class of task performed? | Skills and scripts |
| Decisions | Why is the system designed this way? | ADRs, design notes, architecture docs |

## Capability Plane

A Skill is a **discoverable capability package**, not merely a prompt.

```text
skill-name/
├── SKILL.md
├── references/
├── scripts/
├── assets/
└── agents/
    └── metadata.yaml
```

Only `SKILL.md` is required.

Progressive disclosure has four stages:

1. selection: name and description;
2. procedure: full `SKILL.md`;
3. detail: only task-relevant references;
4. execution: deterministic scripts and assets.

A vague Skill description is a routing bug.

## Enforcement Plane

Narness separates three roles.

### Teach

Edit-time feedback helps the agent self-correct immediately.

### Check

Git lifecycle gates re-evaluate the outgoing change. They are useful but bypassable.

### Block

Server-side CI, repository rules, and release gates decide whether a state may enter authoritative history.

> Agent hooks are feedback mechanisms. CI and repository rules are authority mechanisms.

## Evidence Architecture

A change is complete when evidence appropriate to the changed behavior exists.

```text
Checkpoint
=
Invariant
+ Scope
+ Evidence
+ Executor
+ Failure Feedback
```

- **Invariant:** the fact that must hold.
- **Scope:** where the proof applies.
- **Evidence:** the observation demonstrating the invariant.
- **Executor:** the deterministic mechanism obtaining the evidence.
- **Failure feedback:** where, why, and how to fix a failed proof.

### Evidence by behavioral surface

| Change surface | Typical evidence |
|---|---|
| Pure logic | focused unit tests, type-check, lint |
| Public API / protocol | contract tests, integration tests, compatibility proof |
| UI | type-check, snapshot, screenshot, interaction or E2E proof |
| Model-visible prompt/tool schema | transcript or schema snapshot |
| Database | migration test, invariant check, compatibility or rollback proof |
| Concurrency/lifecycle | deterministic regression and teardown proof |
| CLI | executable smoke test and argument contract |
| Deployment | manifest/policy validation plus rollout or health proof |
| Documentation | link or docs sanity check |
| Release | artifact verification, package acceptance, smoke/live proof |

## Smallest sufficient proof vs authoritative proof

### Edit time

Run cheap corrective checks: format, compile/type-check, cheap invariants.

### Pre-commit

Run fast mechanical checks: format, changed-scope lint, test discipline, commit policy.

### Pre-push

Provide the **smallest sufficient proof** for the outgoing diff: focused tests and relevant contracts.

### CI

Provide **authoritative proof**: full relevant lint/test matrix, coverage, security, architecture invariants, and platform matrix when required.

### Release

Prove the artifact and runtime transition.

## Deterministic primitives and orchestration

Validation logic belongs in executable primitives. Hooks, Skills, and CI decide when and at what scope to run them.

```text
Agent hook ----+
Git hook ------+--> deterministic primitives
Skill ---------+
CI ------------+
```

Do not bury an invariant inside CI YAML when the same check should also run locally.

## Stable required gate

Repository rules should depend on one stable status, not every internal CI job name.

```text
format --------+
lint ----------+
unit ----------+
integration ---+--> required
security ------+
architecture --+
```

Only `required` needs to be configured as the stable merge gate. Internal jobs can evolve independently.

## Change Scope Engine and Evidence Planner

Narness already distinguishes changed and full execution. The next abstraction is to make the reason for execution explicit.

```text
ChangeSet
  -> Scope Resolver
  -> Affected Surfaces
  -> Evidence Planner
  -> Execution Plan
```

A future `narness plan` command should expose this plan. It is **not implemented yet**.

Example:

```text
Changed:
  web/src/features/terminal/Terminal.tsx
  web/src/lib/ws/channel.ts

Affected surfaces:
  - web
  - terminal
  - websocket

Required evidence:
  - format
  - typecheck
  - terminal integration
  - websocket contract
  - UI snapshot

Not required:
  - database
  - deployment
  - full e2e
```

### Proposed planner inputs

- Git base and head;
- changed paths;
- repository change-surface rules;
- capability ownership;
- checkpoint definitions;
- explicit safety fallbacks.

### Proposed planner outputs

- affected surfaces;
- required evidence;
- skipped evidence and reason;
- execution scope;
- fallback-to-full reason when scope cannot be proven safely.

The planner must fail safe. Unknown ownership or a root workspace change should expand scope rather than silently under-check.

## Adapter boundary

Narness should remain agent-runtime agnostic.

```text
narness
├── contract
├── skills
├── constraints
├── checkpoints
├── scope
├── evidence
├── lifecycle
└── adapters
    ├── claude
    ├── codex
    ├── git
    └── github
```

This is architectural vocabulary, not a requirement to create these code modules immediately.

## Non-goals

Narness is not intended to become:

- a model provider;
- an Agent Runtime;
- a replacement for Claude Code or Codex;
- a general workflow DSL;
- a reason to run every check locally;
- a second implementation of compiler, linter, or CI behavior.

Its role is to engineer the workspace around those systems.

## Design test

A repository is moving toward an AI-native workspace when these questions have increasingly deterministic answers:

1. What instructions apply to this path?
2. What capability should handle this task?
3. What rules are advisory and what rules are enforced?
4. What changed surfaces are affected?
5. What evidence proves the change?
6. Which checks should run now?
7. What can still block the change before it reaches authoritative history?
