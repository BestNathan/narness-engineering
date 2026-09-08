# Change-to-Evidence Planning

> Status: Research note and preliminary architecture analysis.
>
> This document records the problem statement, design rationale, reference implementations, and an initial conceptual model for change-aware evidence planning in an AI Workspace. It is intentionally not a final implementation specification.

## 1. Motivation

Modern AI-assisted software development has a verification problem.

Agents can modify code quickly, but determining **what must be verified after a change** is still handled by a mixture of full-suite CI, path filters, package-level test selection, repository instructions, and agent judgment.

Common patterns are:

```text
Run everything
```

```text
Changed files
-> Changed packages
-> Package tests
```

or:

```text
Diff
-> Agent reads AGENTS.md / SKILL.md
-> Agent decides what to validate
```

Each approach solves part of the problem, but none provides a complete and explicit model connecting repository changes to the proof required for those changes.

The missing abstraction is:

> A deterministic mapping from repository changes to the behavioral surfaces they may affect, and from those surfaces to the evidence required to validate them.

This document calls that process **Change-to-Evidence Planning**.

---

## 2. The Problem

A repository does not need tests merely because files changed.

It needs evidence because some behavioral, compatibility, operational, or user-visible contract may have changed.

These concepts are different:

```text
Changed File
!=
Affected Behavior
!=
Required Evidence
```

For example:

```text
server/src/protocol/message.rs
```

A file-oriented system may conclude:

```text
server changed
-> run server tests
```

But the real impact may include:

```text
server protocol
websocket compatibility
web client decoding
SDK serialization
recorded protocol fixtures
```

Likewise, a one-line change to a root lockfile may affect the entire workspace, while a documentation-only change may require documentation validation but no runtime proof.

The verification problem is therefore not "which files changed?"

It is:

```text
What behavior may have changed?
What evidence is required to prove it still works?
```

---

## 3. Why This Problem Exists

### 3.1 Repository topology and behavioral topology are different

Repositories are organized around implementation structures:

```text
directories
packages
crates
modules
files
```

Verification requirements are organized around behavioral and operational structures:

```text
public API
protocol
UI
storage
deployment
authentication
runtime lifecycle
model-visible behavior
platform compatibility
```

A single behavioral surface may span multiple packages:

```text
WebSocket Contract
├── server protocol types
├── web client codec
├── SDK bindings
└── integration fixtures
```

A single package may also contain multiple unrelated surfaces.

Package-level change detection is useful, but it is not sufficient as the final abstraction.

### 3.2 Full validation is safe but expensive

The simplest safe policy is:

```text
Every change
-> Run every check
```

As repositories grow, the complete matrix may include:

- multiple languages;
- multiple operating systems;
- browser tests;
- native applications;
- integration environments;
- snapshot suites;
- container builds;
- release artifact validation;
- external-provider tests.

The cost of full local validation quickly becomes disproportionate to many changes.

This creates pressure to skip checks manually, which makes validation inconsistent.

### 3.3 Path filters optimize cost but encode weak semantics

CI systems often evolve toward:

```text
if src/web/** changed:
    run web tests

if apps/ios/** changed:
    run iOS tests
```

This is useful, but large repositories eventually discover cross-cutting relationships such as:

```text
shared protocol source
-> Node
-> iOS
-> Android
```

or:

```text
package manifest
-> installation
-> packaging
-> platform smoke tests
```

At that point, the routing system is already expressing architectural impact, but usually through a growing body of path-specific conditions or regular expressions.

The problem is not path rules themselves.

The problem is treating path rules as the architecture rather than as inputs to an explicit impact model.

### 3.4 Prompt-only validation is not authoritative

Repositories increasingly document validation rules in:

```text
AGENTS.md
SKILL.md
CONTRIBUTING.md
```

For example:

```text
Protocol change -> contract test
UI change -> snapshot
Model-visible change -> transcript evidence
```

These instructions are valuable because they help an agent reason about the repository.

But they are not deterministic enforcement.

