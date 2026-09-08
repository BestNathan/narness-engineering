# Agent-Native Repository Architecture

> Status: Active research topic.
>
> This topic studies how repository architecture should evolve when AI agents perform a growing share of code navigation, implementation, refactoring, testing, and maintenance.

## 1. Thesis

Traditional repository design is primarily optimized for humans.

It assumes that engineers will:

- browse directories manually;
- retain architecture in long-term memory;
- follow imports and call chains;
- read documentation and source together;
- infer hidden conventions from neighboring code;
- review a manageable amount of change line-by-line.

AI coding changes these assumptions.

An AI-native repository may be read and modified by agents much more frequently and much faster than a human can inspect every line.

The optimization target therefore shifts toward:

> **Agent-first consumability with human-auditable fallback.**

This does not mean making source code unreadable to humans.

It means accepting that the primary consumer of repository structure may increasingly be a machine reasoning under context, tool, and time budgets.

## 2. The wrong response: two codebases

A tempting design is:

```text
human-oriented source
+
AI-oriented source / metadata copy
```

That creates two truths.

They will drift.

Narness should instead pursue:

> **One canonical source of truth, multiple consumable projections.**

```text
Canonical Repository Facts
          ↓
  Semantic / Surface Model
     ┌────┼────────┬──────────┐
     ↓    ↓        ↓          ↓
 Agent   Human   Change     Evidence
 View    View    Impact      View
```

The projections may differ in representation without duplicating the underlying truth.

## 3. What makes a repository agent-consumable?

Agent consumability is not the same as minimal file count or maximal documentation.

A repository is agent-consumable when an agent can cheaply and reliably answer:

```text
Where should I start?
What is relevant?
What must remain true?
Which boundaries should I not cross?
What code is coupled to this behavior?
What procedure should I follow?
How do I prove the result?
```

The architecture should reduce the number of speculative search steps required to reach these answers.

## 4. Human-first and agent-first optimization

Traditional human-first design often values:

- intuitive folder browsing;
- familiar framework conventions;
- prose explanation;
- locally readable abstractions;
- team-specific tacit knowledge.

Agent-first design adds different pressures:

- explicit semantic routing;
- stable machine-readable boundaries;
- low hidden coupling;
- deterministic commands;
- progressive disclosure;
- compact scoped context;
- reproducible evidence;
- explainable impact resolution.

The desired outcome is not to sacrifice human design quality.

It is to make implicit engineering knowledge explicit enough that both agents and humans can recover it.

## 5. One truth, multiple projections

A useful working model is:

```text
Repository
├── source
├── tests
├── schemas
├── configs
├── instructions
├── Skills
└── deterministic tools
      ↓
Engineering Surface Model
      ↓
Projections
├── Agent Code Map
├── Progressive Context View
├── Human Architecture View
├── Change Impact View
├── Constraint View
└── Evidence View
```

Each projection answers a different question.

### Agent Code Map

```text
For this task, what should I inspect first?
```

### Progressive Context View

```text
What knowledge should be loaded now, and what should remain deferred?
```

### Human Architecture View

```text
What are the major concepts and why are they connected?
```

### Change Impact View

```text
What semantic areas did this diff affect?
```

### Constraint View

```text
Which rules are advisory, enforced, or approval-gated?
```

### Evidence View

```text
What proof remains before this state can be trusted?
```

## 6. Physical topology vs semantic topology

The physical directory tree is only one index.

```text
Physical topology:
  files
  directories
  packages
  modules
```

Agent reasoning often needs:

```text
Semantic topology:
  surfaces
  contracts
  capabilities
  invariants
  evidence
  runtime relationships
```

The repository should not be forced to reshape every directory around the semantic graph.

Instead:

> Physical structure should remain coherent, while semantic projections provide additional navigation dimensions.

This keeps source organization practical while avoiding the assumption that directory hierarchy is the only architecture.

## 7. Properties of an agent-native module

A strong module or package boundary should increasingly have explicit properties.

### Clear purpose

The module has a narrow reason to exist.

### Explicit public boundary

Inputs, outputs, contracts, schemas, and exported behavior are identifiable.

### Low hidden coupling

Important behavior does not depend on conventions that only an experienced maintainer knows.

### Discoverable validation

There is a clear path from change to relevant proof.

### Scoped instructions

Special rules are close enough to the code to be found when needed.

### Stable naming

Names communicate engineering role instead of incidental implementation history.

### Bounded context cost

Understanding the module should not require loading a disproportionate amount of unrelated repository state.

