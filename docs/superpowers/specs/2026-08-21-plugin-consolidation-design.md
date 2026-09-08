# narness plugin consolidation — design spec (v0.1)

## 1. Goal and scope

Collapse the two plugins (`narness-rust`, `narness-git`) and the repo-root `docs/theory/` +
`docs/reference/` into a **single `narness` plugin** containing a **single `narness` skill**, whose
`SKILL.md` is the main entry point for the harness design philosophy and whose `references/` is the
one flat home for all supporting material.

The motivation is the cross-reference problem: the same concept (a checkpoint's design, the git
layering model, the test harness) currently lives in two or three places — a plugin skill reference,
a repo-root doc, and an inline SKILL.md section — and the plugins hard-reference each other's paths
(`plugins/narness-git/…` → `plugins/narness-rust/scripts/…`). After this change, every concept has
exactly one file, and every cross-link is an intra-skill relative path.

Scope is **reorganization only**: move files, fix links, rewrite `SKILL.md`. No script logic, hook
logic, or config-template *content* changes. Scripts keep their `narness-rust-*` / `narness-git-*`
names.

## 2. Resolved decisions

| Fork | Decision |
|---|---|
| Fate of `docs/theory/` + `docs/reference/` | Fold entirely into the skill's `references/` |
| Script naming | Keep `narness-rust-*` / `narness-git-*` infixes, flat in one `scripts/` |
| Reference organization | Flat directory, no subdirs; `SKILL.md` holds the topic → file index |
| Skill count | One skill `narness` (was two: `narness-rust`, `narness-git`) |
| Skill location | Inside `plugins/narness/skills/narness/` — NOT symlinked to a root `skills/` (symlinks break on cache-copy install, and splitting skill/scripts/config across top-level dirs reintroduces the cross-reference problem) |
| Duplicate-topic merges | `git-hooks` and `rust-test` each collapse two files into one |
| Language posture | Rust-only for now; no placeholder dirs for future languages |
| `docs/superpowers/` | Untouched (design/plan artifacts, not harness material) |

## 3. Target layout

```
plugins/narness/
  .claude-plugin/plugin.json          # name: "narness"
  hooks/hooks.json                     # PostToolUse → post-edit-gate.sh (unchanged)
  hooks/scripts/post-edit-gate.sh      # calls scripts/narness-rust-check.sh (unchanged)
  scripts/                             # flat, 12 scripts
    narness-rust-fmt.sh
    narness-rust-check.sh
    narness-rust-clippy.sh
    narness-rust-test-unit.sh
    narness-rust-test-integration.sh
    narness-rust-test-e2e.sh
    narness-rust-test.sh
    narness-rust-invariants.sh
    narness-rust-test-discipline.sh
    narness-rust-changed-packages.sh
    narness-git-commit-msg.sh
    narness-git-install.sh
  githooks/                            # pre-commit / commit-msg / pre-push
  config/                              # 10 Rust config templates (moved verbatim)
    rustfmt.toml  clippy.toml  deny.toml  nextest.toml  rust-toolchain.toml
    strict-lints.rs  editorconfig  pre-commit-config.yaml  ci.yml  e2e.yml
  skills/narness/
    SKILL.md                           # main entry: design philosophy + index
    references/                        # flat, 14 files (see §4)
```

## 4. Reference file inventory (flat, 14 files)

Each target file's provenance is listed; **one concept → one file**.

| Target file | Content | Provenance |
|---|---|---|
| `constraint-ladder.md` | The constraint ladder | `docs/theory/constraint-ladder.md` |
| `harness-checkpoints.md` | Harness checkpoints and script design | `docs/theory/harness-checkpoints.md` |
| `tool-checkpoints.md` | Tool checkpoints: what each tool can enforce | `docs/theory/tool-checkpoints.md` |
| `command-interception.md` | Command interception: replacing/normalizing agent commands | `docs/theory/command-interception.md` |
| `decision-guide.md` | Decision guide: when to sink a constraint | `docs/theory/decision-guide.md` |
| `long-running-correctness.md` | Correctness of long-running tasks | `docs/theory/long-running-correctness.md` |
| `why-not-prompts.md` | Why not just prompts | `docs/theory/why-not-prompts.md` |
| `claude-code-hooks.md` | Claude Code hooks (PostToolUse) | `docs/reference/claude-code-hooks.md` |
| `codex-hooks.md` | Codex hooks | `docs/reference/codex-hooks.md` |
| `git-hooks.md` | Git hooks + the layering model (merged) | `docs/reference/git-hooks.md` **+** skill `git-hook-layering.md` |
| `rust-fmt.md` | Format harness | skill `fmt-harness.md` |
| `rust-lint.md` | Lint harness | skill `lint-harness.md` |
| `rust-test.md` | Test harness (three tiers + discipline) | skill `test-harness.md` **+** `docs/reference/rust-test-harness.md` |
| `rust-tool-config.md` | Recommended tool configs (strict mode) | skill `tool-config.md` |

