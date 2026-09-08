# The constraint ladder

## Model overview

| Level | Name | Essence | Main role | Failure consequence |
|---|---|---|---|---|
| L0 | Prompt | natural-language intent | suggest | the agent may ignore or forget it |
| L1 | AGENTS / project convention | standing repository instruction | orient | depends on instruction discovery and compliance |
| L2 | Skill | on-demand task procedure | guide | may not be selected or invoked |
| L3 | Agent hook | event-driven feedback | teach | runs automatically on matched events and feeds failure back |
| L4 | Deterministic script | executable validation | prove | returns a reproducible pass/fail verdict when invoked |
| L5 | Language / tool-native rule | compiler, linter, schema, policy | prevent | invalid states are rejected by the owning tool |
| L6 | Git lifecycle gate | pre-commit, commit-msg, pre-push | check | blocks the local lifecycle action but may be bypassed |
| L7 | CI / repository ruleset | server-side required status or policy | block | invalid states cannot enter authoritative history through the normal path |

## Layer details

### L0 Prompt

Use for intent, desired outcomes, and task-specific requests. Never rely on it for an invariant that must always hold.

### L1 AGENTS / project convention

Use for global or scoped standing rules, project structure, safety boundaries, and routing. Keep it small enough to be discovered and understood cheaply.

### L2 Skill

Use for reusable procedures: review, testing, release, deployment, diagnosis, migration, and other multi-step task classes. Skills are capabilities, not authority.

### L3 Agent hook

Use for cheap event-driven feedback close to the edit. A good hook teaches by returning actionable diagnostics into the agent loop.

### L4 Deterministic script

Use for independently reproducible checks such as format, compile, test, invariant scans, coverage, and repository sanity.

### L5 Language / tool-native rule

Prefer this when the owning language or tool can express the invariant directly. Examples include type constraints, source-level lint forbids, schema validation, and package policy.

### L6 Git lifecycle gate

Use for local commit and push checkpoints. These are early and useful but bypassable, so they are not repository authority.

### L7 CI / repository ruleset

Use for universally required repository acceptance. Required CI, server-side policy, and repository rules are the final block before authoritative history.

## Teach, check, block

The ladder has three operational roles:

```text
Teach: L0-L3
Prove/prevent: L4-L5
Check locally: L6
Block authoritatively: L7
```

The boundaries overlap intentionally. For example, a deterministic L4 script may be mounted by both an L3 agent hook and an L7 CI job.

## Core proposition

The goal is not "move everything to L7." The goal is:

> Place each invariant at the lowest practical layer that can express it correctly, then mount the same deterministic primitive at the lifecycle stages that need it.

A workflow procedure may correctly remain a Skill. A type invariant should not remain a prompt. A universal merge requirement should not rely only on a local Git hook.
