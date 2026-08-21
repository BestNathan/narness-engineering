# Recommended tool configs (strict mode)

## 1. Positioning

Each harness checkpoint is backed by one tool, and each tool reads one config surface. This doc is the consolidated map — **tool → checkpoint → config file → recommended default** — so a project can adopt the whole narness-rust harness by copying the files under `config/`.

The configs ship in **strict mode**: the strongest *code-quality* control. They are **not arbitrary** — they encode the exact numbers the `narness-rust-*.sh` scripts were written against (coverage ≥95% / ≥80%, `-D warnings`, `--all -- --check`, `--all-targets --all-features`) plus the strictest tier of each tool (`#![forbid]` restriction lints, `deny.toml` with everything denied). Strict means *code style and stable operation*, not the newest compiler — everything here is stable-supported. Copy the file, then adapt the genuinely project-specific bits (disallowed lists, license allow-list) — per [rust-lint.md](rust-lint.md), start from your *observed* failure, not a curated list.

## 2. Strict mode: the three invariants

`edition` / `channel` / `components` are where a gate most often "lies". Strict mode binds them with three invariants:

1. **One channel, pinned and stable.** `rust-toolchain.toml` pins a *specific stable release* (`1.89.0`), never a rolling "latest". Pinning is what keeps every gate deterministic — the same compiler on the developer's machine, CI, and the agent, so a gate can never pass locally and fail in CI. Nightly is deliberately avoided: it only reintroduces drift without adding anything the strict lints need.

2. **Edition 2024 everywhere, and it must match.** `rustfmt.toml`'s `edition` must equal every crate's `Cargo.toml` `edition`; a mismatch makes rustfmt parse against the wrong grammar. And `clippy.toml`'s `msrv` must be ≥ 1.85 (the edition-2024 floor) and ≤ the channel — so edition, msrv, and channel can never contradict each other.

3. **Every component a gate needs is listed.** `components` enumerates exactly what the scripts invoke — `rustfmt`, `clippy`, and `llvm-tools-preview` (which `cargo llvm-cov` requires and is the one people miss). Nothing the gate needs may be left to install on demand; that is precisely the drift that makes a gate nondeterministic.

## 3. Two kinds of config

A gate's behavior comes from **two surfaces**, and confusing them is a common mistake:

1. **A config file the tool auto-reads** — `rustfmt.toml`, `clippy.toml`, `.config/nextest.toml`, `deny.toml`, `rust-toolchain.toml`, `.editorconfig`. Machine, agent, and CI all read the same file, so they cannot drift.
2. **A flag the script already passes** — `--all -- --check` (fmt), `-D warnings` (clippy), `--fail-under-lines 95/80` (llvm-cov). These are baked into the scripts; the config file exists to hold what the *flag cannot*: parameters, thresholds, profiles, pinning.

The rule: **the script owns the verdict (the flag); the config file owns the parameter (the number).** They must agree — change the threshold in one place and you must change it in the other.

A third discipline applies to the files themselves: **only set what differs from the tool's default; comment out the rest.** The shipped templates leave default-valued keys commented (`# max_width = 100`), so every *active* line is a deliberate override and every commented line is a documented default — not a dead line. This keeps the config minimal and makes each non-default setting stand out as an intentional choice.

## 4. The map

| Harness tool | Checkpoint | Config surface | Copy `config/` template to | Read by |
|---|---|---|---|---|
| rustfmt | Format | `rustfmt.toml` | `<root>/rustfmt.toml` | `cargo fmt` |
| rustc + components | Compile / every gate | `rust-toolchain.toml` | `<root>/rust-toolchain.toml` | rustup / cargo |
| clippy | Lint | `clippy.toml` (params) + `strict-lints.rs` (levels) | `<root>/clippy.toml` + paste `strict-lints.rs` into `lib.rs` | `cargo clippy` |
| cargo-llvm-cov | Coverage | `--fail-under-lines` flag (already in the script) | — | `cargo llvm-cov` |
| cargo-nextest | Test (runner) | `.config/nextest.toml` | `<root>/.config/nextest.toml` | `cargo nextest` |
| cargo-deny | Dependency audit | `deny.toml` | `<root>/deny.toml` | `cargo deny check` |
| EditorConfig | editor baseline | `.editorconfig` | `<root>/.editorconfig` | editors |
| pre-commit | git hooks (commit) | `.pre-commit-config.yaml` | `<root>/.pre-commit-config.yaml` | pre-commit |
| GitHub Actions | CI merge gate | `.github/workflows/*.yml` | `<root>/.github/workflows/ci.yml` (+ `e2e.yml`) | GitHub |

## 5. Per-tool notes

- **rustfmt** — `rustfmt.toml` holds the style rules (line width, imports). Stable-only keys, so the gate is deterministic on the pinned stable channel. Full design: [rust-fmt.md](rust-fmt.md) §6.
- **rust-toolchain.toml** — the shared prerequisite: a pinned stable channel + the full component list. `llvm-tools-preview` is the coverage gate's dependency and the usual omission. Full design: [SKILL.md](../SKILL.md) "Toolchain pinning".
- **clippy** — `clippy.toml` sets *parameters* (thresholds, `msrv`, disallowed lists); the *levels* live in source. `strict-lints.rs` is the strictest tier's `#![forbid]` header (unsafe, unwrap/expect/panic, arithmetic overflow, unchecked indexing, reasonless `allow`) — paste it into each crate. Full design: [rust-lint.md](rust-lint.md) §5, §8.
- **llvm-cov** — the coverage thresholds are **flags baked into the scripts** (`--fail-under-lines 95` unit / `80` integration); there is no file to copy. To change a threshold, edit the script (or add a `.llvm-cov.toml` / `--fail-under-regions` secondary axis — see `rust-test.md` §3.3).
- **nextest** — `.config/nextest.toml` defines `default` and `ci` profiles; `failure-output = "immediate"` is what makes failures feed back early. Full design: `rust-test.md` §2.
- **cargo-deny** — `deny.toml` enforces the dependency-audit checkpoint; in strict mode every advisory/ban/license/source check is `deny`. Full design: [rust-lint.md](rust-lint.md) §9.
- **EditorConfig / pre-commit / CI** — the outer layers. EditorConfig is convenience (the gate is ground truth); pre-commit stays fast (`--scope=changed` + invariants); CI stays full (`--scope=full --coverage` + `cargo deny check`). Full design: `git-hooks.md` and [rust-test.md](rust-test.md) §8.

## 6. Adoption order

Copy in this order — each file makes the next meaningful:

1. `rust-toolchain.toml` — pin first; without it every other gate can drift.
2. `rustfmt.toml` + `clippy.toml` + `strict-lints.rs` — the code-quality gates' parameters and the L5 `#![forbid]` levels.
3. `.config/nextest.toml` + `deny.toml` — the test runner and the dependency audit.
4. `.pre-commit-config.yaml` — local fast gate (commit time).
5. `ci.yml` (+ optional `e2e.yml`) — the required merge gate and the 补位 tier.
