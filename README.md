# Narness

Narness is an **AI Workspace Engineering** framework for making AI coding agents work inside repositories that are understandable, progressively discoverable, deterministic, and provable.

The project started from a simple harness-engineering principle:

> If a rule can be enforced by code, hooks, scripts, a compiler, Git, or CI, do not leave that rule only in a prompt.

That principle remains the Enforcement Plane of Narness. The broader goal is to design the entire repository as an execution environment for agents.

## The AI Workspace model

```text
AI Workspace
=
Context Architecture
+ Capability Architecture
+ Constraint Architecture
+ Evidence Architecture
+ Lifecycle Orchestration
```

A good workspace does not depend on an agent remembering everything. It provides the right context at the right time, exposes procedures as discoverable capabilities, turns important rules into deterministic checks, derives the proof required for a change, and blocks unproven states from authoritative history.

```text
                         AI WORKSPACE
                              |
        +---------------------+----------------------+
        |                     |                      |
  Instructions           Capabilities            Evidence
        |                     |                      |
 AGENTS / scoped        Skills / tools        Tests / checks
 Rules / approval       Scripts / assets      Snapshots / E2E
        |                     |                      |
        +---------------------+----------------------+
                              |
                         Orchestration
                              |
             Hooks -> Git hooks -> CI -> Review -> Release
                              |
                              v
                     Authoritative Repository
```

See [docs/architecture.md](docs/architecture.md) for the complete model.

## Three orthogonal axes

Narness treats an AI workspace as three independent design problems.

### Context disclosure

```text
Root instructions
  -> scoped instructions
  -> skill metadata
  -> SKILL.md
  -> task-relevant references / scripts / assets
```

The question is: **what should the agent know now?**

Root `AGENTS.md` / `CLAUDE.md` files are contracts and routers, not encyclopedias. Procedures belong in Skills. Historical design reasoning belongs in ADRs or design notes.

### Constraint sinking

```text
L0 Prompt
L1 AGENTS / convention
L2 Skill
L3 Agent hook
L4 Deterministic script
L5 Language / tool-native rule
L6 Git lifecycle gate
L7 Server-side CI / repository ruleset
```

The question is: **where should this rule be guaranteed?**

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

The question is: **when should the workspace intervene?**

Edit-time hooks should be fast and corrective. Local Git hooks should provide the smallest sufficient proof. CI is the repository authority and owns authoritative proof.

## Core concepts

| Concept | Responsibility |
|---|---|
| Workspace Contract | Global invariants, approval boundaries, project structure, and routing |
| Knowledge Plane | Separates standing rules, procedures, and design decisions |
| Capability Plane | Packages procedures as discoverable Skills with progressive disclosure |
| Enforcement Plane | Sinks rules from prompts into hooks, scripts, native rules, Git, and CI |
| Evidence Architecture | Defines what proves a change correct for its behavioral surface |
| Lifecycle Orchestration | Runs the right evidence at edit, commit, push, CI, review, and release time |

A checkpoint is not just a command:

```text
Checkpoint
=
Invariant
+ Scope
+ Evidence
+ Executor
+ Failure Feedback
```

## Repository layout

```text
.
├── README.md
├── CLAUDE.md
├── docs/
│   ├── architecture.md
│   └── adoption.md
├── examples/
│   └── rust-workspace/
├── plugins/
│   └── narness/
├── cli/
├── narness-policy/
└── scripts/
    └── narness-repo-english.sh
```

## What exists today

Narness currently ships:

- a Claude Code plugin with a `narness` Skill and progressive reference material;
- edit-time `PostToolUse` feedback for Rust compilation;
- single-responsibility Rust validation scripts;
- shared Git hook entrypoints for commit, commit-message, and push gates;
- copyable Rust tool and GitHub Actions configuration;
- a CLI that validates runtime prerequisites from `.narness.toml`;
- a policy engine prototype;
- a runnable Rust workspace example showing the AI Workspace pattern.

The current implementation is Rust-first. The architecture is language-independent.

`narness plan` is the next architectural direction, not a shipped command yet. Its proposed contract is documented in [docs/architecture.md](docs/architecture.md): change set -> affected surfaces -> required evidence -> execution plan.

## Quick start

### Install the Claude Code plugin

```bash
claude plugin marketplace add https://github.com/BestNathan/narness-engineering
claude plugin install narness
```

### Check an agent runtime environment

Declare requirements in `.narness.toml`:

```toml
[[checks]]
type = "version"
name = "node"
min = "22"

[[checks]]
type = "exists"
name = "rg"
```

Then run:

```bash
npx narness
npx narness --json
```

### Run the example

```bash
cargo test --manifest-path examples/rust-workspace/Cargo.toml

bash plugins/narness/scripts/narness-rust-fmt.sh examples/rust-workspace
bash plugins/narness/scripts/narness-rust-check.sh examples/rust-workspace
bash plugins/narness/scripts/narness-rust-test-unit.sh examples/rust-workspace --scope=full
bash plugins/narness/scripts/narness-rust-test-integration.sh examples/rust-workspace --scope=full
```

The example contains a root workspace contract, a task Skill with progressive disclosure, unit and integration evidence, an environment declaration, and a stable CI required gate.

## Adopt Narness

Start with [docs/adoption.md](docs/adoption.md):

1. write a small root Workspace Contract;
2. move task procedures into Skills;
3. express checks as single-responsibility executable primitives;
4. mount fast checks in agent and Git hooks;
5. map change surfaces to required evidence;
6. make CI the authoritative full-scope gate;
7. expose one stable required status to repository rules.

## Design rules

- Prefer deterministic enforcement over prompt-only requirements.
- Keep root instructions small and route to scoped knowledge.
- Load Skill metadata broadly, Skill instructions selectively, and supporting detail lazily.
- Keep executable validation primitives single-responsibility.
- Put validation logic in scripts or native tools; orchestration layers only decide when and at what scope to run them.
- Optimize local proof for relevance and speed; optimize CI proof for authority.
- Fail loud. A failed check must say where, why, and how to fix it.
- Keep repository-authored content in English.

## Documentation

- [AI Workspace architecture](docs/architecture.md)
- [Adoption guide](docs/adoption.md)
- [Runnable Rust example](examples/rust-workspace/README.md)
- [Narness Skill](plugins/narness/skills/narness/SKILL.md)
- [Constraint ladder](plugins/narness/skills/narness/references/constraint-ladder.md)
- [Harness checkpoints](plugins/narness/skills/narness/references/harness-checkpoints.md)
