# Rust test harness engineering (test)

## 1. Positioning

Tests are the strongest ground truth for constraining an agent's correctness (L4): lint guarantees "it isn't written badly"; tests guarantee "it does the right thing". A test harness must solve three problems, none of which prompts can solve:

1. **The agent forgets tests** — changes `src/` without a matching test.
2. **The agent writes fake coverage** — tests exist, but they don't reach the critical branches.
3. **The agent writes slow, monolithic tests** — the wrong tests run at the wrong time, dragging the edit loop.

Each sinks into an executable script + gate. The distinctive part of the Rust harness is that tests are split into **three tiers** — unit / integration / e2e — each with its own scope, its own coverage threshold, and its own trigger time. Tiering is what makes testing simultaneously *correct* (coverage has teeth) and *fast* (only the cheap tier runs often).

## 2. The three-tier test design

Rust maps the three tiers directly onto Cargo's test targets:

| Tier | Where it lives | Scope (what it tests) | Coverage gate | Trigger |
|---|---|---|---|---|
| Unit | `#[cfg(test)] mod tests` in `src/` | a single function/module in isolation; everything external is mocked/doubled; pure in-process, no I/O | **≥ 95% lines** | every push (pre-push) |
| Integration | `tests/*.rs` (public API only) | the crate as an external consumer; module wiring across boundaries | **≥ 80% lines** | CI |
| E2E | feature-gated `e2e` target | the full running system: real/containerized deps, real I/O, cross-process flows | **none** (scenario-driven, 补位) | CI (slow stage) |

**Why the thresholds differ:**

- **Unit 95%** — unit tests can reach private internals, so they *should* exercise nearly every branch. A high bar here catches logic bugs cheaply and early.
- **Integration 80%** — integration tests only reach the `pub` surface. The ~15% they can't touch (private defensive clauses, rarely-hit error branches) is exactly what unit tests own. Demanding 95% from integration would force it to test private code it cannot see.
- **E2E none** — e2e is *补位* (gap-filling): it covers what unit + integration structurally cannot — real external contracts, deployment, cross-process behavior. Its sufficiency is measured by **scenario completeness**, not line coverage, so a line threshold is meaningless (a single happy-path e2e can already light up most lines while missing whole scenarios).

## 3. What each tier covers (and why e2e is 补位)

| | Unit | Integration | E2E |
|---|---|---|---|
| Calls real DB / MQ / cache | no (mocked) | no (mocked) | yes |
| Crosses a process / service boundary | no | no | yes |
| Reaches private internals | yes | no | no |
| Verifies an external contract (wire format, timeout, retry) | no | partial | yes |
| Verifies deploy / runtime (config, startup, health) | no | no | yes |

E2E's role is **补位**: it fills the gap from "the pieces work in isolation" (unit) and "the pieces work together through the public API" (integration) up to "the system actually runs end-to-end". You don't chase coverage here; you enumerate the scenarios unit + integration cannot express.

## 4. Tools: cargo test / nextest / llvm-cov

| Tool | Role | Notes |
|---|---|---|
| `cargo test` | default runner | dependency-free; `--lib` / `--tests` / `--features` select the tier |
| `cargo nextest` | faster runner | process isolation, structured output, retries; use where coverage isn't needed (e2e) |
| `cargo llvm-cov` | coverage + runner | runs tests AND measures coverage in one pass — the coverage-gate backend |

`cargo llvm-cov --lib` / `--tests` mirror `cargo test`'s target selection. Because llvm-cov runs the tests *and* measures coverage in the same pass, a tier's coverage gate is a single invocation — you never run the suite twice.

For the full nextest / llvm-cov design see `docs/reference/rust-test-harness.md`.

## 5. Design: one single-responsibility script per tier

Each tier is its own gate script, so each can be placed at a different trigger:

- `narness-rust-test-unit.sh` — unit gate (run + ≥95% coverage), push
- `narness-rust-test-integration.sh` — integration gate (run + ≥80% coverage), CI
- `narness-rust-test-e2e.sh` — e2e gate (run only, no coverage), CI
- `narness-rust-test-discipline.sh` — "a changed .rs must have a test" (a different question, unchanged)

Coverage is a *flag* on each tier gate, not a separate script: llvm-cov runs tests + coverage in one pass, so a separate coverage script would re-run the suite (wasted time). Single-responsibility splits by *tier and checkpoint*; within one tier, "does it pass" and "is it covered enough" are answered by the same tool call.

```bash
#!/usr/bin/env bash
# narness-rust-test-unit.sh — unit gate
set -euo pipefail
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
cargo llvm-cov --lib --fail-under-lines 95
```

## 6. Coverage thresholds: from "tested" to "tested enough", per tier

