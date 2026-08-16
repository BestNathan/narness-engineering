# Rust format harness engineering (fmt)

## 1. Positioning

Formatting is the most "mechanical" layer of the constraint ladder: it has no judgment space, only the single binary question "does it conform to rustfmt". Precisely for that reason it is also the easiest and most-deserving check to sink into a hard constraint (an L4 script) — no agent goodwill needed; just let `cargo fmt --check`'s exit code speak.

Its value is not "making code pretty". It is:

1. **Unifying style** — killing format debates for good.
2. **Raising review signal-to-noise** — logic changes stop being buried in formatting churn.
3. **Lowering the cost of AI-generated code** — run `cargo fmt` once and the agent's output lands in canonical form.
4. **A deterministic CI gate** — the whole team stays consistent without anyone "remembering to format".

## 2. Why format drift needs a harness

The most common formatting problems when an agent hand-writes code:

- inconsistent indentation / line breaks (style drifts across edits)
- long lines not wrapped, imports in a mess
- stale formatting from a different local rustfmt version

The consequence isn't a functional bug, but **accumulating diff noise**: every commit carries unrelated formatting churn that pollutes review and blame. The prompt "please keep formatting consistent" is L0 and the agent inevitably forgets it; `cargo fmt --check` is L4 and can't be bypassed.

## 3. Tool: `rustfmt` and `cargo fmt`

`rustfmt` is Rust's official formatter — the analogue of Prettier (JS/TS), Black (Python), `gofmt` (Go), clang-format (C/C++). It comes as a toolchain component and is normally driven through Cargo:

| Command | Behavior | Use |
|---|---|---|
| `cargo fmt` | **rewrites** source to canonical format | quick format while developing |
| `cargo fmt --all -- --check` | checks without modifying; non-zero exit on drift | gate / CI |
| `rustfmt src/lib.rs` | formats one file (or stdin) directly | editor save hooks, snippets outside a Cargo project |

**Check vs fix output** — answering "was anything formatted?":

- `cargo fmt --all -- --check` **reports**: for each non-conforming file it prints `Diff in <file> at line <n>:` plus the diff that would be applied, and exits non-zero. This is the result a gate needs — which files, and what would change.
- `cargo fmt` **fixes silently**: it rewrites files and prints no summary. To see what changed, inspect `git diff` / `git status`.

The harness-relevant distinction:

- **`cargo fmt`** locates `Cargo.toml`, walks the workspace/crate module tree, and applies the repo's `rustfmt.toml` / `.rustfmt.toml`. This is what the gate must use.
- **`rustfmt`** formats an isolated file and does **not** understand workspace structure, feature context, or crate-level config. Use it only for single files, never as the project gate.

Two flags matter for a correct gate:

- **`--all`** — format **every workspace member**. `cargo fmt` without it only touches the current (default) package, silently leaving the rest of a monorepo unchecked.
- **`--`** — Cargo-argument terminator; everything after it is passed to `rustfmt` itself (e.g. `--check`).

## 4. Design: `narness-rust-fmt.sh` single responsibility

`scripts/narness-rust-fmt.sh` does exactly one thing: a check-only format gate. No compile, no tests, no auto-fix bundled in.

```bash
#!/usr/bin/env bash
# Do only a format check (cargo fmt --all -- --check)
set -euo pipefail
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
cargo fmt --all -- --check
```

Per the project convention "single-responsibility scripts", fmt / check / clippy / test each live in their own script; a "full-gate" god script is forbidden.

## 5. The ground-truth gate: deterministic on a pinned toolchain

