# Rust Workspace Example Contract

## Purpose

This crate demonstrates how an AI coding workspace separates standing rules, task procedures, deterministic checks, evidence, and repository authority.

## Global invariants

- Keep the public routing behavior deterministic.
- Do not use `unwrap`, `expect`, bare `panic!`, or undocumented `unsafe` in production code.
- Add or update evidence when behavior changes.
- Keep repository-authored content in English.
- Do not weaken tests merely to make a gate pass.

## Routing

- For implementation changes, use the `validate-change` Skill in `.agents/skills/validate-change/SKILL.md`.
- For evidence selection, follow that Skill's `references/evidence.md`.
- The repository-level architecture is documented in `../../docs/architecture.md` when this example is viewed inside the Narness repository.

## Completion

A behavior change is complete when:

1. the crate compiles;
2. formatting is clean;
3. focused unit evidence passes;
4. public behavior changes have integration evidence;
5. the final diff contains no unrelated changes.

CI remains the authoritative repository gate.