The existence of tests ≠ coverage. `--fail-under-lines N` makes coverage a hard gate per tier:

| Tier | Gate | Meaning |
|---|---|---|
| Unit | `cargo llvm-cov --lib --fail-under-lines 95` | unit tests must cover ≥95% of lib lines |
| Integration | `cargo llvm-cov --tests --fail-under-lines 80` | integration tests must cover ≥80% of lib lines |
| E2E | `cargo test --features e2e` (no threshold) | scenario completeness, not line coverage |

Below threshold → non-zero exit → the script feeds "coverage 93% < 95%, `foo::bar` uncovered" back to the LLM, forcing it to add tests. Add `--fail-under-regions` / `--fail-under-functions` as secondary axes if you also want to pin branch/function coverage.

## 7. Test efficiency: why tiering is fast

The three tiers are an *efficiency* design, not just a coverage design:

1. **Only the cheap tier runs often** — unit tests are in-process and fast, so they run on every push; integration and e2e (slower, need deps) move to CI. The push path stays seconds, not minutes.
2. **Tier isolation** — `--lib` / `--tests` / `--features e2e` select disjoint target sets, so one tier never compiles or runs another.
3. **Coverage only where it's cheap** — the 95% unit gate is affordable because the unit surface is small; the heavy tiers are measured in CI, and e2e is never measured.
4. **One pass, not two** — llvm-cov runs tests + coverage together; a separate coverage script would double the run time.
5. **nextest for the coverage-free tier** — e2e (no coverage) can use `cargo nextest run` for parallel, process-isolated, retrying execution.

## 8. Layered triggering

| Timing | Trigger | What runs | Purpose |
|---|---|---|---|
| After edit (L3 hook) | PostToolUse | `cargo check` (compile only) | immediate compile-error feedback |
| **Every push** | git pre-push | `narness-rust-test-unit.sh` (unit + ≥95% cov) | fast logic gate before code leaves the machine |
| CI | CI pipeline | integration (≥80% cov) + e2e (补位) as separate jobs | full coverage + system-level regression |
| CI (slow stage) | CI pipeline | e2e only | the slowest, dep-heavy scenarios last |

The hook stage runs only `check` (compile), not tests: full tests are slow, and running them on every edit drags the edit loop. Unit tests are fast enough for pre-push; integration/e2e are not. This is the "fast hook + composable scripts" layering, applied to the test tiers.

## 9. Test discipline: a changed .rs must have a test

This is Narness's distinctive constraint. `narness-rust-test-discipline.sh`'s decision logic:

1. `git diff --name-only HEAD` + `git ls-files --others` collect changed `.rs` files
2. exclude test directories (`tests/`, `benches/`, `examples/`, `*_test.rs`), keep only **non-test source files**
3. for each `src/foo/bar.rs`, find a matching test: `tests/foo/bar.rs` / `tests/foo/bar_test.rs` / `src/foo/bar_test.rs`
4. not found → that file "changed but has no test" → exit 1

So "changing source must come with a test" turns from a prompt into a deterministic check. This is the *existence* gate — it answers "test exists", not "test passes" (that's the tier gates above).

## 10. Feeding failures back to the LLM

Failure info should answer three questions (not just "it failed"):

1. **Where it failed**: file:line + test name
2. **Why it failed**: assertion expected vs actual, or a coverage gap
3. **How to fix**: next-step suggestion ("add a unit test for `foo::bar`", "coverage 93% < 95%")

nextest's structured output and llvm-cov's uncovered-line report naturally satisfy the first two; the hook layer writes the failure to stderr + exit 2.

## 11. Sink path

```
L0 prompt "remember to write tests"
  → L4 narness-rust-test-unit.sh (unit pass + ≥95% coverage, pre-push)
  → L4 narness-rust-test-integration.sh (integration pass + ≥80% coverage, CI)
  → L4 narness-rust-test-e2e.sh (e2e scenarios, CI)
  → L4 narness-rust-test-discipline.sh (changed source must have a test)
  → CI gate (end state, regression protection)
```

## 12. Script mapping

| Script | Command | Coverage | Trigger |
|---|---|---|---|
| `narness-rust-test-unit.sh` | `cargo llvm-cov --lib --fail-under-lines 95` | ≥95% | pre-push |
| `narness-rust-test-integration.sh` | `cargo llvm-cov --tests --fail-under-lines 80` | ≥80% | CI |
| `narness-rust-test-e2e.sh` | `cargo test --features e2e` | none (补位) | CI |
| `narness-rust-test.sh` | `cargo test` | none (dependency-free full run) | local |
| `narness-rust-test-discipline.sh` | git diff → find test file | — | pre-commit |
