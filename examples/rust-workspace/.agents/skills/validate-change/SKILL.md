---
name: validate-change
description: "Select and run the smallest sufficient proof for a Rust behavior change in this example. Use after modifying src/, tests/, or Cargo.toml and before claiming the change is complete."
---

# Validate Change

Use this capability after a Rust implementation change.

## Workflow

1. Inspect the changed files and identify the behavioral surface.
2. Read [references/evidence.md](references/evidence.md) to select the required proof.
3. Run the cheapest relevant proof first.
4. Fix failures before expanding the proof.
5. Before completion, run all evidence required for the changed surface.
6. Report what ran and what was intentionally not required.

## Commands inside this repository

From `examples/rust-workspace`:

```bash
bash ../../plugins/narness/scripts/narness-rust-fmt.sh .
bash ../../plugins/narness/scripts/narness-rust-check.sh .
cargo test --lib
cargo test --test public_contract
```

Do not automatically run integration evidence when only documentation changed. Do not skip integration evidence when the public routing behavior changed.

## Completion rule

The goal is the **smallest sufficient proof locally**. CI remains the authoritative gate.
