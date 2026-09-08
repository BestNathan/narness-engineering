# AI Workspace

> Status: Active topic.

## Purpose

This topic studies the repository as an **AI Workspace**: an execution environment intentionally designed for AI coding agents rather than a passive collection of source files.

The current working model is:

```text
AI Workspace
=
Context Architecture
+ Capability Architecture
+ Constraint Architecture
+ Evidence Architecture
+ Lifecycle Orchestration
```

The central question is:

> What must a repository provide so that an agent can discover the right context, use the right capabilities, obey important constraints, produce sufficient evidence, and move safely through the development lifecycle?

## Current working areas

### Context Architecture

How repository knowledge is disclosed progressively:

```text
Root Instructions
→ Scoped Instructions
→ Skill Metadata
→ SKILL.md
→ References / Scripts / Assets
```

### Capability Architecture

How reusable procedures and tools become discoverable agent capabilities without flooding model context.

### Constraint Architecture

How rules move from prompt-level guidance toward deterministic enforcement.

### Evidence Architecture

How the workspace decides what observations prove that a change is correct.

### Lifecycle Orchestration

How the workspace intervenes across:

```text
Discover
→ Understand
→ Change
→ Fast Feedback
→ Pre-push Proof
→ PR Evidence
→ Review
→ Land
→ Release
```

## Surface as a working semantic spine

A current Narness research hypothesis is that **Engineering Surface** can connect the major AI Workspace concerns without collapsing them into one implementation mechanism.

```text
Before change:
Intent -> Surface -> Context

During change:
Surface -> applicable constraints / guards

After change:
ChangeSet -> Surface -> Evidence
```

This would make Surface a common semantic vocabulary while preserving separate systems for context disclosure, enforcement, and verification.

The hypothesis is intentionally being developed in the [Engineering Surfaces](../engineering-surfaces/README.md) topic before becoming a canonical architecture contract.

## Canonical documents

- [AI Workspace architecture](../../architecture.md)
- [Adoption guide](../../adoption.md)
- [Narness Skill](../../../plugins/narness/skills/narness/SKILL.md)

## Related topics

- [Harness Engineering](../harness-engineering/README.md)
- [Engineering Surfaces](../engineering-surfaces/README.md)
- [Agent-Native Repository Architecture](../agent-native-repository-architecture/README.md)
- [Change-to-Evidence Planning](../change-to-evidence-planning/README.md)

## Open research directions

- workspace contracts and scoped instructions;
- capability discovery and progressive disclosure;
- deterministic versus model-mediated decisions;
- evidence planning;
- lifecycle-aware agent feedback;
- local versus repository authority;
- environment and deployment contracts;
- observability of agent work and produced evidence.

This topic is broader than any single Narness command or plugin. Stable conclusions should graduate into the canonical architecture or implementation.
