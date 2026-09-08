# Engineering Surfaces

> Status: Active research topic.
>
> This topic defines the working model for **Engineering Surfaces**: the semantic structure that connects intent, context, constraints, change impact, and evidence in an AI-native repository.

## 1. Thesis

A repository is physically organized as files, directories, packages, crates, modules, services, and deployment units.

An agent does not work directly in those units of meaning. It works on a task that affects behavior, contracts, workflows, runtime boundaries, and user-visible outcomes.

Narness therefore needs an abstraction between repository topology and engineering reasoning:

> **An Engineering Surface is a semantically meaningful boundary whose context, constraints, change impact, and required evidence can be reasoned about together.**

Examples include:

```text
websocket-contract
terminal-interaction
session-lifecycle
authentication
public-api
database-schema
deployment
model-context
tool-schema
release-artifact
```

The key hypothesis is:

> **Surface is the semantic spine of the AI Workspace.**

Before a change, a Surface helps answer what the agent should know.

During a change, it helps answer what rules and guards apply.

After a change, it helps answer what must be proven.

```text
Intent -> Surface -> Context
Change -> Surface -> Evidence
Evidence -> Gate -> Trust
```

## 2. Why repository topology is insufficient

Repository topology answers questions such as:

```text
Where is this code?
Which package owns this file?
Which module imports this symbol?
```

Engineering reasoning needs different questions:

```text
What behavior is being changed?
Which contracts may be affected?
Which consumers depend on that behavior?
What knowledge is needed to modify it safely?
What evidence proves that it still works?
```

These topologies frequently diverge.

For example:

```text
websocket-contract
├── server/src/protocol/
├── web/src/lib/ws/
├── sdk/src/messages/
└── tests/fixtures/protocol/
```

One Surface spans several packages.

The opposite also happens:

```text
server/
├── authentication
├── websocket-contract
├── session-lifecycle
└── public-api
```

One package participates in several Surfaces.

Therefore:

```text
Repository Topology != Engineering Surface Topology
```

Paths and packages are important signals, but they should not be the final semantic model.

## 3. First-principles role of a Surface

AI Workspace Engineering begins from three questions:

1. What is the minimum relevant truth the agent must know?
2. What boundaries must the agent not be allowed to violate?
3. What evidence makes the resulting change trustworthy?

A Surface connects all three.

### 3.1 Context projection

```text
Intent
  ↓
Relevant Surface
  ↓
Architecture
Files / symbols
Scoped instructions
Skills
Examples
Tests
Known invariants
```

The Surface becomes an entry point for progressive disclosure.

### 3.2 Constraint projection

```text
Surface
  ↓
Applicable rules
Approval boundaries
Tool restrictions
Mechanical invariants
Lifecycle guards
```

The Surface identifies which rules are relevant without loading every repository rule into every task.

### 3.3 Evidence projection

```text
ChangeSet
  ↓
Affected Surface
  ↓
Required invariants
  ↓
Required evidence
  ↓
Gate
```

The same semantic model used for understanding becomes the model used for verification.

## 4. What a Surface is not

A Surface is not automatically:

- a directory;
- a package;
- a business domain;
- a team ownership label;
- a CI job;
- a test suite;
- an LLM-generated topic;
- a replacement for the dependency graph.

Any of these may contribute facts to Surface resolution.

The important distinction is:

> A Surface represents an engineering concern that tends to need to be **understood, constrained, changed, and verified together**.

## 5. Candidate Surface model

The exact schema is not yet a project contract, but the research model should account for several dimensions.

```text
Surface
├── Identity
│   ├── id
│   ├── description
│   └── lifecycle / version
├── Membership Signals
│   ├── paths
│   ├── packages
│   ├── symbols
│   ├── schemas
│   └── runtime resources
├── Context
│   ├── architecture
│   ├── scoped instructions
│   ├── skills
│   ├── references
│   └── examples
├── Contracts
│   ├── invariants
│   ├── public boundaries
│   └── compatibility expectations
├── Relationships
│   ├── depends_on
│   ├── consumed_by
│   ├── overlaps
│   └── contains / contained_by
├── Guards
│   ├── action restrictions
│   ├── required tools
│   └── lifecycle constraints
└── Evidence
    ├── required proof classes
    ├── executors
    └── escalation rules
```

This is a conceptual inventory, not a commitment to one configuration format.

## 6. How Surfaces should be discovered

A Surface should not be invented from a single taxonomy.

Candidate signals include:

### Code structure

- modules;
- packages;
- crates;
- service boundaries;
- generated code;
- shared libraries.

### Behavioral capability