Two agents may interpret the same change differently, miss a cross-package consumer, choose a wrong comparison base, or select insufficient evidence.

Human-readable instructions should guide **how to work**.

They should not be the only authority deciding **what proof is mandatory**.

---

## 4. Fundamental Model

The proposed abstraction is:

```text
ChangeSet
    ↓
Affected Surfaces
    ↓
Required Evidence
    ↓
Execution Plan
```

Equivalently:

```text
Repository Change
-> Impact Resolution
-> Proof Resolution
```

This can be viewed as a repository-level compiler.

A conventional compiler performs:

```text
Source
-> Semantic Analysis
-> Dependency Resolution
-> Executable Artifact
```

A Change-to-Evidence planner performs:

```text
Diff
-> Impact Analysis
-> Evidence Resolution
-> Proof Plan
```

Its output is a structured answer to:

> What must be proven before this change can be considered sufficiently validated?

---

## 5. ChangeSet

The first abstraction is `ChangeSet`.

Conceptually:

```text
ChangeSet {
    base
    head
    mergeBase

    committedChanges
    stagedChanges
    unstagedChanges
    untrackedChanges
}
```

Future versions may derive additional facts such as:

```text
packages
dependencyChanges
configurationChanges
generatedArtifacts
symbols
schemas
```

The foundational input remains explicit repository state.

### 5.1 The comparison base is part of the contract

A planner must not silently assume every change is relative to `main`.

Real workflows include:

```text
feature -> main
feature -> staging
feature-B -> feature-A
stacked PRs
release branches
environment branches
```

If every feature branch is compared to `main`, parent changes repeatedly re-enter the child scope and local gates rerun irrelevant evidence.

Therefore:

> The comparison base must be explicit or reliably resolved by repository-owned policy.

If the correct base cannot be established, the planner should fail or widen verification scope rather than silently guess.

---

## 6. Affected Surface

The key abstraction is the **Surface**.

A surface is:

> A semantically meaningful area whose correctness can be independently reasoned about and evidenced.

Examples:

```text
websocket-contract
terminal-ui
session-lifecycle
authentication
public-api
database-schema
deployment
model-context
tool-schema
cli
installation
release-artifact
```

A surface is intentionally different from:

```text
directory
package
crate
file
```

Those are signals used to resolve impact.

They are not the behavioral impact itself.

Instead of directly coupling files to tests:

```text
file
-> check
```

the model becomes:

```text
file
-> surface
-> evidence
```

This allows repository layout and verification architecture to evolve independently.

---

## 7. Evidence

Evidence is proof that a relevant invariant still holds.

Examples include:

```text
compiler success
lint success
unit test
integration test
contract test
snapshot
recorded transcript
browser flow
installation smoke
migration test
platform test
release artifact validation
```

Evidence should describe what is proven, not only which command happens to execute it.

For example:

```text
Evidence:
    websocket-contract
```

may currently be executed by:

```text
scripts/check-websocket-contract.sh
```

The script is an implementation detail.

The evidence concept remains:

```text
client and server remain protocol-compatible
```

This distinction makes it possible to produce the same evidence differently in local development, CI, or specialized execution environments.

---

## 8. Checkpoints

A useful validation checkpoint can be expressed as:

```text
Checkpoint
=
Invariant
+ Scope
+ Evidence
+ Executor
+ Failure Feedback
```

For example:

```text
Invariant:
    Client and server protocol remain compatible.

Scope:
    websocket-contract

Evidence:
    websocket-contract-test

Executor:
    repository test script

Failure Feedback:
    protocol compatibility test output
```

This turns validation into an explicit proof obligation instead of an implicit command convention.

---

## 9. Planning and Execution Are Separate

Planning answers:

```text
What changed?
What may be affected?
What must be proven?
Why is that proof required?
```

Execution answers:

```text
How is each proof produced?
What succeeded?
What failed?
What evidence was recorded?
```

Therefore:

```text
plan != run
```

A plan should be inspectable by humans, agents, local tooling, and CI without immediately executing expensive work.

