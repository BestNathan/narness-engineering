# Decision guide: when to sink a constraint

## 1. Decision tree

When you meet a rule you "hope the agent will obey", judge in this order:

```
Has the agent violated this rule once?
├── No → express it with prompts (L0/L1) for now, and observe
└── Yes → has it violated it twice or more?
    ├── No → escalate to a Skill (L2) or Hook (L3)
    └── Yes → can it be expressed as a script (L4) or at compile time (L5)?
        ├── Yes → sink it to L4/L5 (prefer compile time)
        └── No → sink it to a Hook (L3), and use a script to feed back failures
```

## 2. Rules of thumb

- A rule expressible as a `clippy` lint → go straight to `clippy -D warnings` (L5)
- An invariant expressible with the type system → use types (L5), e.g. newtype, trait bounds
- Needs "immediate feedback after a change" → use a Hook (L3)
- Needs "pre-commit / CI validation" → use a script (L4)
- Only "intent and background" remain → leave it in prompts (L0/L1)

## 3. Anti-pattern checklist

| Anti-pattern | Problem | Correct approach |
|---|---|---|
| Writing "be sure to write tests" in CLAUDE.md | soft constraint, inevitably fails long-term | narness-rust-test-discipline script + hook |
| Prompting "don't use unwrap" | the agent always forgets | clippy::unwrap_used (L5) |
| Verbally requiring "remember to format" | nobody executes it | cargo fmt --check gate (L4) |
| Writing invariants as comments | comments don't enforce | type system or assertions (L5/L4) |
