# Rust test harness engineering

## 1. Positioning

Tests are the strongest ground truth for constraining an agent's correctness (L4): lint guarantees "it isn't written badly"; tests guarantee "it does the right thing". A test harness must solve three problems, none of which prompts can solve:

1. **The agent forgets tests** — changes `src/` without a matching test.
2. **The agent writes fake coverage** — tests exist, but they don't reach the critical branches.
3. **The agent writes slow, monolithic tests** — the wrong tests run at the wrong time, dragging the edit loop.

Each sinks into an executable script + gate. The distinctive part of the Rust harness is that tests are split into **three tiers** — unit / integration / e2e — each with its own scope, its own coverage threshold, and its own trigger time. Tiering is what makes testing simultaneously *correct* (coverage has teeth) and *fast* (only the cheap tier runs often).

## 2. The three-tier test design

Rust maps the three tiers directly onto Cargo's test targets:

| Tier | Where it lives | Scope | Coverage gate | Trigger |
|---|---|---|---|---|
| Unit | `#[cfg(test)] mod tests` in `src/` | a single function/module in isolation; mocked; in-process, no I/O | **≥ 95% lines** | every push (pre-push — changed crates) |
| Integration | `tests/*.rs` (public API only) | the crate as an external consumer; module wiring across boundaries | **≥ 80% lines** | CI (full) |
| E2E | feature-gated `e2e` target | the full running system: real deps, real I/O, cross-process | **none** (scenario-driven, gap-filling) | dedicated optional workflow (always full) |

**Scope: changed vs full.** Unit and integration are *scope-aware*; e2e is not. `--scope=changed` targets only the crates changed since the last push (the crate, not the file, is the unit of change); `--scope=full` runs the whole workspace. `--coverage` (opt-in) toggles the coverage gate on. e2e has neither flag.

**Why the thresholds differ:**

- **Unit 95%** — unit tests can reach private internals, so they *should* exercise nearly every branch.
- **Integration 80%** — integration tests only reach the `pub` surface. The ~15% they can't touch (private defensive clauses, rarely-hit error branches) is exactly what unit tests own.
- **E2E none** — e2e is *gap-filling* (gap-filling): sufficiency is measured by **scenario completeness**, not line coverage.

## 3. What each tier covers (and why e2e is gap-filling)

| | Unit | Integration | E2E |
|---|---|---|---|
| Calls real DB / MQ / cache | no (mocked) | no (mocked) | yes |
| Crosses a process / service boundary | no | no | yes |
| Reaches private internals | yes | no | no |
| Verifies an external contract | no | partial | yes |
| Verifies deploy / runtime | no | no | yes |

E2E's role is **gap-filling**: it fills the gap from "the pieces work in isolation" (unit) and "the pieces work together through the public API" (integration) up to "the system actually runs end-to-end". You don't chase coverage here; you enumerate the scenarios unit + integration cannot express.

## 4. Tools: cargo test / nextest / llvm-cov

| Tool | Role | Notes |
|---|---|---|
| `cargo test` | default runner | dependency-free; `--lib` / `--tests` / `--features` select the tier |
| `cargo nextest` | faster runner | process isolation, structured output, retries; use where coverage isn't needed (e2e) |
| `cargo llvm-cov` | coverage + runner | runs tests AND measures coverage in one pass — the coverage-gate backend |

## 5. The nextest runner

### 5.1 Why nextest instead of cargo test

