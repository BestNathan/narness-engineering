# Rust format harness engineering (fmt)

## 1. Positioning

Formatting is the most "mechanical" layer of the constraint ladder: it has no judgment space, only the single binary question "does it conform to rustfmt". Precisely for that reason it is also the easiest and most-deserving check to sink into a hard constraint (an L4 script) — no agent goodwill needed; just let `cargo fmt --check`'s exit code speak.

## 2. Why format drift needs a harness

The most common formatting problems when an agent hand-writes code:

- inconsistent indentation / line breaks (style drifts across edits)
- long lines not wrapped, imports in a mess
- stale formatting from a different local rustfmt version

The consequence isn't a functional bug, but **accumulating diff noise**: every commit carries unrelated formatting churn that pollutes review and blame. The prompt "please keep formatting consistent" is L0 and the agent inevitably forgets it; `cargo fmt --check` is L4 and can't be bypassed.

## 3. Tool: rustfmt / cargo fmt

`cargo fmt` wraps rustfmt, in two modes:

| Command | Behavior | Use |
|---|---|---|
| `cargo fmt` | **automatically rewrites** source to standard format | quick format while developing / hook auto-fix |
| `cargo fmt --check` | checks without modifying; non-zero exit on drift | gate / CI |

## 4. Design: narness-rust-fmt.sh single responsibility

`scripts/narness-rust-fmt.sh` does exactly one thing: `cargo fmt --check`. No compile, no tests bundled in.

```bash
#!/usr/bin/env bash
# Do only a format check (cargo fmt --check)
set -euo pipefail
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
cargo fmt --check
```

Per the project convention "single-responsibility scripts", fmt / check / clippy / test each live in their own script; a "full-gate" god script is forbidden.

## 5. rustfmt.toml: fixing format conventions as config

Formatting rules should not live in prompts; they should be fixed into `rustfmt.toml` (project root). rustfmt reads it automatically, and machine and agent obey the same rules:

```toml
# rustfmt.toml
max_width = 100
edition = "2021"
imports_granularity = "Crate"
group_imports = "StdExternalCrate"
```

Point: to change a rule, change `rustfmt.toml`, not a prompt describing "please use 100 columns".

## 6. Key design decision: check-only or auto-fix

This is fmt's essential difference from lint/test — **fmt is the only check that can be auto-fixed safely**. So it has two placements:

| Scenario | Which command | Why |
|---|---|---|
| hook after edit (L3) | `cargo fmt` auto-fix | formatting fixes are side-effect-free and judgment-free; just fix it |
| pre-commit gate (L4) | `cargo fmt --check` | report only, force the agent to run fmt itself before committing |
| CI (L4) | `cargo fmt --check` | physically stop bad formatting from entering |

The current `narness-rust-fmt.sh` uses `--check` semantics (detect, don't modify), positioned as a "gate" not an "auto-fixer". If you want the hook to auto-format, add a separate `cargo fmt` command at the hook layer without changing this script's single responsibility.

## 7. Feeding failures back to the LLM

On failure `cargo fmt --check` prints the diff (which lines are misformatted) to stdout. Per the hook contract, write the diagnostics to **stderr** and `exit 2` so the LLM can see them:

```bash
if ! out="$(cargo fmt --check 2>&1)"; then
  printf '%s\n' "$out" >&2
  exit 2
fi
```

fmt's failure info is naturally actionable — the diff tells the agent "change these lines to this", no extra explanation needed.

## 8. Sink path

fmt has no "compile-time" equivalent — the compiler doesn't check formatting. So its end state is **an L4 script + CI gate**, and it can't reach L5. This is the reality of the constraint ladder: not every rule can sink to compile time; sink it as far as it will go.

```
L0 prompt "keep formatting consistent" → L4 narness-rust-fmt.sh --check → CI gate (end state)
```

## 9. Script mapping

| Script | Command | Meaning |
|---|---|---|
| `narness-rust-fmt.sh` | `cargo fmt --check` | detect only, no modify; non-zero exit = drift |
