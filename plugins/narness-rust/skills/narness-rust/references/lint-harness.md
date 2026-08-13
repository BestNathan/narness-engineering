# Rust lint harness engineering (clippy)

## 1. Positioning

Compiling ≠ correct. Lint catches code that "compiles but shouldn't be written" — bare `unwrap()`, `panic!`, ignored `Result`, wasteful clone. A lint harness's value is turning these "code smells" from manual-review judgment into `clippy -D warnings`'s deterministic pass/fail.

## 2. Why a lint harness is needed

Anti-patterns an agent repeatedly writes in Rust and that prompts can't cure:

- `unwrap()` / `expect()` everywhere, panicking on any error
- bare `panic!` / `todo!` / `unimplemented!` left in production code
- `Result` / `Option` `.unwrap()`ed or silently discarded
- pointless clone, simplifiable conditions, ignored `#[must_use]`

The prompt "don't use unwrap" is L0 and the agent inevitably violates it under pressure. clippy is L4/L5 and physically blocks it.

## 3. Tool: cargo clippy

`cargo clippy` is Rust's official lint tool. By default it only "warns"; add `-D warnings` to escalate warnings to "errors" (deny) and trigger a non-zero exit:

```bash
cargo clippy                 # warnings, exit 0
cargo clippy -- -D warnings  # warnings escalated to errors, non-zero exit
```

## 4. Design: narness-rust-clippy.sh single responsibility

`scripts/narness-rust-clippy.sh` does only a lint check, with `-D warnings` built in:

```bash
#!/usr/bin/env bash
# Do only a lint check (cargo clippy -D warnings)
set -euo pipefail
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
cargo clippy --all-targets --all-features -- -D warnings
```

`--all-targets --all-features` covers tests, benches, examples and all features, so "the main lib passes but test code hides an unwrap" can't slip through.

## 5. The sink semantics of -D warnings

`-D warnings` is the key step from L4 toward L5:

| Form | Level | Effect |
|---|---|---|
| verbally require "don't use unwrap" | L0 | relies on goodwill |
| `narness-rust-clippy.sh` (script runs clippy -D) | L4 | constrains only when a script is invoked |
| `#![forbid(clippy::unwrap_used)]` (source attribute) | **L5** | physically impossible to violate at compile time |

A script gate is L4 and still needs the agent/CI to invoke it; writing the lint into the source's `#![forbid(...)]` is L5, **checked on every compile** — the extra layer clippy can sink to that fmt cannot.

## 6. Configuring clippy rules

### 6.1 clippy.toml (thresholds and preferences)

The project-root `clippy.toml` holds clippy's global preferences (e.g. complexity thresholds):

```toml
# clippy.toml
cognitive-complexity-threshold = 25
too-many-arguments-threshold = 7
```

### 6.2 Crate-level attributes (warn / deny / forbid)

Fix lint levels at the top of `src/lib.rs`; three tiers, each stronger:

```rust
// warn: escalated to errors by -D warnings in CI
#![warn(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

// forbid: a hard compile error (recommended for production invariants)
#![forbid(unsafe_code)]
```

Common production-constraint lints:

| lint | forbids what |
|---|---|
| `clippy::unwrap_used` / `clippy::expect_used` | bare unwrap/expect |
| `clippy::panic` | bare panic! |
| `clippy::todo` / `clippy::unimplemented` | unfinished code entering the repo |
| `unsafe_code` (rustc lint) | unsafe blocks |
| `clippy::arithmetic_side_effects` | arithmetic that may overflow |

## 7. Division of labor with narness-rust-invariants.sh

clippy is static analysis but can't cover every convention. The two are complementary, not overlapping:

| Check | Means | Division |
|---|---|---|
| bare unwrap/panic etc. | clippy (`-D warnings`) | if a ready lint exists, use clippy |
| unsafe lacking a SAFETY comment | `narness-rust-invariants.sh` (grep) | clippy doesn't check "does the comment exist"; the script fills the gap |
| cross-file conventions (e.g. naming) | `narness-rust-invariants.sh` | clippy only handles single-file semantics |

Principle: **if a clippy lint can express it, prefer clippy** (sinks more thoroughly); only fall back to script grep for what clippy can't express.

## 8. Feeding failures back to the LLM

clippy's output naturally satisfies "localizable + actionable":

```
error: called `.unwrap()` on a `Result` value
  --> src/parser.rs:42:10
   |
42 |     let n = s.parse().unwrap();
   |             ^^^^^^^^^^^^^^^ help: use `?` to propagate the error
```

lint name + file:line + fix suggestion; the agent can change it on sight. The hook layer writes this output to stderr + exit 2; no further processing needed.

## 9. Sink path

```
L0 prompt "don't use unwrap"
  → L4 narness-rust-clippy.sh (cargo clippy -D warnings gate)
  → L5 #![forbid(clippy::unwrap_used)] (compile-time physical ban)
```

## 10. Script mapping

| Script | Command | Meaning |
|---|---|---|
| `narness-rust-clippy.sh` | `cargo clippy --all-targets --all-features -- -D warnings` | lint gate, warnings escalated to errors |
| `narness-rust-check.sh` | `cargo check` | compile check (the hard prerequisite for lint) |
| `narness-rust-invariants.sh` | grep scan | invariants clippy can't cover |