### Observable behavior

Important outputs and failures are inspectable through tests, logs, traces, snapshots, or deterministic tools.

These properties benefit humans as well, but they become especially important for agents.

## 8. Code maps as generated or derived views

A Code Map should not be a manually maintained giant file list.

It should be a projection of repository facts and Engineering Surfaces.

Conceptually:

```text
Task Intent
  ↓
Surface
  ↓
Code Map
├── primary implementation
├── public contracts
├── consumers
├── tests
├── examples
├── scoped instructions
└── related Skills
```

A useful map prioritizes.

It should distinguish:

```text
must read
likely relevant
adjacent / dependent
available on demand
```

This supports progressive disclosure rather than context flooding.

## 9. Progressive context architecture

An agent-native repository should treat context as a budgeted resource.

A possible disclosure sequence:

```text
Level 0: repository identity
Level 1: Surface summaries
Level 2: selected Surface contract
Level 3: relevant files / symbols / tests
Level 4: references / historical decisions
Level 5: deep implementation detail
```

The system should optimize for:

> **sufficient context, not maximum context.**

More context can reduce reasoning quality if it introduces unrelated details, stale documentation, or conflicting conventions.

## 10. Documentation roles

Agent-native architecture should separate document roles clearly.

### README

Primarily explains the project to humans and gives high-level entry points.

### AGENTS / CLAUDE

Defines standing agent contracts and routing.

It should not become a full project encyclopedia.

### Scoped AGENTS

Defines local invariants and boundaries for a subtree or Surface-adjacent area.

### Skills

Describe task procedures.

### Architecture / ADR

Explain stable system structure and design decisions.

### Topics

Preserve unresolved research and evolving methodology.

### Surface metadata

Connects semantic concerns to context, constraints, relationships, and evidence.

The key principle is:

> Do not force one document type to serve every consumer and lifecycle stage.

## 11. Skills and agent-native architecture

Skills are part of repository architecture because they package procedures that would otherwise live as tacit human workflow.

A Skill can answer:

```text
When this task class appears:
  what sequence should be followed?
  what tools should be used?
  what references should be loaded?
  what evidence should be produced?
```

The repository therefore becomes more than source code.

It becomes a structured work environment.

## 12. Deterministic interfaces over prose-only behavior

If an operation is common and mechanically expressible, an agent-native repository should expose it as an executable interface.

Prefer:

```bash
./scripts/check-protocol
./scripts/test-terminal --changed
narness plan
```

over requiring an agent to reconstruct the correct shell sequence from prose every time.

The rule is not "replace documentation with scripts."

The rule is:

> Put procedural meaning in documentation and deterministic mechanics in executable interfaces.

## 13. Semantic locality

Traditional locality means related files are near each other.

Agent-native locality can also be semantic.

Even when files are physically separated, the workspace should make the relationship cheap to discover.

Example:

```text
protocol schema
server codec
web client
SDK
fixtures
```

These may live in different packages.

An Engineering Surface can restore semantic locality without forcing an unnatural monorepo layout.

## 14. Designing for bounded reasoning

Agents operate under context limits and imperfect attention.

Architecture should therefore prefer:

### Smaller stable contracts

A narrow interface is cheaper to reason about than a broad implicit dependency.

### Explicit invariants

Important assumptions should not require reverse-engineering implementation details.

### Controlled abstraction depth

Long chains of indirection increase navigation cost.

### Deterministic discovery

Important commands and entry points should be findable from stable locations.

### Fewer accidental aliases

Multiple names for the same concept make routing harder.

### Clear ownership of truth

A concept should have an identifiable canonical definition.

## 15. Human auditability remains a requirement

Agent-first does not mean human-irrelevant.

Humans still need to:

- investigate incidents;
- approve high-risk changes;
- understand architecture shifts;
- debug novel failures;
- perform security review;
- decide product and policy questions;
- recover when automation is wrong.

The standard should therefore be:

```text
Agent-first operation
Human-readable explanation
Human-interruptible execution
Human-auditable evidence
```

Humans may stop reading every implementation line while still retaining control over the system.

## 16. Architecture evaluation metrics

Agent-native architecture needs better metrics than subjective directory neatness.

Candidate measures include:

### Context acquisition cost

How many tool calls, files, or tokens are needed before the agent reaches the relevant implementation?

### Navigation precision

How much loaded material is actually relevant?

### Navigation recall

How often does the workspace miss an important consumer, contract, or test?

### Change localization

Can an intended change remain inside a small, understood semantic region?

