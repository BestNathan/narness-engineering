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

## Guide, Guard, Verify

The constraint ladder describes **where** a rule can live. Narness also needs a second model describing **what role** that mechanism plays in agent behavior.

The working model is:

```text
Guide
  -> help the agent choose correctly

Guard
  -> prevent invalid actions or state transitions

Verify
  -> require evidence before trust or admission
```

These roles are complementary rather than mutually exclusive.

A critical invariant may intentionally appear at several layers:

```text
AGENTS.md
  -> explain the rule

Skill
  -> teach the correct procedure

Hook / native rule
  -> reject an invalid action

Evidence gate
  -> prove the resulting state is acceptable
```

### Guide: soft constraints and routing

Guide mechanisms improve the probability that the agent chooses the right path before a hard failure is necessary.

Typical mechanisms:

- root and scoped instructions;
- Skill routing and procedures;
- architecture references;
- Engineering Surface context;
- examples;
- warnings;
- recommended commands.

Guide is appropriate when:

- judgment is genuinely required;
- several valid implementation strategies exist;
- the rule is explanatory rather than mechanically decidable;
- the agent needs context before acting.

Guide is not repository authority.

A model can misunderstand, forget, truncate, or rationalize around guidance.

Therefore:

> Important correctness or safety invariants should not stop at Guide when a lower deterministic layer can express them.

### Guard: action and transition enforcement

A Guard acts at the point where an invalid action or state transition would occur.

Examples:

```text
attempt destructive migration
  -> require explicit approval

write generated file manually
  -> reject and route to generator

push change with forbidden secret
  -> reject

modify protocol without synchronized schema
  -> block lifecycle transition

publish artifact outside protected release environment
  -> deny
```

A Guard answers:

> **May this action or transition happen?**

Potential Guard locations include:

- tool-call policy;
- sandbox/filesystem policy;
- agent hooks;
- deterministic scripts;
- compiler or type-system rules;
- Git hooks;
- repository permissions;
- protected environments.

Guards should be:

- deterministic where practical;
- close to the invalid action;
- explicit about the violated invariant;
- repair-oriented in their failure feedback;
- narrow enough not to suppress legitimate exploration unnecessarily.

### Verify: evidence-based admission

Verify happens after or alongside the work and asks a different question:

> **What evidence proves that the resulting state is acceptable?**

Examples:

```text
protocol change
  -> compatibility evidence

UI change
  -> visual / interaction evidence

database change
  -> migration + compatibility evidence

runtime lifecycle change
  -> regression + teardown evidence
```

Verify should depend on produced evidence, not agent self-report.

The relevant architecture is:

```text
ChangeSet
  -> Affected Surfaces
  -> Evidence Obligations
  -> Evidence Producers
  -> Evidence Records
  -> Gate
```

### Why all three are needed

Guide alone is probabilistic.

Guard alone can prevent known invalid actions but cannot prove that the final behavior is correct.

Verify alone detects problems late and can make the repair loop unnecessarily expensive.

Together:

```text
Guide
  reduces wrong paths

Guard
  blocks prohibited paths

Verify
  proves accepted outcomes
```

This can also be viewed as:

```text
Before action  -> Guide
At boundary    -> Guard
Before trust   -> Verify
```

### Sinking an invariant through the roles

A useful design exercise is to take one important invariant and ask how far it should sink.

Example:

```text
Invariant:
  public protocol changes must remain client-compatible

Guide:
  AGENTS explains compatibility policy
  protocol Skill explains the change workflow

Guard:
  schema generation cannot be bypassed
  incompatible schema form is rejected mechanically

Verify:
  cross-client contract evidence is mandatory before push / merge
```

The goal is not to duplicate every rule everywhere.

The goal is to ensure that high-value invariants have the appropriate combination of explanation, enforcement, and proof.

### Failure semantics

Guide, Guard, and Verify should fail differently.

```text
Guide failure
  -> agent chose a weak path
  -> provide better context / procedure

Guard failure
  -> action is rejected
  -> explain the violated boundary and allowed repair

Verify failure
  -> state cannot advance
  -> report missing / failed / stale evidence
```

This distinction is important for observability because "the agent failed" is too coarse. Narness should eventually be able to identify whether the failure was:

- context/routing;
- prohibited action;
- missing proof;
- failed proof;
- stale proof;
- repository authority rejection.

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
