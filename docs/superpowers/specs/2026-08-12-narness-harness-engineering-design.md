# Narness — harness engineering design doc

- Date: 2026-08-12
- Status: design direction approved (Option A: the constraint ladder as the backbone)

## 1. Overview

Narness is a "research + documentation + Claude Code tooling" project. It articulates and puts into practice an engineering philosophy:

> **When code, hooks, or scripts can constrain an AI agent's behavior, prefer them over prompts.** An AI agent will very likely not follow prompts; scripts and hooks let the agent discover that its implementation is wrong and guide it toward correct behavior, thereby guaranteeing correctness on long-running tasks.

### 1.1 Brand name

"Narness" is an **intentional brand name**, not a typo of "harness". All directories, marketplaces, skills, and doc titles use `narness` / `Narness` consistently.

### 1.2 Initial scope (pure theory)

The initial phase focuses on theory/research, docs, and the Claude Code plugin skeleton, **with no example projects** (examples to be added later). Deliverables:

1. Theory/research docs (`docs/theory/`)
2. Claude Code marketplace (outer `.claude-plugin/marketplace.json`)
3. The `narness-rust` plugin (subdirectory `plugins/narness-rust/`), containing skills / hooks / scripts
4. Project overview `README.md`

### 1.3 Explicitly excluded (YAGNI)

The following are **not** done in the initial phase:

- Example projects (a Rust exercise or benchmark library demonstrating "with vs without a harness")
- Plugins for other languages (narness-python / narness-js, etc.)
- CI integration scripts (initial scripts are designed to be callable by both agent and CI, but no concrete CI config is produced)

## 2. Core theory: the constraint ladder

This is Narness's theoretical core; all docs, skills, and scripts are organized around it.

### 2.1 Ladder model (weak to strong)

| Level | Name | Essence | Strength | Failure consequence |
|---|---|---|---|---|
| L0 | Prompts | natural-language instructions | weakest | the agent may simply ignore it, no enforcement |
| L1 | Project conventions | context-injected rules like CLAUDE.md / AGENTS.md | weak | still relies on the agent reading and obeying voluntarily |
| L2 | Skill | workflow instructions invocable on demand | weak-medium | the agent may not invoke the skill |
| L3 | Hook | event-driven enforced script | medium-strong | runs automatically; failure info fed back to the agent |
| L4 | Script validation | independent ground truth like cargo check / test / clippy | strong | deterministic pass/fail; the agent is forced to fix |
| L5 | Compile-time / type system | physical constraints at the language and type level | strongest | violating it won't compile; physically impossible to drift |

### 2.2 Core proposition

> The higher the level (L0–L2), the more it depends on the agent's "goodwill" and the more easily it fails on long-running tasks; the lower the level (L3–L5), the less it depends on the agent's volition and the more it guarantees long-running correctness. **Narness's goal is to sink as many constraints as possible from L0–L2 down to L3–L5.**

### 2.3 Ladder ↔ three harness layers

| Harness layer | Ladder level | Concrete means |
|---|---|---|
| Compile/test as ground truth | L4–L5 | `cargo check`, `cargo test`, `cargo clippy -D warnings`, trait bounds, `#![forbid(unsafe_code)]` |
| Code-standard / invariant enforcement | L4 | ban bare `unwrap()`/`expect()`, require a SAFETY comment for `unsafe`, use anyhow/thiserror instead of `panic!` |
| Test-discipline enforcement | L3–L4 | hook detects "changed a .rs with no matching test", write tests before implementation |

## 3. Repository layout

```
narness-engineering/
├── README.md                              # project overview, Narness idea at a glance
├── LICENSE                                # MIT
├── .gitignore
├── .claude-plugin/
│   └── marketplace.json                   # outer marketplace definition
├── plugins/
│   └── narness-rust/                      # plugin subdirectory
│       ├── .claude-plugin/
│       │   └── plugin.json                # plugin metadata
│       ├── skills/
│       │   └── narness-rust/
│       │       └── SKILL.md               # the narness-rust skill
│       ├── hooks/
│       │   ├── hooks.json                 # hook definition
│       │   └── scripts/                   # scripts called by the hook
│       │       └── post-edit-gate.sh      # the PostToolUse fast gate
│       └── scripts/                       # standalone validation scripts (shared by agent and CI, single responsibility)
│           ├── verify-fmt.sh              # format check
│           ├── verify-check.sh            # compile check
│           ├── verify-clippy.sh           # lint check
│           ├── verify-test.sh             # tests
│           ├── verify-invariants.sh       # invariant check
│           └── verify-test-discipline.sh  # test-discipline check
└── docs/
    ├── theory/                            # theory/research docs
    │   ├── why-not-prompts.md
    │   ├── constraint-ladder.md
    │   ├── decision-guide.md
    │   └── long-running-correctness.md
    ├── reference/                         # tool-practice references
    │   └── rust-test-harness.md           # Rust test harness (nextest + llvm-cov)
    └── superpowers/
        └── specs/                         # design docs (this doc)
```

### 3.1 Directory responsibilities

| Path | Responsibility |
|---|---|
| `.claude-plugin/marketplace.json` | defines marketplace metadata and the plugin list, pointing at `plugins/narness-rust` |
| `plugins/narness-rust/` | one plugin's complete implementation, independently installable |
| `plugins/narness-rust/skills/` | skill definitions, one directory + `SKILL.md` per skill |
| `plugins/narness-rust/hooks/` | hook config + event-triggered scripts |
| `plugins/narness-rust/scripts/` | standalone validation scripts decoupled from hooks, callable manually by the agent or reused by CI |
| `docs/theory/` | theory docs, the "research" body of the project |