| Dimension | cargo test | cargo-nextest |
|---|---|---|
| Execution model | multi-threaded within the test binary | each test in its own process, in parallel |
| Speed | baseline | 2–3× faster (parallel binaries eliminate the long tail) |
| Isolation | shared process (one panic affects global state) | process isolation (one crash doesn't affect the rest) |
| Flaky handling | none | `--retries` automatic retries |
| Timeout | none (a hang stalls CI) | per-test timeout, hard kill |
| Output | wall of text | structured result table + progress + per-test duration |
| Failure localization | must parse yourself | exact location and output of each failing test |

nextest's value for a harness isn't just "speed": its **structured output** — each test's pass/fail, location, duration is machine-readable — lets a script feed failures back to the LLM precisely, instead of throwing it a wall of text.

### 5.2 Installation and basic usage

```bash
cargo install cargo-nextest
cargo nextest run                 # run tests
cargo nextest run --retries 2     # rerun only failing tests
cargo nextest run --profile ci    # specify a profile
```

Note: nextest does not run doctests; run `cargo test --doc` separately.

### 5.3 nextest.toml configuration

Config file: `.config/nextest.toml`.

```toml
[profile.ci]
retries = 2
fail-fast = true
failure-output = "immediate-final"
slow-timeout = { period = "60s", terminate-after = 2 }

[profile.ci.junit]
path = "target/nextest/ci/junit.xml"
```

Key point: `failure-output = "immediate"` prints failures as they happen — a prerequisite for feeding the LLM. The sooner the failure appears, the sooner the agent sees it.

### 5.4 Integrating with the harness

Wrap nextest in a single-responsibility script that writes failures to stderr and exits non-zero:

```bash
#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
cargo nextest run
```

## 6. Coverage with llvm-cov

### 6.1 Why coverage is needed

The "existence" of tests doesn't equal "coverage". An agent may write tests that don't cover the critical branches. Coverage is the **ground truth of test quality**, turning the soft constraint "tests were written" into the hard constraint "coverage ≥ threshold".

### 6.2 Installation and usage

```bash
cargo install cargo-llvm-cov
cargo llvm-cov                    # run tests and produce coverage
cargo llvm-cov --html             # HTML report at target/llvm-cov/html/index.html
cargo llvm-cov --lcov --output-path lcov.info   # for Codecov / VS Code Coverage Gutters
```

`cargo llvm-cov --lib` / `--tests` mirror `cargo test`'s target selection. Because llvm-cov runs the tests *and* measures coverage in the same pass, a tier's coverage gate is a single invocation — you never run the suite twice.

### 6.3 Coverage thresholds as a gate (per tier)

| Tier | Gate | Why |
|---|---|---|
| Unit | `cargo llvm-cov --lib --fail-under-lines 95` | unit reaches private internals, so it should cover nearly every branch |
| Integration | `cargo llvm-cov --tests --fail-under-lines 80` | integration only reaches the pub surface; the ~15% it can't touch is what unit owns |
| E2E | `cargo test --features e2e` (no threshold) | e2e is gap-filling: scenario-driven, not line-driven |

Add `--fail-under-regions` / `--fail-under-functions` as secondary axes:

```bash
cargo llvm-cov --lib --fail-under-lines 95 --fail-under-regions 95
```

Or write `.llvm-cov.toml`:

```toml
fail-under-lines = 95
fail-under-regions = 95
```

Below threshold → non-zero exit → the script feeds "coverage 93% < 95%, `foo::bar` uncovered" back to the LLM, forcing it to add tests.

## 7. Design: one single-responsibility script per tier

Each tier is its own gate script, so each can be placed at a different trigger. Two flags sit on top of the tiering:

- `narness-rust-test-unit.sh` — unit gate (run + `--coverage` for ≥95%), pre-push `--scope=changed`
- `narness-rust-test-integration.sh` — integration gate (run + `--coverage` for ≥80%), CI `--scope=full`
- `narness-rust-test-e2e.sh` — e2e gate (run only, no coverage, always full), dedicated optional workflow
- `narness-rust-test-discipline.sh` — "a changed .rs must have a test" (a different question, unchanged)

Coverage is a *flag* (`--coverage`) on each tier gate, not a separate script: llvm-cov runs tests + coverage in one pass, so a separate coverage script would re-run the suite. Single-responsibility splits by *tier and checkpoint*; within one tier, "does it pass" and "is it covered enough" are answered by the same tool call.

```bash
#!/usr/bin/env bash
# narness-rust-test-unit.sh — unit gate
set -euo pipefail
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
cargo llvm-cov --lib --fail-under-lines 95
```

## 8. Test efficiency: why tiering is fast

1. **Only the cheap tier runs often** — unit tests are in-process and fast, so they run on every push; integration and e2e move to CI.
2. **Tier isolation** — `--lib` / `--tests` / `--features e2e` select disjoint target sets, so one tier never compiles or runs another.
3. **Coverage only where it's cheap** — the 95% unit gate is affordable because the unit surface is small.
4. **One pass, not two** — llvm-cov runs tests + coverage together.
5. **nextest for the coverage-free tier** — e2e (no coverage) can use `cargo nextest run` for parallel, process-isolated, retrying execution.

## 9. Layered triggering

| Timing | Trigger | What runs | Purpose |
|---|---|---|---|
| After edit (L3 hook) | PostToolUse | `cargo check` (compile only) | immediate compile-error feedback |
| **Every push** | git pre-push | `narness-rust-test-unit.sh --scope=changed` (run-only) | fast logic gate on the changed crates |
| CI | CI pipeline | `clippy --scope=full` + `test-unit --scope=full --coverage` + `test-integration --scope=full --coverage` | full coverage + system-level regression (required merge gate) |
| Dedicated e2e workflow | CI pipeline (optional) | e2e only (always full) | gap-filling scenarios, on demand / nightly — not a merge blocker |

### Changed vs full scope

`--scope=changed` computes the set of crates changed since the last push — committed-ahead + staged + unstaged + untracked, mapped to their owning workspace member — and runs only those (`-p <crate>`). The unit of change is the **crate**. `--scope=full` runs `--workspace`.

The mapping is **fail-safe**: if the changed set can't be determined or a workspace-level file changed (`Cargo.lock`, root `Cargo.toml`, `rust-toolchain.toml`), it silently runs full rather than skip a crate. A gate must never under-check.

### e2e: a dedicated, optional workflow

e2e is **optional**, not part of the required CI gate. It runs always-full in its **own** workflow — triggered on demand (`workflow_dispatch`), on a schedule (nightly), or on release — never as a merge blocker.

```yaml
# .github/workflows/e2e.yml — dedicated, optional e2e workflow
name: e2e
on:
  workflow_dispatch:          # manual
  schedule:
    - cron: '17 3 * * *'      # nightly
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash plugins/narness/scripts/narness-rust-test-e2e.sh
```

The hook stage runs only `check` (compile), not tests: full tests are slow. Unit tests are fast enough for pre-push; integration/e2e are not.

## 10. Test discipline: a changed .rs must have a test

`narness-rust-test-discipline.sh`'s decision logic:

1. `git diff --name-only HEAD` + `git ls-files --others` collect changed `.rs` files
2. exclude test directories (`tests/`, `benches/`, `examples/`, `*_test.rs`), keep only non-test source files
3. for each `src/foo/bar.rs`, find a matching test: `tests/foo/bar.rs` / `tests/foo/bar_test.rs` / `src/foo/bar_test.rs`
4. not found → "changed but has no test" → exit 1

So "changing source must come with a test" turns from a prompt into a deterministic check — the *existence* gate, answering "test exists", not "test passes".

## 11. Feeding failures back to the LLM

Failure info should answer three questions (not just "it failed"):

1. **Where**: file:line + test name
2. **Why**: assertion expected vs actual, or a coverage gap
3. **How to fix**: next-step suggestion ("add a unit test for `foo::bar`", "coverage 93% < 95%")

nextest's structured output and llvm-cov's uncovered-line report satisfy the first two; the hook layer writes the failure to stderr + exit 2.

## 12. Sink path

```
L0 prompt "remember to write tests"
  → L4 narness-rust-test-unit.sh (unit pass, pre-push --scope=changed)
  → L4 narness-rust-test-integration.sh (integration pass + ≥80% coverage, CI)
  → L4 narness-rust-test-e2e.sh (e2e scenarios, dedicated optional workflow)
  → L4 narness-rust-test-discipline.sh (changed source must have a test)
  → CI gate (end state)
```

## 13. Script mapping

| Script | Command | Coverage | Trigger |
|---|---|---|---|
| `narness-rust-test-unit.sh --scope=changed` | `cargo test -p <crates…> --lib` | none (run-only) | pre-push |
| `narness-rust-test-unit.sh --scope=full --coverage` | `cargo llvm-cov --workspace --lib --fail-under-lines 95` | ≥95% | CI |
| `narness-rust-test-integration.sh --scope=full --coverage` | `cargo llvm-cov --workspace --tests --fail-under-lines 80` | ≥80% | CI |
| `narness-rust-test-e2e.sh` | `cargo test --features e2e` | none (gap-filling, always full) | dedicated optional workflow |
| `narness-rust-test.sh` | `cargo test --workspace` | none | local |
| `narness-rust-test-discipline.sh` | git diff → find test file | — | pre-commit |
| `narness-rust-changed-packages.sh` | git diff → cargo metadata → `-p <crate>` | — | (helper) |