---

## 10. Explainability Is a Requirement

The planner should preserve provenance:

```text
web/src/lib/ws/channel.ts
    ↓
matched websocket-contract
    ↓
requires websocket-contract-test
```

A user or agent should be able to answer:

```text
Why is this check running?
Why did Windows become affected?
Why did this change expand to full scope?
Why was a check skipped?
```

The required chain is:

```text
Change
-> Rule
-> Surface
-> Evidence
```

Optimization logic that cannot explain itself becomes another opaque CI system.

---

## 11. Local Proof and Repository Proof

Local development and repository admission have different goals.

```text
Local proof
!=
Repository authority
```

Local development should prefer the **smallest sufficient proof** that provides fast feedback for the current change.

CI should provide **authoritative proof** appropriate for repository admission.

Conceptually:

```text
Change
      ↓
Evidence Requirements
      ↓
┌──────────────┬───────────────┐
│ Local        │ CI            │
│ fast         │ authoritative │
│ focused      │ broader       │
└──────────────┴───────────────┘
```

The two environments should share the same underlying evidence model even when their execution strategies differ.

---

## 12. Fail-Safe Scope Expansion

The planner should follow:

> Never optimize by under-proving.

Known impact can narrow proof:

```text
Known change
-> narrow proof
```

Unknown impact must widen proof:

```text
Unknown change
-> conservative proof
```

Potential full-scope triggers include:

```text
workspace configuration
root dependency manifests
lockfiles
shared toolchain configuration
planner configuration
CI infrastructure
shared generated schemas
unrecognized repository structure
```

An unresolved change must not silently produce:

```text
No affected surfaces
```

---

## 13. Determinism Boundary

The planner itself should be deterministic.

It should not rely on an LLM deciding:

```text
This file looks related to WebSocket behavior,
so perhaps these tests should run.
```

Instead:

```text
repository facts
+ declared repository knowledge
-> deterministic plan
```

AI remains useful around that planner:

```text
understand task
-> modify code
-> request plan
-> execute evidence
-> interpret failures
-> repair
-> re-plan
```

The authority boundary becomes:

> The agent decides how to repair.  
> The repository determines what must be proven.

---

## 14. Reference Design: DeepSeek Harness

DeepSeek Harness provides a strong reference for the `ChangeSet` side of the architecture.

Relevant repository locations:

- `scripts/change-scope.ts`
- `scripts/change-scope.spec.ts`
- `.agents/skills/dsh-pre-push-checks/SKILL.md`
- `.agents/skills/dsh-code-review/SKILL.md`
- `docs/testing.md`
- `.github/workflows/ci.yml`

Its `change-scope` command uses an explicit base, resolves the merge base, and records committed, staged, unstaged, and untracked changes in a structured report.

Its pre-push workflow then applies a strong principle:

> There is no universal local baseline.

Instead, each change should run the narrowest available evidence that would fail for the corresponding regression, while CI owns exhaustive coverage and platform matrices.

Conceptually, DeepSeek Harness currently resembles:

```text
Deterministic ChangeSet
        ↓
Agent semantic interpretation
        ↓
Skill-defined evidence guidance
        ↓
Focused local validation
```

### What Narness should borrow

- explicit base/head semantics;
- merge-base correctness;
- structured ChangeSet output;
- separation of committed and dirty worktree layers;
- smallest-sufficient local evidence;
- CI as broader authoritative proof.

### What Narness can generalize

Where practical:

```text
Agent-mediated impact selection
```

can evolve toward:

```text
Deterministic Surface + Evidence resolution
```

---

## 15. Reference Design: OpenClaw

OpenClaw provides the closest existing reference for automated architectural impact routing.

Relevant repository locations:

- `scripts/ci-changed-scope.mjs`
- `docs/ci/scope-and-routing.md`
- `docs/reference/test.md`
- `AGENTS.md`
- `.github/workflows/ci.yml`

Its changed-scope logic maps changed paths into architectural CI lanes such as:

