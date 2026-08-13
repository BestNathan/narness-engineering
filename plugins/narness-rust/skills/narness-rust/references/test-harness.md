# Rust test harness engineering (test)

## 1. Positioning

Tests are the strongest ground truth for constraining an agent's correctness (L4). Lint guarantees "it isn't written badly"; tests guarantee "it does the right thing". A test harness must solve two problems: **the agent forgets tests**, and **writes tests that don't cover the critical branches**. Neither can be solved with prompts; both must sink into executable scripts + gates.

## 2. Why a test harness is needed

The two most common kinds of test failure from an agent:

1. **Forgetting**: changes `src/` without a matching test, or tests only the happy path
2. **Fake coverage**: tests exist, but the assertions don't verify the key behavior or the critical branch isn't reached

"Remember to write tests" is L0; `narness-rust-test-discipline.sh` (a changed .rs must have a test) + coverage thresholds (tested enough) are L4.

## 3. Tools: cargo test / nextest / llvm-cov

| Tool | Role | Notes |
|---|---|---|
| `cargo test` | default test runner | dependency-free; the initial scripts use it |
| `cargo nextest` | faster runner | process isolation, structured output, retries, timeouts; recommended |
| `cargo llvm-cov` | coverage | the gate that turns "tested" into "tested enough" |

For the full nextest / llvm-cov design see `docs/reference/rust-test-harness.md`.

## 4. Design: two single-responsibility scripts

test maps to two scripts, each with its own job:

- `narness-rust-test.sh` — runs tests (`cargo test`); answers only "did the tests pass"
- `narness-rust-test-discipline.sh` — test discipline (a changed .rs must have a test); answers only "does the changed source have a matching test"

```bash
#!/usr/bin/env bash
# narness-rust-test.sh — do only the tests
set -euo pipefail
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
cargo test
```

## 5. Test discipline: a changed .rs must have a test

This is Narness's distinctive constraint. `narness-rust-test-discipline.sh`'s decision logic:

1. `git diff --name-only HEAD` + `git ls-files --others` collect changed `.rs` files
2. exclude test directories (`tests/`, `benches/`, `examples/`, `*_test.rs`), keep only **non-test source files**
3. for each `src/foo/bar.rs`, find a matching test: `tests/foo/bar.rs` / `tests/foo/bar_test.rs` / `src/foo/bar_test.rs`
4. not found → that file "changed but has no test" → exit 1

So "changing source must come with a test" turns from a prompt into a deterministic check.

## 6. Layered triggering

A test harness shouldn't have a single trigger time; layer it by the constraint ladder:

| Timing | Trigger | What runs | Purpose |
|---|---|---|---|
| After edit (L3 hook) | PostToolUse | `cargo check` (compile, not full tests) | immediate compile-error feedback |
| Pre-commit (L4 script) | agent calls narness-rust-*.sh | full test + discipline + coverage | complete gate, stop accumulation |
| CI (L4/L5) | CI pipeline | full tests + coverage + JUnit | regression protection |

**The hook stage runs only check, not full tests**: full tests are slow; running them on every edit drags the edit loop. The hook does only the fastest compile check; full tests are left to pre-commit and CI — the "fast hook + composable scripts" layering.

## 7. Coverage thresholds: from "tested" to "tested enough"

The existence of tests ≠ coverage. Use `cargo llvm-cov --fail-under-lines 80 ...` to make coverage a hard gate; below threshold, non-zero exit:

```bash
cargo llvm-cov --fail-under-lines 80 --fail-under-regions 80 --fail-under-functions 75
```

Coverage turns "are the tests sufficient" from the agent's own judgment into a deterministic pass/fail: below threshold → the script feeds "coverage 78% < 80%, `foo::bar` uncovered" back to the LLM, forcing the agent to add tests.

## 8. Feeding failures back to the LLM

Failure info should answer three questions (not just "it failed"):

1. **Where it failed**: file:line + test name
2. **Why it failed**: assertion expected vs actual, coverage gap
3. **How to fix**: next-step suggestion ("add a test for `foo::bar`")

nextest's structured output naturally satisfies the first two; the hook layer writes the failure to stderr + exit 2.

## 9. Sink path

```
L0 prompt "remember to write tests"
  → L4 narness-rust-test.sh (tests pass)
  → L4 narness-rust-test-discipline.sh (changed source must have a test)
  → L4 llvm-cov threshold (tested enough)
  → CI gate (end state, regression protection)
```

## 10. Script mapping

| Script | Command / logic | Meaning |
|---|---|---|
| `narness-rust-test.sh` | `cargo test` | do the tests pass |
| `narness-rust-test-discipline.sh` | git diff + find test file | does the changed source have a test |