- authentication;
- terminal interaction;
- protocol negotiation;
- task scheduling;
- persistence;
- deployment.

### Contracts

- public APIs;
- wire protocols;
- schemas;
- tool schemas;
- model-visible prompts;
- CLI contracts.

### Runtime topology

- process boundaries;
- services;
- queues;
- databases;
- browsers;
- platforms;
- deployment targets.

### Dependency topology

- import and package graphs;
- generated consumer relationships;
- shared schemas;
- cross-platform consumers.

### Evidence topology

A particularly valuable signal is:

> What code usually has to be validated together?

If several files across different packages repeatedly require the same compatibility or regression proof, they may belong to one Surface.

### Historical change and failure data

Future research may use:

- co-change history;
- CI failure correlation;
- incident history;
- regression clusters;
- review patterns.

These should initially be treated as discovery hints rather than repository authority.

## 7. Declared knowledge vs inferred knowledge

Narness should distinguish authority levels.

```text
Repository-declared knowledge
        ↓ authoritative
Deterministically derived knowledge
        ↓ authoritative when derivation is known
LLM-proposed knowledge
        ↓ advisory
Historical / statistical inference
        ↓ advisory until accepted
```

An LLM can help:

- propose new Surfaces;
- classify an Intent;
- identify suspicious missing relationships;
- explain why a mapping may be incomplete;
- draft Surface declarations.

An LLM should not silently decide mandatory evidence at repository admission time.

The working authority rule is:

> **Models may propose semantic structure; the repository owns the structure that can block or admit a change.**

## 8. Surface resolution before a change

The first resolution problem is:

```text
Intent -> Relevant Surfaces
```

This is inherently less deterministic than post-change impact resolution because no real diff exists yet.

Possible signals include:

- task language;
- issue labels;
- explicitly named components;
- current file context;
- symbols mentioned by the user;
- selected Skill;
- repository search results.

A useful approach is confidence-tiered disclosure:

```text
High-confidence Surface
  -> load core context

Adjacent / dependent Surface
  -> expose summary + route

Unknown
  -> broaden search gradually
```

The goal is not perfect task classification.

The goal is to reduce blind whole-repository exploration while keeping escape routes when the initial Surface hypothesis is incomplete.

## 9. Surface resolution after a change

The post-change problem is stronger because the repository has objective facts.

```text
ChangeSet
  ↓
Path / package / symbol / schema facts
  ↓
Surface Resolver
  ↓
Affected Surfaces
```

Resolution should preserve provenance:

```text
server/src/protocol/message.rs
  -> matched path rule
  -> websocket-contract

schema/protocol.json
  -> generated consumer relation
  -> websocket-contract
  -> sdk-contract
```

Unknown changes must fail safe.

```text
Known impact -> narrow proof
Unknown impact -> widen proof
```

The resolver must never optimize by silently producing no affected Surface for an unrecognized change.

## 10. Surface relationships

Surfaces are unlikely to form a clean tree.

A graph is a more realistic working model.

Possible relationship types:

```text
contains
depends_on
consumed_by
compatible_with
generated_from
deployed_with
overlaps
```

Example:

```text
websocket-contract
  ├── consumed_by -> web-client
  ├── consumed_by -> sdk
  └── depends_on  -> protocol-schema
```

A changed Surface may therefore expand impact to related Surfaces.

This creates an important distinction:

```text
directly affected Surface
!=
transitively required proof Surface
```

The graph must remain explainable. Every expansion should have provenance.

## 11. Surface-driven context

A Surface can expose a machine-oriented context manifest.

Conceptually:

```text
surface: websocket-contract

context:
  architecture:
    - docs/protocol.md
  instructions:
    - server/AGENTS.md
    - web/AGENTS.md
  code:
    - server/src/protocol/
    - web/src/lib/ws/
  tests:
    - tests/protocol/
  skills:
    - protocol-change
```

The agent does not necessarily receive all of this immediately.

Progressive disclosure may be:

```text
Surface summary
  ↓
Architecture + invariants
  ↓
Relevant code map
  ↓
Task-selected files
  ↓
Detailed references / tests / fixtures
```

The Surface is the routing structure, not the context dump.

## 12. Surface-driven guards

Some Surface properties should affect what actions are allowed.

Examples:

```text
database-schema
  -> migration required
  -> destructive migration requires approval

public-api
  -> compatibility check required
  -> generated API artifacts must stay synchronized

release-artifact
  -> signing/release scripts only
  -> protected environment for publication
```

This does not mean every Surface needs custom tool policy.

The research question is which invariants are important enough to sink from guidance into hard enforcement.

## 13. Surface-driven evidence

A Surface should own proof obligations at the semantic level.