## 5. Dedup / merge decisions

- **`git-hooks.md`** merges `docs/reference/git-hooks.md` with the skill's
  `git-hook-layering.md`. The layering model (edit → commit → push → CI), the block-vs-feedback
  contract, `core.hooksPath` sharing, the pre-commit alternative, and the server-side backstop all
  live in one file; the shorter repo-doc's unique bits (if any) are folded in, and the redundant
  rest is dropped.
- **`rust-test.md`** merges the skill's `test-harness.md` with `docs/reference/rust-test-harness.md`.
  One file for the three tiers (unit ≥95% / integration ≥80% / e2e gap-filling), test discipline, and the
  layered triggering model.
- **Renames** (flat dir needs a `rust-` prefix to disambiguate): `fmt-harness.md` → `rust-fmt.md`,
  `lint-harness.md` → `rust-lint.md`, `tool-config.md` → `rust-tool-config.md`.
- **Not merged**: `claude-code-hooks.md` and `codex-hooks.md` stay separate (distinct platforms).

## 6. SKILL.md outline (the main entry)

Frontmatter: `name: narness`; description reframed as language-agnostic harness engineering.

Body, in order:

1. **Core idea** — constrain agents with code/hooks/scripts, not prompts (from both old SKILLs'
   shared intro).
2. **The constraint ladder** — one general table (L0–L5), no longer a separate "Rust mapping" and
   "git mapping".
3. **Harness checkpoint taxonomy** — the eight checkpoints as the one yes/no-question table
   (summarized from `harness-checkpoints.md`).
4. **The two surfaces** — edit-time hook (feeds back) vs git/CI (blocks); the block-vs-feedback
   contract (from the old git SKILL).
5. **Changed vs full scope** — the `--scope`/`--coverage` model and the fail-safe fallback.
6. **Config minimalism** — only set what differs from a tool's default; comment out the rest.
7. **Steps to sink a constraint** — the L0→L5 decision steps.
8. **Index** — one table mapping topic → `references/<file>` (grouped by principle / tool /
   language / platform in the *table* only; links stay flat).
9. **Scripts** — the 12-script table (unchanged content, relinked to `../../scripts/`).
10. **Config templates** — pointer to `../../config/` + `references/rust-tool-config.md`.
11. **Anti-patterns** — the consolidated "anti-pattern → hard constraint" table.

## 7. Path-reference fixes

| Location | Before | After |
|---|---|---|
| `githooks/pre-commit`, `pre-push` | `$root/plugins/narness-rust/scripts` | `$root/plugins/narness/scripts` |
| `githooks/commit-msg` | `$root/plugins/narness-git/scripts` | `$root/plugins/narness/scripts` |
| `scripts/narness-git-install.sh` | `SOURCE_GITHOOKS` → `narness-git/githooks` | → `narness/githooks` |
| `references/rust-tool-config.md` | links to `docs/reference/…` | intra-skill `references/…` links |
| `.claude-plugin/marketplace.json` | two plugin entries | one entry, `source: ./plugins/narness` |
| `CLAUDE.md` §Structure + §1 script naming | `plugins/narness-rust`, `plugins/narness-git` | `plugins/narness` |

## 8. Deletions

- `plugins/narness-rust/` (entire tree, after content moved)
- `plugins/narness-git/` (entire tree, after content moved)
- `docs/theory/` (7 files, after move)
- `docs/reference/` (4 files, after move/merge)

## 9. Non-goals

- No new-language scaffolding (`narness-python` etc.) — future languages are a new reference file
  plus new scripts, not a new plugin.
- No changes to script bodies, hook bodies, or config-template content.
- No changes to `cli/`, `docs/superpowers/`, or `.claude-plugin/marketplace.json` schema.

## 10. Verification

After the move, confirm:

1. `find plugins -name '*.sh' -o -name '*.md' | sort` matches §3/§4 exactly.
2. No surviving reference to `narness-rust/` or `narness-git/` paths:
   `grep -rn "narness-rust\|narness-git" plugins docs/reference docs/theory` returns nothing except
   script *names* (`narness-rust-fmt.sh` etc.), which are intentional.
3. Every link in `SKILL.md` resolves to an existing file (spot-check the index table).
4. `git status` shows moves/renames plus exactly three content edits — the `SKILL.md` rewrite and
   the two merged references (`git-hooks.md`, `rust-test.md`). No content diff in `scripts/`,
   `githooks/`, or `config/`.
