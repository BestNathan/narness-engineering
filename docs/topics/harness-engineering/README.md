# Harness Engineering

> Status: Active topic.

## Purpose

Harness Engineering studies how a repository and its surrounding tooling shape agent behavior so that useful outcomes do not depend on prompt memory alone.

The core principle is:

> If a rule can be enforced by code, hooks, scripts, a compiler, Git, or CI, do not leave that rule only in a prompt.

Harness Engineering is therefore concerned with the entire path from guidance to repository authority.

## Constraint sinking

The current working ladder is:

```text
L0 Prompt
L1 AGENTS / Convention
L2 Skill
L3 Agent Hook
L4 Deterministic Script
L5 Language / Tool Native Rule
L6 Git Lifecycle Gate
L7 Server-side CI / Repository Ruleset
```

The design problem is not simply "how do we add more checks?"

It is:

> At which layer should each invariant live so that it is visible enough to guide the agent and strong enough to be trusted?

## Major areas

### Instructions

Root and scoped instructions define standing contracts, approval boundaries, architecture rules, and routing.

### Skills

Skills own task-specific procedures and progressively disclose detail only when relevant.

### Hooks

Agent hooks and Git hooks provide fast feedback close to the point where invalid state is introduced.

### Deterministic primitives

Scripts and language-native tooling provide reusable, independently executable checks.

### Evidence

Validation should be described in terms of what it proves rather than only the commands that happen to run.

### Repository authority

Server-side CI and repository rules own the authoritative admission decision.

## Current reference material

- [AI Workspace architecture](../../architecture.md)
- [Adoption guide](../../adoption.md)
- [Constraint ladder](../../../plugins/narness/skills/narness/references/constraint-ladder.md)
- [Harness checkpoints](../../../plugins/narness/skills/narness/references/harness-checkpoints.md)
- [Narness Skill](../../../plugins/narness/skills/narness/SKILL.md)

## Related topics

- [AI Workspace](../ai-workspace/README.md)
- [Change-to-Evidence Planning](../change-to-evidence-planning/README.md)

## Open research directions

- where judgment should remain model-mediated;
- when a repeated instruction should become a deterministic primitive;
- how local hooks and CI should divide responsibility;
- how Skills should route to scripts and references;
- how evidence requirements should be represented;
- how repository policy should stay stable while internal CI topology evolves;
- how harness design affects model context, cache stability, and agent observability.

Stable patterns should graduate into Narness architecture, Skills, scripts, examples, or CI templates.
