# Rust AI Workspace Example

This directory is a runnable reference for adopting Narness in a small Rust repository.

It demonstrates five parts of the AI Workspace model:

1. **Workspace Contract** — [AGENTS.md](AGENTS.md) keeps global rules and routes validation work.
2. **Capability Plane** — [validate-change](.agents/skills/validate-change/SKILL.md) is a task Skill with progressive disclosure.
3. **Constraint Plane** — the project can be checked with the single-responsibility Narness Rust scripts.
4. **Evidence Plane** — unit and integration tests prove different behavioral surfaces.
5. **Lifecycle Plane** — [.github/workflows/ci.yml](.github/workflows/ci.yml) shows a stable `required` gate.

## Run it

From the Narness repository root:

```bash
cargo test --manifest-path examples/rust-workspace/Cargo.toml

bash plugins/narness/scripts/narness-rust-fmt.sh examples/rust-workspace
bash plugins/narness/scripts/narness-rust-check.sh examples/rust-workspace
bash plugins/narness/scripts/narness-rust-test-unit.sh examples/rust-workspace --scope=full
bash plugins/narness/scripts/narness-rust-test-integration.sh examples/rust-workspace --scope=full
```

## Walk through the workspace

### Start at the contract

Read [AGENTS.md](AGENTS.md). It deliberately does not explain every testing command. It defines global invariants and routes change validation to the Skill.

### Discover the capability

The Skill metadata in [.agents/skills/validate-change/SKILL.md](.agents/skills/validate-change/SKILL.md) tells an agent when the capability applies.

The Skill points to [references/evidence.md](.agents/skills/validate-change/references/evidence.md) only when evidence selection is needed.

```text
metadata -> SKILL.md -> relevant reference -> deterministic commands
```

### Change behavior

The public function in [src/lib.rs](src/lib.rs) has both unit and integration evidence.

A private implementation change can usually be proven with unit tests. A public behavior change also requires the integration test because the public contract changed.

### Run the smallest sufficient proof

From `examples/rust-workspace`:

```bash
bash ../../plugins/narness/scripts/narness-rust-check.sh .
cargo test --lib
```

Before proposing a public behavior change:

```bash
bash ../../plugins/narness/scripts/narness-rust-fmt.sh .
bash ../../plugins/narness/scripts/narness-rust-check.sh .
cargo test --lib
cargo test --test public_contract
```

### Let CI be authoritative

The nested workflow is a copyable example for a standalone repository. It shows separate evidence jobs converging into a stable `required` status.

In a consuming repository, expose the Narness scripts at `plugins/narness/scripts/`, then copy the workflow to the repository's root `.github/workflows/` directory.

## Environment declaration

The example includes [.narness.toml](.narness.toml) to show how runtime prerequisites are declared separately from code correctness.

## What this example intentionally does not do

- It does not pretend that `narness plan` exists today.
- It does not run E2E tests for a library with no external runtime.
- It does not put every command into AGENTS.md.
- It does not create a monolithic "run all gates" script.
- It does not use CI as the only place where a check can be executed.