Example:

```text
Surface: websocket-contract

Invariants:
  - server and client codecs remain compatible
  - schema evolution remains supported

Evidence:
  - protocol unit proof
  - cross-client contract proof
  - serialization fixture proof
```

Executors are separate:

```text
websocket-contract-test
  local  -> scripts/check-ws-contract.sh --changed
  CI     -> scripts/check-ws-contract.sh --full
```

The Surface expresses **what must be proven**.

The executor expresses **how the proof is produced in this environment**.

## 14. Example end-to-end flow

```text
User intent:
  "add a new WebSocket message type"

        ↓

Intent resolver:
  websocket-contract

        ↓

Context projection:
  protocol architecture
  codec files
  schema rules
  fixtures
  protocol Skill

        ↓

Agent change:
  server/src/protocol/message.rs
  web/src/lib/ws/message.ts
  tests/fixtures/protocol.json

        ↓

Post-change resolver:
  websocket-contract
  web-client

        ↓

Evidence planner:
  server compile
  web typecheck
  protocol unit
  websocket contract
  fixture compatibility

        ↓

Evidence records:
  pass / fail / missing / stale

        ↓

pre-push:
  reject until required local proof is complete

        ↓

CI:
  authoritative broader proof

        ↓

repository gate:
  admit / reject
```

## 15. Minimal viable adoption

Narness should not require a complete repository ontology.

A practical progression may be:

### Stage 1 — named areas

```text
paths -> coarse Surface
```

### Stage 2 — explicit cross-cutting Surfaces

Add protocol, deployment, public API, model context, and other important boundaries that span packages.

### Stage 3 — context and evidence projections

Attach:

- relevant docs;
- Skills;
- invariants;
- proof obligations.

### Stage 4 — relationships

Add cross-Surface impact expansion.

### Stage 5 — richer resolvers

Potentially include:

- symbols;
- schemas;
- dependency graphs;
- runtime topology;
- historical evidence.

The architecture should make early simple declarations compatible with later richer resolution.

## 16. Evaluation criteria

A useful Surface model should improve measurable properties.

### Context precision

How much irrelevant material must the agent read before reaching the relevant code?

### Navigation recall

Does the Surface expose all important consumers and contracts, not only the obvious package?

### Change localization

Can a task be narrowed to a small semantic area without hiding critical dependencies?

### Evidence completeness

Does the Surface reliably lead to the proof required for the changed behavior?

### Explainability

Can the system explain:

```text
why this Surface?
why this context?
why this guard?
why this evidence?
```

### Stability

Can repository layout evolve without constantly changing Surface identity?

## 17. Failure modes

### Surface equals directory

This recreates path filtering under a new name.

### Surface explosion

Creating a Surface for every module or file makes the semantic model harder to use than the repository itself.

### Hidden inference

If mandatory impact resolution depends on opaque model judgment, the repository no longer has a deterministic authority boundary.

### Static ontology obsession

Attempting to fully model the repository before delivering value will stall adoption.

### Context dumping

A Surface that always loads every related file defeats progressive disclosure.

### Evidence coupling

If a Surface directly hard-codes one test command rather than a proof obligation, execution architecture becomes difficult to evolve.

## 18. Open research questions

### Identity

- What is the minimum stable identity of a Surface?
- When should one Surface split into two?
- When should several Surfaces merge?
- How should Surface versions be represented?

### Graph semantics

- Which relationship types are actually needed?
- How should impact propagate across relationships?
- How do we prevent uncontrolled transitive expansion?

### Intent resolution

- How much should be deterministic?
- When is model classification appropriate?
- How should uncertainty be represented?

### Context

- What should be loaded automatically?
- What should remain discoverable but deferred?
- How should generated summaries be kept fresh?

### Evidence

- Which evidence belongs directly to a Surface?
- Which proof is cross-Surface?
- Can evidence be reused when multiple Surfaces require the same invariant?

### Governance

- Who owns Surface declarations?
- How are missing mappings detected?
- How should proposed model-generated relationships be reviewed?

## 19. Graduation criteria

Parts of this topic should graduate into canonical architecture only when Narness can define stable answers for:

- Surface identity;
- authoritative resolution inputs;
- relationship semantics;
- context projection;
- evidence projection;
- fail-safe behavior;
- explainability requirements.

Implementation should follow the stable conceptual model rather than define it accidentally.

## Related topics

- [AI Workspace](../ai-workspace/README.md)
- [Harness Engineering](../harness-engineering/README.md)
- [Change-to-Evidence Planning](../change-to-evidence-planning/README.md)
- [Agent-Native Repository Architecture](../agent-native-repository-architecture/README.md)