### Constraint escape rate

How often can invalid changes bypass only-prose rules?

### Evidence closure time

How quickly can the agent reach a state where all required proof is complete?

### Repair loop efficiency

After a failed gate, can the agent identify the relevant cause and repair path without restarting broad exploration?

### Human recovery cost

When the agent fails, how hard is it for a human to reconstruct what happened and why?

## 17. Repository patterns worth researching

### Surface-oriented code maps

Semantic maps generated from Surface declarations and repository facts.

### Contract-first boundaries

Schemas, APIs, protocols, and invariants made explicit enough to route context and evidence.

### Scoped instruction routing

Instructions attached to the smallest stable scope that owns them.

### Executable capability interfaces

Common workflows available as scripts or Skills rather than reconstructed ad hoc.

### Evidence-addressable tests

Tests named and grouped by the behavior they prove, not only by package location.

### Stable machine-readable metadata

Repository knowledge represented in formats that can be consumed without full prose parsing.

## 18. Anti-patterns

### Giant root instruction files

They maximize context cost and dilute important invariants.

### Directory-as-architecture absolutism

A folder tree cannot represent every cross-cutting contract.

### Prompt-only operational knowledge

Critical workflows remain probabilistic if the agent must remember them from prose.

### Generated summaries without provenance

A convenient view becomes dangerous if the agent cannot determine where it came from or whether it is stale.

### Duplicated AI documentation

Separate manually maintained "AI docs" create a second truth.

### Excessive micro-modularization

Making every file tiny does not automatically improve reasoning; it can increase navigation and indirection.

### Opaque abstractions

A highly generic framework can reduce human repetition while increasing agent inference cost.

## 19. Migration path for existing repositories

An existing project does not need a full redesign.

A gradual path is:

### Stage 1 — Explicit workspace contract

Clarify global invariants and routing.

### Stage 2 — Scoped instructions and Skills

Move local procedures and task workflows out of giant root prompts.

### Stage 3 — Deterministic entry points

Expose build, test, lint, migration, and release mechanics as stable commands.

### Stage 4 — Identify high-value Surfaces

Start with contracts that frequently cross package boundaries or require special proof.

### Stage 5 — Build semantic projections

Generate or maintain small Code Maps and context routes for those Surfaces.

### Stage 6 — Connect change to evidence

Use the same semantic model for post-change proof.

### Stage 7 — Refactor physical architecture only where evidence supports it

If repeated agent failures reveal poor boundaries, then change package/module structure.

The semantic model should help identify where physical redesign is actually valuable.

## 20. Open research questions

### Repository structure

- Which directory patterns reduce agent navigation cost?
- When should physical layout follow Surface boundaries?
- When should semantic metadata be preferred over moving code?

### Code representation

- Are smaller files actually better for agents?
- What abstraction depth is optimal?
- How much type/schema information should be made explicit?

### Context

- What is the best generated Code Map representation?
- How should freshness and provenance be represented?
- How can context selection be evaluated empirically?

### Human role

- Which artifacts do humans still need to inspect directly?
- How should high-risk changes escalate from agent-first operation to human review?

### Tooling

- Which repository facts should Narness derive automatically?
- Which facts should remain explicitly authored?
- Can compiler, language server, dependency graph, and test metadata be unified into Surface projections?

## 21. Research hypothesis

The long-term hypothesis is:

> The AI-native repository is not a second source tree designed for machines. It is a repository whose engineering knowledge is explicit enough to produce machine-optimized views without losing canonical truth or human control.

That suggests a future architecture:

```text
Canonical Repository
        ↓
Repository Facts
        ↓
Engineering Surfaces
        ↓
┌───────────────┬────────────────┬────────────────┐
│ Agent Context │ Change Impact  │ Evidence Plan  │
└───────────────┴────────────────┴────────────────┘
        ↓
Agent Work + Repository Gates
        ↓
Auditable Result
```

## 22. Graduation criteria

Stable conclusions should graduate into canonical Narness architecture only after the project can define:

- what "agent consumability" means operationally;
- which metrics are useful;
- how Code Maps are sourced and kept fresh;
- how human auditability is preserved;
- when semantic metadata should influence physical repository design.

Until then, this remains a research topic rather than a fixed repository style guide.

## Related topics

- [AI Workspace](../ai-workspace/README.md)
- [Engineering Surfaces](../engineering-surfaces/README.md)
- [Harness Engineering](../harness-engineering/README.md)
- [Change-to-Evidence Planning](../change-to-evidence-planning/README.md)