The fmt gate is only meaningful on a **pinned toolchain** — see [SKILL.md](../SKILL.md) "Toolchain pinning" for the shared prerequisite (a lying gate's usual cause is rustfmt version drift). fmt-specific:

- Run the gate from the **workspace root** so `cargo fmt --all` sees every member.
- CI must **check, never mutate**:

```
cargo fmt --all -- --check     # correct: reports drift, exits non-zero
cargo fmt --all                # wrong in CI: rewrites files and doesn't commit them back
```

## 6. Config as code: `rustfmt.toml`

Formatting rules should not live in prompts; they should be fixed into `rustfmt.toml` (project root, or `.rustfmt.toml`). rustfmt reads it automatically, and machine, agent, and CI obey the same rules:

```toml
edition = "2024"
max_width = 100
tab_spaces = 4
hard_tabs = false
newline_style = "Unix"
reorder_imports = true
reorder_modules = true
```

| Config | Meaning |
|---|---|
| `edition` | the Rust edition used to parse and format (e.g. `2021`, `2024`) |
| `max_width` | desired line width — a *tendency*, not a hard guarantee (long URLs, string literals, unbreakable tokens may still overflow) |
| `tab_spaces` / `hard_tabs` | indentation unit |
| `newline_style` | `Unix` = LF, `Windows` = CRLF, `Native` = follow the OS |
| `reorder_imports` / `reorder_modules` | sort and re-group `use` statements |

Point: to change a rule, change `rustfmt.toml`, not a prompt describing "please use 100 columns". Commit the config so every environment shares it.

## 7. stable vs nightly config (a determinism hazard)

Some rustfmt options are **nightly-only** (`imports_granularity`, `group_imports`, `wrap_comments`, `format_code_in_doc_comments`, `format_strings`, `normalize_comments`, …). On a stable toolchain they don't take effect — rustfmt warns `unstable features are only available in nightly` — and a config that silently half-applies is nondeterministic.

fmt-specific rules:

1. On stable CI, use only **stable-supported** options; verify each key against the pinned `rustfmt --version`.
2. Don't paste random `rustfmt.toml` snippets from the web.
3. If the team truly needs nightly-only formatting, everyone runs the same dated nightly — see [SKILL.md](../SKILL.md) "Toolchain pinning".

## 8. Escape hatches and why they weaken the gate

rustfmt offers three ways to opt out. Each is a **soft spot** where the gate stops applying, so overuse defeats the point of having a gate:

| Hatch | Form | When (rarely) justified |
|---|---|---|
| ignore paths | `ignore = ["generated", "src/generated/**"]` | generated/vendored code where formatting would create huge diffs |
| skip submodules | `skip_children = true` | almost never — leaves whole modules permanently unformatted |
| skip code | `#[rustfmt::skip]` (items), `#[rustfmt::skip::macros(...)]` | hand-aligned tables, generated blocks, DSL macro args |

Rules of thumb:

- Prefer fixing generated code **at the generator** (have the generator emit rustfmt-clean output) over `ignore`.
- Don't `ignore = ["target"]` — `target/` is never in Cargo's source walk anyway.
- Treat `#[rustfmt::skip]` as an exception to be justified, not a styling tool; a team that leans on it to resist formatting loses uniformity.
- If you must skip, keep it **visible and few** — a skip is a decision a reviewer can question.

## 9. What rustfmt cannot format (the gate's blind spot)

rustfmt formats what it can **parse**. Rust's macro system makes some code opaque to it:

- macro internals it can't understand (custom DSLs, `macro_rules!` bodies, proc-macro attributes)
- embedded languages inside macros — SQL, HTML, regex, templates, GraphQL
- complex built-in macros (`println!`, `format!`, `json!`, `sqlx::query!`)

In these spots rustfmt may format only partially or leave the code untouched. Harness implication: **the fmt gate is necessary, not sufficient** — a green `--check` does not guarantee every line is canonical. Don't fight rustfmt over macro-heavy code (you can't win); accept that the gate covers the parseable surface and rely on the other checkpoints for the rest.

## 10. Key design decision: check-only or auto-fix

fmt is the **only checkpoint that can be auto-fixed safely** — formatting rewrites are side-effect-free and judgment-free. So it has two placements:

| Scenario | Which command | Why |
|---|---|---|
| hook after edit (L3) / editor save | `cargo fmt` auto-fix | just fix it; no judgment, no risk |
| pre-commit gate (L4) | `cargo fmt --all -- --check` | report only; force the agent to run fmt itself before committing |
| CI (L4) | `cargo fmt --all -- --check` | physically stop bad formatting from entering |

The current `narness-rust-fmt.sh` uses `--check` semantics (detect, don't modify), positioned as a **gate**, not an auto-fixer. If you want the after-edit hook to auto-format, add a separate `cargo fmt` command at the hook layer without changing this script's single responsibility.

**Pre-commit behavior**: the gate runs on every `pre-commit`. On drift it **blocks the commit** (non-zero exit) and its failure message must do two things — **report** the drift (the per-file diff) and **hint the fix**: "run `cargo fmt --all` to auto-format, then re-commit". The hint names the tool's own auto-fixer, not a second narness script — a check+fix "god script" is forbidden, so the check stays check-only and the fix stays a tool command.

## 11. Editor integration is convenience, the gate is ground truth

Editor "format on save" (rust-analyzer calling rustfmt in VS Code/RustRover/Neovim/etc.) is a **convenience**, not an enforcement mechanism — it only fires if the editor is configured, and each IDE has its own code-style settings that can drift from the repo's rules.

The ground truth is always:

```
rustfmt.toml + cargo fmt --all -- --check   ← the standard every environment is measured against
```

Rules:

- Point the editor at `rustfmt` via the Rust LSP, and make sure the editor's toolchain matches the project's `rust-toolchain.toml`.
- Don't let IDE-private code-style settings become a de-facto standard; if they disagree with `rustfmt.toml`, the CI gate catches the drift.

## 12. Division of labor: fmt vs clippy vs rust-analyzer

These three tools are frequently confused; they are **separate checkpoints** (single responsibility) and must not be merged:

| Tool | Question it answers |
|---|---|
| `rustfmt` | what the code *looks like* (layout, spacing, imports) |
| `clippy` | whether the code is *idiomatic / suspect* (see [lint-harness.md](lint-harness.md)) |
| `rust-analyzer` | how the IDE *understands* the code (completion, diagnostics, refactor) |

rustfmt will not delete unused imports or do semantic fixes — that's `cargo fix` / `cargo clippy --fix` / `cargo machete` / `cargo udeps` territory. Keeping these as distinct gates is what makes each failure message precise.

## 13. First-format hygiene: one dedicated commit

Introducing rustfmt to an existing codebase produces one large, one-time diff. Land it as an isolated commit:

```
chore: format Rust code with rustfmt
```

Then keep logic changes in separate commits. This keeps `git blame`, review, and rollback clean — the same "separate formatting churn from logic" goal as §2, applied at the moment of adoption.

## 14. Feeding failures back to the LLM

On failure, `cargo fmt --check` prints `Diff in <file> at line <n>:` plus the diff for each non-conforming file, and exits non-zero — the result identifies **which files** are misformatted and exactly what would change. Per the hook contract, write the diagnostics to **stderr** and `exit 2` so the LLM can see them, and append the fix hint:

```bash
if ! out="$(cargo fmt --all -- --check 2>&1)"; then
  printf '%s\n' "$out" >&2
  echo "fix: run 'cargo fmt --all' to auto-format" >&2
  exit 2
fi
```

The diff tells the agent "change these lines to this"; the hint names the exact command that does it.

## 15. Sink path

fmt has no "compile-time" equivalent — the compiler doesn't check formatting. So its end state is **an L4 script + CI gate**, and it can't reach L5. This is the reality of the constraint ladder: not every rule can sink to compile time; sink it as far as it will go.

```
L0 prompt "keep formatting consistent"
  → L4 narness-rust-fmt.sh (cargo fmt --all -- --check gate)
  → CI gate (end state)
```

## 16. Script mapping

| Script | Command | Meaning |
|---|---|---|
| `narness-rust-fmt.sh` | `cargo fmt --all -- --check` | detect only, no modify; non-zero exit = drift, workspace-wide |