```text
Node
macOS
iOS
Android
Windows
Skills
UI
installation smoke
```

The important characteristic is that these are not merely package ownership rules.

The routing captures cross-cutting relationships such as:

```text
shared source
-> multiple platform lanes
```

and:

```text
CI/planner infrastructure
-> CI routing verification
```

OpenClaw also exposes changed-scope information to developers and agents through commands such as:

```text
changed:lanes
check:changed
test:changed
```

Its repository instructions further map behavioral change categories to evidence classes, including contract proof, boundary proof, UI captures, documentation checks, and real-flow validation.

Conceptually:

```text
Changed Paths
     ↓
Repository-specific Scope Resolver
     ↓
CI Lanes
     ↓
Lane-specific Evidence
```

### What Narness should borrow

- an explicit affected-surface layer;
- cross-package impact relationships;
- machine-readable scope output;
- change-aware local validation;
- behavioral evidence categories.

### What Narness should generalize

OpenClaw necessarily contains substantial repository-specific path knowledge.

Narness should separate:

```text
Planner Engine
+
Repository-owned Surface Declarations
```

rather than embedding project-specific architecture into the planner implementation.

---

## 16. Reference Design: Codex

Codex provides a simpler but robust changed-area architecture.

Relevant repository locations:

- `AGENTS.md`
- `.github/workflows/rust-ci.yml`
- `.github/workflows/blocking-ci.yml`
- `codex-rs/skills/src/assets/samples/skill-creator/SKILL.md`

Its Rust CI detects changed areas and exposes coarse-grained values such as:

```text
codex
workflows
argument-comment-lint
```

Jobs then run conditionally from those outputs.

This provides:

```text
Changed Paths
-> Coarse Areas
-> Conditional Evidence
```

Codex also encodes many change-to-evidence relationships in `AGENTS.md`, for example:

```text
agent logic change
-> integration test

TUI-visible change
-> snapshot evidence

crate-local change
-> crate-local tests

shared/core/protocol change
-> broader test scope

dependency change
-> generated lock synchronization
```

Its blocking CI architecture adds another important pattern:

```text
dynamic internal jobs
        ↓
stable required aggregator
        ↓
repository rules
```

Branch protection depends on one stable verdict while internal CI topology can evolve.

Codex's Skill architecture also provides a strong progressive-disclosure model:

```text
name + description
        ↓
SKILL.md
        ↓
references / scripts / assets
```

### What Narness should borrow

- simple deterministic routing where sufficient;
- stable required aggregation;
- explicit change-to-evidence rules;
- progressive capability disclosure;
- incremental sophistication instead of starting with a complex semantic engine.

---

## 17. Synthesis

The three projects emphasize different parts of the same underlying problem:

```text
DeepSeek Harness
    ↓
Reliable ChangeSet
+ smallest sufficient evidence

OpenClaw
    ↓
Architectural changed-scope routing
+ behavioral evidence lanes

Codex
    ↓
Simple deterministic changed-area CI
+ stable repository authority
+ progressive capability disclosure
```

Narness can unify these ideas into:

```text
ChangeSet
    ↓
Surface Resolver
    ↓
Evidence Planner
    ↓
Execution Plan
    ↓
Executor
    ↓
Stable Repository Verdict
```

The important contribution is not another CI configuration language.

The contribution is making the relationship between:

```text
change
impact
proof
```

explicit and reusable.

---

## 18. Proposed Conceptual Architecture

```text
                  Repository
                      |
                      v
                Change Resolver
                      |
                      v
                  ChangeSet
                      |
                      v
                Scope Resolver
                      |
                      v
             Affected Surfaces
                      |
                      v
              Evidence Planner
                      |
                      v
               Required Evidence
                      |
                      v
                Execution Plan
                 /           \
                v             v
          Local Executor    CI Executor
                |             |
                v             v
            Fast Proof   Authoritative Proof
                              |
                              v
                     Stable Required Verdict
```

---

## 19. Core Domain Objects

The conceptual model currently contains five primary objects.