## 4. Marketplace

`/Users/nathan/workspace/narness-engineering/.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-marketplace.json",
  "name": "narness",
  "version": "0.1.0",
  "description": "Narness harness engineering — constrain AI agents with code, hooks and scripts instead of prompts",
  "owner": { "name": "narness" },
  "plugins": [
    {
      "name": "narness-rust",
      "description": "Rust harness engineering skills, hooks and validation scripts",
      "version": "0.1.0",
      "source": "./plugins/narness-rust",
      "author": { "name": "narness" }
    }
  ]
}
```

Key points (verified against the official `$schema` and Anthropic's official multi-plugin marketplace):

- `source` points at the plugin's subdirectory relative to the marketplace root (the directory containing `.claude-plugin/`), and must start with `./`; `"./plugins/narness-rust"` is correct.
- Each plugin directory must carry its own `.claude-plugin/plugin.json`; Claude Code looks for that manifest at the resolved plugin root.
- The top-level `version` is the marketplace manifest version, independent of each plugin's own `version`.

## 5. The plugin: narness-rust

### 5.1 plugin.json

```json
{
  "name": "narness-rust",
  "description": "Rust harness engineering: constrain AI agents with cargo, clippy, hooks and invariant scripts instead of prompts",
  "version": "0.1.0",
  "author": { "name": "narness" },
  "license": "MIT",
  "keywords": ["rust", "harness", "hooks", "clippy", "engineering"]
}
```

### 5.2 Skills

The initial phase does **one** core skill: `narness-rust` (`plugins/narness-rust/skills/narness-rust/SKILL.md`).

**Skill responsibility**: guide the agent in applying harness engineering in Rust projects.

**SKILL.md outline**:

1. **When to use** — when establishing constraints in a Rust project, or when the agent repeatedly violates the same kind of constraint
2. **The constraint ladder's Rust mapping** — map L0–L5 to concrete Rust means (see the 2.3 table)
3. **Steps to sink a constraint** — how to escalate level by level to hook / script / compile-time when a "prompt-only constraint fails"
4. **Script usage guide** — when to call `verify-fmt.sh` / `verify-check.sh` / `verify-clippy.sh` / `verify-test.sh` / `verify-invariants.sh` / `verify-test-discipline.sh`, and how to read failure output and fix it
5. **Test discipline** — write tests first, a changed .rs must have a matching test, how to satisfy the gate

### 5.3 Hooks

`plugins/narness-rust/hooks/hooks.json` defines a `PostToolUse` hook: when the agent modifies a `.rs` file with `Edit` / `Write`, it triggers a fast-gate script; failure info is fed back to the agent for fixing.

- **Event**: `PostToolUse`
- **matcher**: `Edit|Write|MultiEdit`
- **Behavior**: `post-edit-gate.sh` is the hook entrypoint; it judges whether the change is a `.rs` file, and if so calls `verify-check.sh` for a compile check (skipping the slow full test); on failure it injects stderr into the conversation
- **Design consideration**: the hook runs only a **fast** gate (avoid running full `cargo test` on every edit, which would stall); the rest (fmt / clippy / test) is run by the agent invoking the corresponding single-responsibility script, or by CI — the "fast hook + composable scripts" layering

### 5.4 Standalone scripts (scripts/)

Scripts are the substance of "code constraint", decoupled from hooks, callable manually by the agent, callable by the hook, reusable by CI. All are parameterized (accept the project root path); in the initial phase they exist as a "reference implementation", not bound to any concrete example project. **Each script does exactly one thing (single responsibility)**, independently callable, independently verifiable, composable on demand.

| Script | Responsibility | Harness layer |
|---|---|---|
| `verify-fmt.sh` | `cargo fmt --check` | compile/test ground truth |
| `verify-check.sh` | `cargo check` | compile/test ground truth |
| `verify-clippy.sh` | `cargo clippy --all-targets --all-features -- -D warnings` | compile/test ground truth |
| `verify-test.sh` | `cargo test` | compile/test ground truth |
| `verify-invariants.sh` | scan `.rs` under `src/`: bare `unwrap()`/`expect()`, `panic!`, `unsafe` without a SAFETY comment | code standard / invariants |
| `verify-test-discipline.sh` | detect whether a recently changed `.rs` has a matching test file | test discipline |

## 6. Theory doc structure

`docs/theory/` four docs:

| Doc | Content |
|---|---|
| `why-not-prompts.md` | why not just prompts: the principle and instances of agents ignoring prompts, leading to the necessity of "code constraint > prompts" |
| `constraint-ladder.md` | the ladder model in detail: each level's capability, limitation, applicable scenario, Claude Code implementation |
| `decision-guide.md` | decision criteria (tree/checklist): when to sink a constraint from prompts into code |
| `long-running-correctness.md` | how the harness guarantees long-running correctness: the role of hooks/scripts at each stage of a long-running task |

## 7. Acceptance criteria (initial phase complete)

1. Repository layout matches section 3; `git` initialized
2. `marketplace.json` and `plugin.json` fields complete and correctly formatted (aligned with the Claude Code plugin spec)
3. The `narness-rust` skill's `SKILL.md` exists and covers the 5.2 outline
4. `hooks.json` and the six single-responsibility scripts exist and are executable, and scripts can be invoked independently
5. The four theory docs exist, with the core proposition (section 2.2) running through them
6. `README.md` briefly states the Narness idea and usage

## 8. Next steps

1. User reviews this design doc
2. Produce an implementation plan via the `writing-plans` skill
3. Implement the initial phase per the plan
