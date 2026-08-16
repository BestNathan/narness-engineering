# Rust lint harness engineering (clippy)

## 1. Positioning

Compiling ≠ correct. Lint catches code that "compiles but shouldn't be written" — bare `unwrap()`, `panic!`, ignored `Result`, wasteful clone. A lint harness's value is turning these "code smells" from manual-review judgment into `clippy -D warnings`'s deterministic pass/fail.

## 2. Why a lint harness is needed

Anti-patterns an agent repeatedly writes in Rust and that prompts can't cure:

- `unwrap()` / `expect()` everywhere, panicking on any error
- bare `panic!` / `todo!` / `unimplemented!` left in production code
- `Result` / `Option` silently discarded
- pointless clone, simplifiable conditions, ignored `#[must_use]`

The prompt "don't use unwrap" is L0 and the agent inevitably violates it under pressure. clippy is L4/L5 and physically blocks it.

## 3. Tool: cargo clippy and its lint groups

`cargo clippy` is Rust's official lint tool. Its lints are organized into **groups** with different default levels — this grouping is the raw material for the three strictness tiers:

| Group | Default level | Character |
|---|---|---|
| `correctness` | **deny** | outright bugs (wrong code) |
| `style` / `complexity` / `perf` / `suspicious` | **warn** (these four = `clippy::all`) | smells: ugly, needlessly complex, slow, dubious |
| `pedantic` | allow | opinionated "there's a better way" |
| `nursery` | allow | new, still-unstable lints |
| `restriction` | allow | ban an entire language feature |
| `cargo` | allow | lints over `Cargo.toml` |

Two escalation facts matter:

1. `cargo clippy -- -D warnings` escalates whatever is **warn** to error — so it hard-denies `clippy::all` by default.
2. But allow-by-default groups (`pedantic`, `restriction`, `nursery`, `cargo`) are **not warnings** — `-D warnings` does *not* touch them. You must explicitly opt into them first (via `#![warn(clippy::pedantic)]` or `-W clippy::pedantic`), and only then does `-D warnings` bite.

## 4. How to design a lint rule

Adding a lint is a design decision, not a paste job. The discipline, in order:

1. **Start from the observed failure, not a lint list.** The agent keeps writing `unwrap()`? That's the rule. Don't paste a curated "best clippy config" from the web (same principle as fmt's "don't paste a random `rustfmt.toml`") — a rule you didn't derive from a real failure is noise.
2. **Map the failure to an existing lint.** For almost every anti-pattern there is a clippy lint already (`clippy::unwrap_used`, `clippy::panic`, `clippy::arithmetic_side_effects`, …). Prefer the tool-native lint over a hand-rolled grep — it sinks lower (L5 vs L4).
3. **Assign it a tier by how objective it is.** Objective bug → general tier. Refinement/opinion → medium (pedantic). Feature ban (unwrap/panic/unsafe) → strictest (restriction). §5.
4. **Escalate to `deny`/`forbid`.** A `warn` lint is invisible to the agent and rots; `deny` makes it bite; `forbid` makes it un-overridable downstream.
5. **Every `allow` needs a reason.** `#[allow(clippy::x, reason = "...")]` — clippy's `allow_attributes_without_reason` enforces this, so exceptions stay visible and reviewable.
6. **Sink to the lowest level.** `-D` flag (L4 script) → `#![deny]` (L5 source) → `#![forbid]` (L5 un-overridable).

## 5. Three strictness tiers

| Tier | Enable | What it denies | When |
|---|---|---|---|
| **一般严格** (general) | `-D warnings` | `clippy::all` — correctness + style + complexity + perf + suspicious | every project's baseline |
| **中等严格** (medium) | `+ #![warn(clippy::pedantic)]` | the above + opinionated "better way" lints | libraries, shared code |
| **最严格** (strictest) | `+ #![deny]`/`#![forbid]` restriction lints | the above + entire feature bans (unwrap, panic, unsafe, arithmetic overflow) | safety- / security-critical code |

**Tier 1 — general (baseline, no source changes):**

```bash
cargo clippy --all-targets --all-features -- -D warnings
```

`narness-rust-clippy.sh` does exactly this.

**Tier 2 — medium (+ pedantic):** opt into pedantic as warnings, then let `-D warnings` escalate them, and selectively allow the ones that don't fit:

```rust
// lib.rs
#![warn(clippy::pedantic)]
#![allow(clippy::missing_errors_doc, reason = "internal APIs don't document errors")]
#![allow(clippy::module_name_repetitions, reason = "domain terms repeat intentionally")]
```

**Tier 3 — strictest (+ restriction feature bans):** each `deny`/`forbid` bans a whole feature; `forbid` cannot be overridden downstream:

```rust
// lib.rs
#![forbid(unsafe_code)]
#![deny(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
#![deny(clippy::arithmetic_side_effects)]
#![deny(clippy::indexing_slicing)]
```

The principle: **a tier is which groups you opt into + which level (`deny` vs `forbid`) you set.** You move up a tier by enabling a stricter group — you never rewrite the rules.

## 6. Design: narness-rust-clippy.sh single responsibility

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

## 7. The sink semantics of -D warnings

`-D warnings` is the key step from L4 toward L5:

| Form | Level | Effect |
|---|---|---|
| verbally require "don't use unwrap" | L0 | relies on goodwill |
| `narness-rust-clippy.sh` (script runs clippy -D) | L4 | constrains only when a script is invoked |
| `#![deny(clippy::unwrap_used)]` (source attribute) | L5 | a compile error on every build |
| `#![forbid(clippy::unwrap_used)]` (source attribute) | L5 | a compile error that can't be `allow`ed away |

A script gate is L4 and still needs the agent/CI to invoke it; writing the lint into the source is L5, checked on every compile — the extra layer clippy can sink to that fmt cannot.

## 8. Writing clippy config: clippy.toml vs lint levels

Two kinds of clippy configuration are often conflated. Keep them separate:

1. **Lint levels** (allow/warn/deny/forbid) — set in **source attributes** (`#![deny(...)]`) or **CLI flags** (`-D ...`). *Not* in `clippy.toml`.
2. **Lint parameters** (numeric thresholds, disallowed lists, msrv) — set in **`clippy.toml`**.

```toml
# clippy.toml — parameters for lints that take config (NOT allow/warn/deny)

# numeric thresholds (feed the named complexity lints)
cognitive-complexity-threshold = 25
too-many-arguments-threshold = 7
too-many-lines-threshold = 200
type-complexity-threshold = 250

# disallowed lists (feed the disallowed_* restriction lints)
disallowed-methods = [
    { path = "std::vec::Vec::set_len", reason = "unsafe: can corrupt the length" },
    { path = "std::process::Command::new", reason = "use the safe runner wrapper" },
]
disallowed-types = [
    { path = "std::sync::Mutex", reason = "use parking_lot::Mutex or tokio::sync::Mutex" },
]
disallowed-macros = [
    { path = "std::dbg", reason = "use tracing::debug instead" },
]

# toolchain context
msrv = "1.75"
```

The `disallowed-*` lists are **inert until you also enable their lint** — the list is the parameter, the level is the switch:

```rust
#![deny(clippy::disallowed_methods, clippy::disallowed_types, clippy::disallowed_macros)]
```

Point: config sets a lint's *parameter*; the level decides whether it fires as an error. Both are required.

## 9. Extending your own lint rules (the async-trait example)

clippy covers a lot, but not everything. When you have a *project-specific* rule — "don't use crate X", "every `unsafe` needs a comment", "this module must not leak type Y" — you extend the harness. The canonical example: **ban `async-trait`**.

**The rule**: `async fn` in traits is native since Rust 1.75 (the project pins 1.89.0), so pulling in the `async-trait` crate is legacy. Ban it.

**Why clippy can't do it**: `#[async_trait]` is a proc-macro *attribute*, not a type, method, or macro call — so `disallowed-types` / `disallowed-methods` / `disallowed-macros` don't reliably reach it. This is the classic "clippy can't express it" case.

**The extension ladder** (sink as low as it goes):

**Step 1 — L4 grep invariant** (deterministic catch). Add a rule to `narness-rust-invariants.sh`:

```bash
# ban async-trait: use native async fn in trait (Rust 1.75+)
matches="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -nH -E 'async_trait' {} + 2>/dev/null || true)"
if [[ -n "$matches" ]]; then
  printf '%s\n' "$matches" >&2
  echo "✗ async-trait is banned; use native async fn in trait (stabilized in Rust 1.75)" >&2
  fail=1
fi
```

**Step 2 — L5 dependency ban** (strongest; can't even compile). Remove the crate so the compiler enforces the rule: delete `async-trait` from `Cargo.toml`, or `cargo deny` bans it from the tree:

```toml
# deny.toml
[bans]
deny = ["async-trait"]
```

With the dependency gone, `use async_trait::async_trait` fails at **compile time** — the rule sinks to L5, where no script invocation is needed.

**The decision rule** for extending a custom lint:

| The ban targets… | Use | Level |
|---|---|---|
| a type / method / macro call | `clippy.toml` `disallowed-*` + `#![deny(...)]` | L5 |
| an attribute macro / cross-file rule / comment requirement | `narness-rust-invariants.sh` grep | L4 |
| "this crate must not exist at all" | remove the dependency / `cargo deny` | L5 |

## 10. Division of labor with narness-rust-invariants.sh

clippy is static analysis but can't cover every convention. The two are complementary, not overlapping:

| Check | Means | Division |
|---|---|---|
| bare unwrap/panic etc. | clippy (`-D warnings`) | if a ready lint exists, use clippy |
| unsafe lacking a SAFETY comment | `narness-rust-invariants.sh` (grep) | clippy doesn't check "does the comment exist"; the script fills the gap |
| ban a crate / attribute macro | `narness-rust-invariants.sh` (grep) or remove the dep | see §9 |

Principle: **if a clippy lint can express it, prefer clippy** (sinks more thoroughly); only fall back to script grep for what clippy can't express.

## 11. Feeding failures back to the LLM

clippy's output naturally satisfies "localizable + actionable":

```
error: called `.unwrap()` on a `Result` value
  --> src/parser.rs:42:10
   |
42 |     let n = s.parse().unwrap();
   |             ^^^^^^^^^^^^^^^ help: use `?` to propagate the error
```

lint name + file:line + fix suggestion; the agent can change it on sight. The hook layer writes this output to stderr + exit 2; no further processing needed.

## 12. Sink path

```
L0 prompt "don't use unwrap"
  → L4 narness-rust-clippy.sh (cargo clippy -D warnings gate)
  → L5 #![deny(clippy::unwrap_used)] (compile-time error)
  → L5 #![forbid(clippy::unwrap_used)] (un-overridable compile-time ban)
```

## 13. Script mapping

| Script | Command | Meaning |
|---|---|---|
| `narness-rust-clippy.sh` | `cargo clippy --all-targets --all-features -- -D warnings` | lint gate, warnings escalated to errors |
| `narness-rust-check.sh` | `cargo check` | compile check (the hard prerequisite for lint) |
| `narness-rust-invariants.sh` | grep scan | the extension point for invariants clippy can't cover (e.g. ban async-trait) |