### ChangeSet

What changed relative to a known repository state?

### Surface

What meaningful behavioral or operational area may be affected?

### Evidence

What observation can prove the relevant invariant?

### Checkpoint

Why is the evidence required, and what invariant does it protect?

### Execution

How is the evidence produced in this environment?

Together:

```text
ChangeSet
    ↓
Surface
    ↓
Evidence
    ↓
Checkpoint
    ↓
Execution
```

These names are preliminary domain vocabulary, not finalized implementation types.

---

## 20. Example

Suppose a change contains:

```text
server/src/protocol/message.rs
web/src/lib/ws/message.ts
```

The planner may resolve:

```text
Affected Surfaces
├── websocket-contract
├── server-protocol
└── web-client
```

which requires:

```text
Evidence
├── server-compile
├── web-typecheck
├── protocol-unit
└── websocket-contract-test
```

with provenance such as:

```text
server/src/protocol/message.rs
    -> websocket-contract
    -> websocket-contract-test

web/src/lib/ws/message.ts
    -> websocket-contract
    -> websocket-contract-test

web/src/lib/ws/message.ts
    -> web-client
    -> web-typecheck
```

The planner does not need to understand the semantic implementation of the Rust or TypeScript source.

It needs reliable repository-owned knowledge that those paths participate in those surfaces.

---

## 21. Declarative Knowledge, Not a Workflow DSL

The planner will eventually require repository-specific declarations.

However, the design should avoid becoming a general workflow orchestration language.

The primary relationship should remain:

```text
repository facts
-> surfaces
-> evidence
```

Execution systems already exist:

```text
shell
package scripts
Cargo
GitHub Actions
Make
just
Bazel
task runners
```

Narness should coordinate proof obligations rather than replace every underlying build and execution tool.

---

## 22. Knowledge Ownership

Knowledge should live at the layer that owns it.

```text
Repository topology
-> repository configuration

Behavioral procedure
-> Skill

Mechanical invariant
-> deterministic script

Language rule
-> language-native tooling

Admission policy
-> CI / repository rules
```

The planner should reference existing deterministic evidence primitives where possible instead of duplicating their implementation.

---

## 23. Non-Goals

The initial design does not require:

```text
LLM semantic diff analysis
AST-level whole-repository dependency graphs
probabilistic risk scoring
automatic test generation
automatic architectural inference
arbitrary workflow orchestration
```

A useful first system can operate on:

```text
Git facts
+
path/package metadata
+
repository declarations
```

and still provide substantial value.

---

## 24. Evolution Path

### Stage 1 — ChangeSet

```text
Diff
-> structured repository changes
```

### Stage 2 — Path and Package Scope

```text
ChangeSet
-> known affected areas
```

### Stage 3 — Behavioral Surfaces

```text
Affected areas
-> semantic surfaces
```

### Stage 4 — Evidence Planning

```text
Surfaces
-> required evidence
```

### Stage 5 — Execution

```text
Evidence plan
-> local / CI execution
```

### Stage 6 — Rich Impact Analysis

Possible future inputs include:

```text
dependency graphs
schema relationships
public API changes
symbol ownership
runtime topology
observed historical failures
```

The architecture should allow richer resolvers without changing the fundamental model.

---

## 25. Design Principles

### Explicit state over guessed state

Base, head, and repository state should be known inputs.

### Behavioral surfaces over directory ownership

Paths are signals. Surfaces describe impact.

### Evidence over ritual

A command matters because of what it proves, not because it has traditionally been run.

### Deterministic obligations over model judgment

Agents may reason about implementation, but mandatory proof should be mechanically resolvable wherever practical.

### Smallest sufficient local proof

Development feedback should remain fast and relevant.

### Authoritative CI proof

Repository admission remains a server-side responsibility.

### Fail safe

Unknown impact widens proof rather than silently removing it.

### Explain every decision

Every required evidence item should have traceable provenance.

### Stable authority over dynamic topology

Internal CI jobs may change while repository protection depends on a stable aggregate verdict.

