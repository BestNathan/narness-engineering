# Topics

Topics are long-lived research and design spaces within Narness.

They exist for questions that are important to AI Workspace Engineering or Harness Engineering but are still evolving. A topic may accumulate research notes, reference implementations, competing designs, experiments, and design decisions over time.

Stable project contracts should not remain buried inside topics. Once a topic reaches a durable conclusion, the relevant parts should graduate into the canonical architecture, adoption guides, Skills, deterministic scripts, or implementation code.

## Topic model

A topic is organized as a directory:

```text
docs/topics/<topic-name>/
├── README.md
├── research/
├── design/
├── references/
└── decisions/
```

Only `README.md` is required. Additional directories should be created when the topic actually needs them.

The topic README acts as the map:

- why the topic matters;
- the problem being investigated;
- current working model;
- open questions;
- related canonical documents;
- research and reference material;
- decisions that have graduated into the project architecture.

## Topic lifecycle

```text
Research
   ↓
Working Model
   ↓
Proposed Architecture
   ↓
Validated Design
   ↓
Graduated Project Contract
```

Topics do not need to move through these stages linearly. They may remain open research areas for a long time.

## Current topics

| Topic | Purpose | Status |
|---|---|---|
| [AI Workspace](ai-workspace/README.md) | The repository as an execution environment for AI agents: context, capabilities, constraints, evidence, and lifecycle orchestration. | Active |
| [Harness Engineering](harness-engineering/README.md) | How agent behavior is shaped and made reliable through instructions, Skills, hooks, deterministic checks, Git gates, CI, and repository authority. | Active |
| [Engineering Surfaces](engineering-surfaces/README.md) | The semantic model connecting intent, context, constraints, change impact, and evidence. | Active research |
| [Agent-Native Repository Architecture](agent-native-repository-architecture/README.md) | How repository structure and projections should evolve for agent-first consumability with human-auditable fallback. | Active research |
| [Change-to-Evidence Planning](change-to-evidence-planning/README.md) | How repository changes are mapped to affected Surfaces, evidence obligations, produced evidence records, and authoritative proof. | Research / preliminary design |

## Candidate future topics

These are useful boundaries for future research, but should become directories only when substantial material exists:

- Agent Context and Progressive Disclosure
- Skills and Capability Architecture
- Constraint Sinking and Enforcement
- Evidence Architecture
- Repository Lifecycle and Quality Gates
- Agent Observability and Trace Evidence
- Workspace Deployment and Environment Contracts

## Relationship to canonical documentation

```text
Topics
  ↓ research / discussion / competing designs

docs/architecture.md
  ↓ accepted architecture

docs/adoption.md
  ↓ adoption workflow

plugins/narness/skills/
  ↓ operational agent procedures

scripts/ + CI
  ↓ deterministic enforcement
```

This separation lets Narness preserve the reasoning behind its architecture without making exploratory work look like a frozen product contract.
