# Rust test harness engineering

## 1. Positioning

Tests are the strongest ground truth for constraining an AI agent's correctness (constraint ladder L4). This document explains how to build a Rust test harness with **cargo-nextest** + **cargo-llvm-cov** — one that doesn't just "run tests", but **feeds test failures back to the LLM in a structured, actionable way**, so the agent discovers problems and fixes them itself.

Core proposition: test constraints should not stay at the level of prompts ("remember to write tests"), but sink into an executable harness (scripts + hooks + threshold gates).

## 2. Test runner: nextest

### 2.1 Why nextest instead of cargo test

| Dimension | cargo test | cargo-nextest |
|---|---|---|
| Execution model | multi-threaded within the test binary | each test in its own process, in parallel |
| Speed | baseline | 2–3× faster (parallel binaries eliminate the long tail) |
| Isolation | shared process (one panic affects global state) | process isolation (one crash doesn't affect the rest) |
| Flaky handling | none | `--retries` automatic retries |
| Timeout | none (a hang stalls CI) | per-test timeout, hard kill |
| Output | wall of text | structured result table + progress + per-test duration |
| Failure localization | must parse yourself | exact location and output of each failing test |

**Narness view**: nextest's value isn't just "speed". Its key meaning for a harness is **structured output** — each test's pass/fail, location, and duration are machine-readable, which lets a script feed failures back to the LLM precisely and concisely, instead of throwing it a wall of text.

### 2.2 Installation and basic usage

```bash
cargo install cargo-nextest

# run tests
cargo nextest run

# rerun only failing tests (retry flaky)
cargo nextest run --retries 2

# specify a profile
cargo nextest run --profile ci
```

Note: nextest does not run doctests; run `cargo test --doc` separately.

### 2.3 nextest.toml configuration

Config file: `.config/nextest.toml`.

```toml
[profile.default]
retries = 0
fail-fast = false
failure-output = "immediate"   # print failures immediately (not after the whole run)

[profile.ci]
retries = 2
fail-fast = true
failure-output = "immediate-final"
slow-timeout = { period = "60s", terminate-after = 2 }

# emit JUnit XML for CI consumption
[profile.ci.junit]
path = "target/nextest/ci/junit.xml"
```

Key point: `failure-output = "immediate"` prints failures as they happen — a prerequisite for feeding the LLM. The sooner the failure appears, the sooner the agent sees it.

### 2.4 Integrating with the harness

Wrap nextest in a single-responsibility script that writes failures to stderr and exits 1:

```bash
#!/usr/bin/env bash
# Do one thing: run tests with nextest
set -euo pipefail
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
cargo nextest run
```

## 3. Coverage: llvm-cov

### 3.1 Why coverage is needed

The "existence" of tests doesn't equal "coverage". An agent may have written tests that don't cover the critical branches. Coverage is the **ground truth of test quality**, turning the soft constraint "tests were written" into the hard constraint "coverage ≥ threshold".

### 3.2 Installation and usage

```bash
cargo install cargo-llvm-cov

# run tests and produce coverage
cargo llvm-cov

# generate an HTML report (line-by-line highlighting of uncovered code)
cargo llvm-cov --html
# report at target/llvm-cov/html/index.html

# emit lcov (for Codecov / VS Code Coverage Gutters)
cargo llvm-cov --lcov --output-path lcov.info
```

### 3.3 Coverage thresholds as a gate (per tier)

Coverage is a hard gate, but the threshold depends on the test tier — the three tiers measure different things, so they have different bars:

| Tier | Gate | Why |
|---|---|---|
| Unit | `cargo llvm-cov --lib --fail-under-lines 95` | unit reaches private internals, so it should cover nearly every branch |
| Integration | `cargo llvm-cov --tests --fail-under-lines 80` | integration only reaches the pub surface; the ~15% it can't touch is what unit owns |
| E2E | `cargo test --features e2e` (no threshold) | e2e is 补位 (gap-filling): scenario-driven, not line-driven |

Add `--fail-under-regions` / `--fail-under-functions` as secondary axes:

```bash
cargo llvm-cov --lib --fail-under-lines 95 --fail-under-regions 95
```

Or write `.llvm-cov.toml`:

```toml
fail-under-lines = 95
fail-under-regions = 95
```

**Narness view**: the value of a coverage threshold is turning "are tests sufficient" from the agent's own judgment into a **deterministic pass/fail**. Below threshold → exit non-zero → a hook/script feeds "coverage 93% < 95%, the following functions are uncovered: …" back to the LLM, forcing the agent to add tests.

## 4. When to trigger tests (layered triggering)

A test harness shouldn't have a single trigger time. Layer it by constraint ladder L3–L5:

| Timing | Trigger | What runs | Purpose |
|---|---|---|---|
| After edit (L3 hook) | PostToolUse hook | fast compile check (`cargo check`, not full tests) | immediate compile-error feedback |
| **Every push** | git pre-push | `narness-rust-test-unit.sh --scope=changed` (changed crates, run-only) | fast logic gate before code leaves the machine |
| CI | CI pipeline | `test-unit --scope=full --coverage` (≥95%) + `test-integration --scope=full --coverage` (≥80%) | full coverage + system-level regression (required gate) |
| Dedicated e2e workflow | CI pipeline (optional) | e2e (补位, always full) | full-system scenarios on demand / nightly — not a merge blocker |

**Why the hook stage runs only check, not full tests**: full tests are slow; running them on every edit drags down the edit loop and breaks the agent's flow. The hook does only the fastest compile check; full tests are left to pre-commit scripts and CI — the "fast hook + composable scripts" layering.

## 5. How to guarantee the harness can feed the LLM

This is Narness's core: a harness's value isn't "detecting failure", but **letting the LLM see the failure and fix it accordingly**. Four points:

### 5.1 Localizable output

Failure info must contain a precise location (file:line + reason) so the agent doesn't have to guess. nextest's structured output satisfies this naturally; coverage reports can point out "which lines are uncovered".

### 5.2 Clear exit-code semantics

- `0`: passed
- `1`: validation failed (script level)
- `2`: hook failed, stderr fed back to the LLM

Scripts use distinct exit codes to distinguish "passed/failed"; hooks use exit 2 to trigger feedback.

### 5.3 The hook's stderr feedback mechanism

When a PostToolUse hook exits 2, its **stderr is injected into the LLM context as a system message**. So on failure, the script must write diagnostics to stderr (not stdout), or the LLM won't see them.

```bash
# Wrong: diagnostics go to stdout; the hook feeds back stderr, so the LLM can't see them
cargo nextest run 2>&1 | tail

# Right: write diagnostics to stderr
if ! out="$(cargo nextest run 2>&1)"; then
  printf '%s\n' "$out" >&2   # stderr; the hook feeds it back to the LLM
  exit 2
fi
```

### 5.4 Actionable failure info

Failure info should answer three questions, not just "it failed":

1. **Where it failed**: filename + line + test name
2. **Why it failed**: assertion expected vs actual, compile error, coverage gap
3. **How to fix**: next-step suggestion (e.g. "coverage 78% < 80%, add tests for `foo::bar`")

## 6. Mapping to narness-rust scripts

This document's tools map to the narness-rust plugin's single-responsibility scripts:

| Script | Tool | See |
|---|---|---|
| `narness-rust-check.sh` | cargo check | §4 after-edit hook |
| `narness-rust-test-unit.sh` | cargo llvm-cov --lib --fail-under-lines 95 | §3.3 unit tier |
| `narness-rust-test-integration.sh` | cargo llvm-cov --tests --fail-under-lines 80 | §3.3 integration tier |
| `narness-rust-test-e2e.sh` | cargo test --features e2e | §3.3 e2e tier |
| `narness-rust-test.sh` | cargo test (can be swapped for nextest) | §2 full run |
| `narness-rust-clippy.sh` | cargo clippy -D warnings | compile-time constraint |
| `narness-rust-invariants.sh` | invariant scan | code standards |
| `narness-rust-test-discipline.sh` | test discipline | §4 pre-commit |

(The initial scripts use `cargo test` to stay dependency-free; `nextest` / `llvm-cov` are recommended tools documented here and can later serve as optional script backends.)