### Progressive sophistication

Repositories should be able to begin with simple path rules and evolve toward richer impact models without replacing the architecture.

---

## 26. Role in the AI Workspace

Change-to-Evidence Planning is not only a CI optimization mechanism.

Within an AI Workspace it becomes part of the agent feedback loop:

```text
Understand
    ↓
Change
    ↓
Plan Evidence
    ↓
Execute Proof
    ↓
Observe Failure
    ↓
Repair
    ↓
Re-plan
```

It gives an agent a deterministic repository authority that can answer:

```text
What did I affect?
What am I required to prove?
What proof remains missing?
Why is that proof required?
```

The intended responsibility split is:

> AI handles judgment and repair.  
> The workspace handles invariants and proof obligations.

---

## 27. Planning from actual change, not predicted change

A key refinement is that Narness should not require an agent to predict its exact file changes before implementation.

Before editing, the workspace can use task intent and repository knowledge to provide likely context and baseline guidance.

But mandatory evidence should be derived from the **actual resulting ChangeSet**.

```text
Before change:
Intent
  -> candidate Surfaces
  -> context / Skills / constraints

After change:
Actual ChangeSet
  -> affected Surfaces
  -> mandatory evidence
```

This avoids turning the agent's initial plan into repository authority.

The agent may intend to touch one package and later discover that the correct solution crosses a protocol, schema, UI, or deployment boundary.

The real diff is therefore the stronger post-change fact.

> **Plans guide work. Changes determine proof obligations.**

This creates a deliberate asymmetry:

- pre-change Surface resolution may be heuristic or model-assisted;
- post-change Surface resolution should become deterministic wherever practical.

---

## 28. Evidence Obligation vs Evidence Record

The planner currently describes required evidence. The next conceptual distinction is between an **Evidence Obligation** and an **Evidence Record**.

### Evidence Obligation

An obligation states what must be proven.

Conceptually:

```text
EvidenceObligation {
    id
    surface
    invariant
    required_level
    reason
    provenance
}
```

Example:

```text
id:
  websocket-contract

surface:
  websocket-contract

invariant:
  server and web client remain protocol-compatible

reason:
  protocol source changed
```

### Evidence Record

A record states that a specific producer actually attempted or produced the proof for a specific repository state.

Conceptually:

```text
EvidenceRecord {
    obligation_id
    producer
    scope
    change_fingerprint
    status
    started_at
    completed_at
    provenance
    artifact_refs
}
```

Possible statuses:

```text
missing
running
passed
failed
stale
unavailable
waived
```

A checklist written by the agent is not an Evidence Record.

The record should be produced by the mechanism that actually performed the proof.

> **Evidence must be observed, not self-attested.**

---

## 29. Evidence Producers

Evidence should be separated from the command or environment that produces it.

```text
Evidence Obligation
       ↓
Evidence Producer
       ↓
Evidence Record
```

A producer may be:

- a compiler;
- a linter;
- a unit-test runner;
- a contract-test script;
- a browser runner;
- a migration validator;
- a deployment smoke test;
- a CI job;
- a release verification system.

The same semantic evidence can have different producers at different lifecycle stages.

Example:

```text
Evidence:
  websocket-contract

Local producer:
  scripts/check-websocket-contract --changed

CI producer:
  scripts/check-websocket-contract --full
```

This preserves the distinction:

```text
what must be proven
!=
how it is executed here
```

It also allows local and CI workflows to share a proof model without requiring identical execution cost.

---

## 30. Evidence freshness and ChangeSet binding

A passed check is only useful if it still corresponds to the repository state being admitted.

For example:

```text
1. run protocol tests -> pass
2. modify protocol file again
3. push
```

The previous result must not silently satisfy the current obligation.

Evidence therefore needs a freshness model.

A simple conceptual binding is:

```text
Evidence Record
  -> Change Fingerprint
```

The fingerprint may eventually include some combination of:

