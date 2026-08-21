# The constraint ladder

## 1. Model overview

| Level | Name | Essence | Strength | Failure consequence |
|---|---|---|---|---|
| L0 | Prompts | natural-language instructions | weakest | the agent may simply ignore it |
| L1 | Project conventions | CLAUDE.md / AGENTS.md | weak | relies on the agent reading them voluntarily |
| L2 | Skill | workflow that can be invoked on demand | weak-medium | the agent may not invoke it |
| L3 | Hook | event-driven enforced script | medium-strong | runs automatically; failure is fed back |
| L4 | Script validation | cargo check/test/clippy | strong | deterministic pass/fail |
| L5 | Compile-time | the language and type system | strongest | violating it won't compile |

## 2. Layer details

### L0 Prompts

- What it can constrain: expressing intent, directional suggestions
- What it misses: anything that must be "always obeyed"
- When to use: always as a starting point, never as the endpoint

### L1 Project conventions (CLAUDE.md)

- What it can constrain: project background, conventions, habits
- What it misses: depends on the agent reading and obeying voluntarily
- When to use: to write "background" and "why", not "must"

### L2 Skill

- What it can constrain: step-by-step guidance for complex workflows
- What it misses: the agent may not trigger the skill
- When to use: to capture "how to do it" as a reusable workflow

### L3 Hook

- What it can constrain: automatic checks at event time
- What it misses: covers only the triggered events, not proactive decisions
- When to use: immediate validation after a change, immediate failure feedback

### L4 Script validation

- What it can constrain: independently verifiable deterministic rules
- What it misses: needs the agent/CI to invoke it
- When to use: compile, test, format, invariants

### L5 Compile-time

- What it can constrain: constraints that are physically impossible to violate at the language level
- What it misses: only what the type system can express
- When to use: any invariant expressible with types

## 3. Core proposition

The higher the level, the more it depends on the agent's goodwill; the lower the level, the more it guarantees long-running correctness. The goal: **sink constraints from L0–L2 down to L3–L5.**