- comparison base;
- head commit;
- relevant changed paths;
- relevant content hashes;
- Surface-specific inputs;
- tool/configuration versions;
- generated artifacts;
- environment identity where required.

The exact fingerprint strategy is an implementation research question.

The invariant is more important:

> **If facts relevant to the proof change, the proof becomes stale.**

This does not necessarily mean every repository edit invalidates every Evidence Record.

A richer future model may invalidate only evidence whose dependency inputs changed.

The progression could be:

```text
Stage 1:
any diff change -> local evidence stale

Stage 2:
Surface change -> Surface evidence stale

Stage 3:
proof dependency change -> only dependent evidence stale
```

Narness should prefer correctness before optimizing reuse.

---

## 31. Pre-push as an evidence completeness gate

A pre-push hook can become more than a script that runs a fixed test list.

Its conceptual role is:

```text
Outgoing ChangeSet
        ↓
Evidence Planner
        ↓
Required Evidence Set
        ↓
Evidence State
        ↓
Complete and fresh?
   yes /      \ no
 allow       reject
```

A useful interaction is:

```text
$ git push

Narness:
  affected surfaces:
    - websocket-contract
    - web-client

  required evidence:
    [passed] server-compile
    [passed] web-typecheck
    [missing] websocket-contract
    [stale] protocol-fixture-compatibility

  push rejected

  next actions:
    ./scripts/check-websocket-contract
    ./scripts/check-protocol-fixtures
```

The hook should not require the agent to understand every policy in advance.

It should tell the agent exactly what evidence is missing and how that evidence can be produced.

This gives a mechanical repair loop:

```text
push
  -> missing proof
  -> execute producer
  -> observe result
  -> repair if failed
  -> push again
```

This is stronger than "please remember to run the relevant tests."

---

## 32. Evidence reuse across local, CI, and release

Local evidence and repository authority should remain separate.

A local Evidence Record can improve efficiency and explainability, but local Git hooks are bypassable.

Therefore:

```text
Local Evidence
  -> useful development proof

CI Evidence
  -> authoritative repository admission proof

Release Evidence
  -> artifact / environment transition proof
```

The semantic obligation may be shared while authority differs.

Conceptually:

```text
EvidenceObligation:
  websocket-contract

records:
  local:
    passed against change X

  CI:
    passed against commit Y
    authority = repository

  release:
    not required
```

Future Narness design may allow safe evidence reuse or artifact promotion, but it should not weaken the repository authority boundary.

### Guide / Guard / Verify relationship

Change-to-Evidence is primarily the **Verify** side of the broader Harness Engineering model.

```text
Guide
  -> tell the agent which procedure is appropriate

Guard
  -> prevent known invalid actions / transitions

Verify
  -> require produced evidence for the resulting state
```

The three roles share Engineering Surfaces as a candidate semantic anchor.

For a protocol Surface:

```text
Guide:
  load protocol Skill and compatibility rules

Guard:
  prevent unsynchronized generated schema state

Verify:
  require cross-client compatibility evidence
```

This reinforces the broader Narness responsibility split:

> The agent may choose how to implement and repair. The workspace owns enforceable boundaries and proof obligations.

---

## 33. Conclusion

The underlying problem is not that repositories lack tests.

The problem is that repositories rarely have an explicit model connecting:

```text
Change
-> Impact
-> Evidence
```

DeepSeek Harness demonstrates a strong explicit ChangeSet and smallest-sufficient-proof workflow.

OpenClaw demonstrates sophisticated architectural changed-scope routing.

Codex demonstrates simple deterministic changed-area CI, progressive capability disclosure, and stable required aggregation.

Narness can synthesize these ideas into a reusable architecture:

```text
ChangeSet
-> Affected Surfaces
-> Required Evidence
-> Execution Plan
-> Authoritative Verdict
```

The goal is not merely faster CI.

The goal is repository verification that is:

```text
explicit
deterministic
explainable
composable
agent-readable
enforceable
```

This document should be treated as research input and preliminary design rationale for future planner architecture work, not as a frozen implementation contract.
