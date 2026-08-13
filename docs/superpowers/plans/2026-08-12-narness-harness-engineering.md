# Narness Harness Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Narness project skeleton — the outer marketplace, the narness-rust plugin (skill + hook + scripts), and four theory docs — putting into practice the engineering idea of "constraining an agent with code/hooks/scripts rather than prompts".

**Architecture:** The constraint ladder (L0 prompts → L5 compile-time) is the theoretical core, threading through the docs and scripts. The repo is an "outer marketplace + subdirectory plugins" structure: `marketplace.json` points to `plugins/narness-rust`; the plugin contains a skill, a PostToolUse hook (fast gate), and standalone validation scripts (full gate / invariants / test discipline).

**Tech Stack:** Claude Code plugins (marketplace.json / plugin.json / hooks.json / SKILL.md), bash scripts (macOS-compatible, zero extra dependencies, JSON parsed with the system python3), markdown theory docs.

**Already exists:** `.gitignore`, the design doc `docs/superpowers/specs/2026-08-12-narness-harness-engineering-design.md` (already committed).

**Acceptance (aligned with design doc section 7):** complete directory structure; correct marketplace/plugin JSON format; skill covers the 5.2 outline; hook + three scripts executable; four theory docs present and threaded with the core proposition; README briefly states the philosophy and usage.

---

### Task 1: Project scaffold and directory structure

**Files:**
- Create: `LICENSE`
- Create: directory tree (`plugins/narness-rust/{skills/narness-rust,hooks/scripts,scripts}`, `docs/theory`, `.claude-plugin`)

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p .claude-plugin \
  plugins/narness-rust/.claude-plugin \
  plugins/narness-rust/skills/narness-rust \
  plugins/narness-rust/hooks/scripts \
  plugins/narness-rust/scripts \
  docs/theory
```

- [ ] **Step 2: Write LICENSE (MIT)**

Create `LICENSE`:

```
MIT License

Copyright (c) 2026 Narness contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: Verify the directory structure**

Run: `find . -type d -not -path './.git*' | sort`
Expected: output contains `.claude-plugin`, `plugins/narness-rust/...`, `docs/theory` and other directories.

- [ ] **Step 4: Commit**

```bash
git add LICENSE
git commit -m "chore: scaffold project directories and MIT license"
```

---

### Task 2: marketplace.json (outer marketplace)

**Files:**
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Write marketplace.json**

Create `.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-marketplace.json",
  "name": "narness",
  "version": "0.1.0",
  "description": "Narness harness engineering — constrain AI agents with code, hooks and scripts instead of prompts",
  "owner": { "name": "narness" },
  "plugins": [
    {
      "name": "narness-rust",
      "description": "Rust harness engineering skills, hooks and validation scripts",
      "version": "0.1.0",
      "source": "./plugins/narness-rust",
      "author": { "name": "narness" }
    }
  ]
}
```

- [ ] **Step 2: Verify JSON validity**

Run: `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Verify fields**

Run: `python3 -c "import json;d=json.load(open('.claude-plugin/marketplace.json'));print(d['name'], d['version'], d['plugins'][0]['source'])"`
Expected: `narness 0.1.0 ./plugins/narness-rust`

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat: add narness marketplace manifest"
```

---

### Task 3: plugin.json (narness-rust plugin metadata)

**Files:**
- Create: `plugins/narness-rust/.claude-plugin/plugin.json`

- [ ] **Step 1: Write plugin.json**

Create `plugins/narness-rust/.claude-plugin/plugin.json`:

```json
{
  "name": "narness-rust",
  "description": "Rust harness engineering: constrain AI agents with cargo, clippy, hooks and invariant scripts instead of prompts",
  "version": "0.1.0",
  "author": { "name": "narness" },
  "license": "MIT",
  "keywords": ["rust", "harness", "hooks", "clippy", "engineering"]
}
```

- [ ] **Step 2: Verify JSON validity**

Run: `python3 -m json.tool plugins/narness-rust/.claude-plugin/plugin.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add plugins/narness-rust/.claude-plugin/plugin.json
git commit -m "feat: add narness-rust plugin manifest"
```

---

### Task 4: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Create `README.md`:

```markdown
# Narness

Narness is a "research + documentation + Claude Code tooling" project that articulates and puts into practice an engineering philosophy:

> When code, hooks, or scripts can constrain an AI agent's behavior, prefer them over prompts. An agent will very likely not follow prompts; scripts and hooks let the agent discover that its implementation is wrong and guide it toward correct behavior, thereby guaranteeing correctness on long-running tasks.

## Philosophy

Prompts are soft constraints that an agent may ignore; scripts and hooks are hard constraints an agent cannot escape. Narness organizes its methodology around the **constraint ladder** (L0 prompts → L5 compile-time) and ships plugins that put constraints into code.

## Layout

- `docs/theory/` — theory and research docs
- `plugins/narness-rust/` — the Rust harness-engineering plugin (skill + hook + scripts)
- `.claude-plugin/marketplace.json` — marketplace definition

## Quick start

Install the `narness-rust` plugin after adding the marketplace:

```bash
claude plugin marketplace add <this repo's URL>
claude plugin install narness-rust
```

## Theory docs

- [Why not just prompts](docs/theory/why-not-prompts.md)
- [The constraint ladder](docs/theory/constraint-ladder.md)
- [Decision guide](docs/theory/decision-guide.md)
- [Correctness of long-running tasks](docs/theory/long-running-correctness.md)
```

- [ ] **Step 2: Self-review the content**

Check: does the README contain the one-line philosophy, layout description, quick start, and links to the four theory docs? If anything is missing, add it.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add project README"
```

---

### Task 5: Theory doc — why-not-prompts.md

**Files:**
- Create: `docs/theory/why-not-prompts.md`

- [ ] **Step 1: Write why-not-prompts.md**

Create `docs/theory/why-not-prompts.md`:

```markdown
# Why not just prompts

## 1. Prompts are soft constraints

A prompt is a piece of natural-language text that "requests" or "suggests" an agent do something, rather than "enforcing" it. Whether the constraint takes effect depends on whether the agent:

1. notices the text
2. correctly understands its meaning
3. remembers to comply at the specific decision point
4. judges compliance as more important than other goals

If any link breaks, the constraint fails. All four links depend on the agent's "goodwill", not on any verifiable mechanism.

## 2. Three failure mechanisms

### 2.1 Attention dilution

In a long context, one prompt competes for attention against a mass of information. As the conversation grows, constraints written early (even in the system prompt or CLAUDE.md) get gradually diluted, and at the specific decision point the agent may not even "think of" the constraint.

### 2.2 Probabilistic compliance

An LLM is a probabilistic model, not a rules engine. The same prompt, under different contexts and different sampling, is obeyed to different degrees. Today it remembers to write tests; tomorrow it may forget.

### 2.3 Conceding when goals conflict

When "following the constraint" conflicts with "finishing the current goal" — for example, hurrying to fix a bug, where skipping tests looks "faster" — the agent may rationalize the constraint away.

## 3. Why hard constraints work

Code, hooks, and scripts are hard constraints:

- They don't depend on the agent noticing — a hook fires automatically on an event
- They don't depend on the agent understanding — a script outputs a deterministic pass/fail
- They don't depend on the agent choosing to comply — a compile failure is a failure, no negotiation possible

## 4. Conclusion

Prompts are suited to expressing "intent" and "why", not to bearing the "must-do what". Constraints should sink as far as possible into the hard-constraint layers. This is Narness's core premise; see [the constraint ladder](constraint-ladder.md).
```

- [ ] **Step 2: Self-review the content**

Check: does it cover the complete logical chain "soft-constraint definition → three failure mechanisms → why hard constraints work → conclusion", and does the conclusion point to `constraint-ladder.md`?

- [ ] **Step 3: Commit**

```bash
git add docs/theory/why-not-prompts.md
git commit -m "docs: add why-not-prompts theory doc"
```

---

### Task 6: Theory doc — constraint-ladder.md

**Files:**
- Create: `docs/theory/constraint-ladder.md`

- [ ] **Step 1: Write constraint-ladder.md**

Create `docs/theory/constraint-ladder.md`:

```markdown
# The constraint ladder

## 1. Model overview

| Level | Name | Essence | Strength | Failure consequence |
|---|---|---|---|---|
| L0 | Prompts | natural-language instructions | weakest | the agent may simply ignore it |
| L1 | Project conventions | CLAUDE.md / AGENTS.md | weak | relies on the agent reading them voluntarily |
| L2 | Skill | workflow that can be invoked on demand | weak-medium | the agent may not invoke it |
| L3 | Hook | event-driven enforced script | medium-strong | runs automatically; failure is fed back |
| L4 | Script validation | cargo check/test/clippy | strong | deterministic pass/fail |
| L5 | Compile-time | the language and type system | strongest | violating it won't compile |

## 2. Layer details

### L0 Prompts

- What it can constrain: expressing intent, directional suggestions
- What it misses: anything that must be "always obeyed"
- When to use: always as a starting point, never as the endpoint

### L1 Project conventions (CLAUDE.md)

- What it can constrain: project background, conventions, habits
- What it misses: depends on the agent reading and obeying voluntarily
- When to use: to write "background" and "why", not "must"

### L2 Skill

- What it can constrain: step-by-step guidance for complex workflows
- What it misses: the agent may not trigger the skill
- When to use: to capture "how to do it" as a reusable workflow

### L3 Hook

- What it can constrain: automatic checks at event time
- What it misses: covers only the triggered events, not proactive decisions
- When to use: immediate validation after a change, immediate failure feedback

### L4 Script validation

- What it can constrain: independently verifiable deterministic rules
- What it misses: needs the agent/CI to invoke it
- When to use: compile, test, format, invariants

### L5 Compile-time

- What it can constrain: constraints that are physically impossible to violate at the language level
- What it misses: only what the type system can express
- When to use: any invariant expressible with types

## 3. Core proposition

The higher the level, the more it depends on the agent's goodwill; the lower the level, the more it guarantees long-running correctness. The goal: **sink constraints from L0–L2 down to L3–L5.**
```

- [ ] **Step 2: Self-review the content**

Check: the six-level table matches design doc table 2.1; each level has "what it can constrain / what it misses / when to use"; the core proposition is clear.

- [ ] **Step 3: Commit**

```bash
git add docs/theory/constraint-ladder.md
git commit -m "docs: add constraint-ladder theory doc"
```

---

### Task 7: Theory doc — decision-guide.md

**Files:**
- Create: `docs/theory/decision-guide.md`

- [ ] **Step 1: Write decision-guide.md**

Create `docs/theory/decision-guide.md`:

```markdown
# Decision guide: when to sink a constraint

## 1. Decision tree

When you meet a rule you "hope the agent will obey", judge in this order:

```
Has the agent violated this rule once?
├── No → express it with prompts (L0/L1) for now, and observe
└── Yes → has it violated it twice or more?
    ├── No → escalate to a Skill (L2) or Hook (L3)
    └── Yes → can it be expressed as a script (L4) or at compile time (L5)?
        ├── Yes → sink it to L4/L5 (prefer compile time)
        └── No → sink it to a Hook (L3), and use a script to feed back failures
```

## 2. Rules of thumb

- A rule expressible as a `clippy` lint → go straight to `clippy -D warnings` (L5)
- An invariant expressible with the type system → use types (L5), e.g. newtype, trait bounds
- Needs "immediate feedback after a change" → use a Hook (L3)
- Needs "pre-commit / CI validation" → use a script (L4)
- Only "intent and background" remain → leave it in prompts (L0/L1)

## 3. Anti-pattern checklist

| Anti-pattern | Problem | Correct approach |
|---|---|---|
| Writing "be sure to write tests" in CLAUDE.md | soft constraint, inevitably fails long-term | verify-test-discipline script + hook |
| Prompting "don't use unwrap" | the agent always forgets | clippy::unwrap_used (L5) |
| Verbally requiring "remember to format" | nobody executes it | cargo fmt --check gate (L4) |
| Writing invariants as comments | comments don't enforce | type system or assertions (L5/L4) |
```

- [ ] **Step 2: Self-review the content**

Check: the decision tree is logically coherent; the rules of thumb cover L3–L5; the anti-pattern checklist is consistent with the "code constraints > prompts" proposition.

- [ ] **Step 3: Commit**

```bash
git add docs/theory/decision-guide.md
git commit -m "docs: add decision-guide theory doc"
```

---

### Task 8: Theory doc — long-running-correctness.md

**Files:**
- Create: `docs/theory/long-running-correctness.md`

- [ ] **Step 1: Write long-running-correctness.md**

Create `docs/theory/long-running-correctness.md`:

```markdown
# Correctness of long-running tasks

## 1. What is a long-running task

A task that can't be completed in a single conversation and needs multiple round-trips or spans sessions: implementing a module from scratch, refactoring a whole subsystem, fixing a cross-file bug. Traits: context keeps growing, early constraints get diluted, errors accumulate.

## 2. Why long-running tasks drift most easily

- Early prompts get drowned by later context
- Small deviations at each step accumulate into a large directional error
- Without an external checkpoint, the agent struggles to notice "it's already wrong"

## 3. The harness's role at each stage

| Stage | Corresponding harness | Role |
|---|---|---|
| Task start | L1/L2 (CLAUDE.md + skill) | establish ground truth and acceptance criteria |
| During coding | L3 (hook) | validate every change immediately; deviations don't survive overnight |
| Staged commit | L4 (script) | full gate; keep accumulated errors from entering the next step |
| Integration / regression | L5 (compile-time) + CI | physical constraints + regression protection |

## 4. Core insight

Long-running correctness doesn't come from the agent "remembering the rules all along", but from this: every change passes through hard-constraint validation; an error is caught and fed back by a script/hook the moment it is produced; the agent is forced to fix it while it is still small. This is the mechanism of "letting the agent discover its own mistakes".
```

- [ ] **Step 2: Self-review the content**

Check: the four parts — long-running task definition, drift reasons, harness role-by-stage table, core insight — are complete.

- [ ] **Step 3: Commit**

```bash
git add docs/theory/long-running-correctness.md
git commit -m "docs: add long-running-correctness theory doc"
```

---

### Task 9: narness-rust skill

**Files:**
- Create: `plugins/narness-rust/skills/narness-rust/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `plugins/narness-rust/skills/narness-rust/SKILL.md`:

```markdown
---
name: narness-rust
description: "Guide to applying harness engineering in Rust projects — constrain an AI agent with cargo/clippy/hooks/scripts instead of prompts. Use when establishing constraints for a Rust project, or when sinking a rule that keeps failing under prompt-only constraint into code."
---

# Narness Rust — Rust harness engineering

Sink constraints on an AI agent from "prompts" down to "code, hooks, scripts", guaranteeing correctness on long-running tasks.

## Core idea

When code, hooks, or scripts can constrain an agent, prefer them over prompts. Prompts are soft constraints an agent may ignore; scripts are hard constraints an agent cannot escape.

## The constraint ladder (Rust mapping)

| Level | Means | Strength |
|---|---|---|
| L0 Prompts | verbal/doc requirements | weakest |
| L1 Project conventions | CLAUDE.md | weak |
| L2 Skill | this skill | weak-medium |
| L3 Hook | PostToolUse validation | medium-strong |
| L4 Scripts | check.sh / verify-invariants.sh | strong |
| L5 Compile-time | clippy -D warnings, #![forbid] | strongest |

## When to use this skill

- When establishing harness constraints for a Rust project
- When the agent repeatedly violates the same kind of constraint (e.g. always writing unwrap, always forgetting tests)
- When sinking a rule that "fails under prompt-only constraint" into code

## Steps to sink a constraint

1. Identify: which rule does the agent repeatedly violate?
2. Locate the level: which of L3–L5 does this rule best fit?
3. Implement:
   - L3 → configure a PostToolUse hook to run a validation script
   - L4 → call a validation script under scripts/
   - L5 → add a clippy lint / `#![forbid(...)]` / trait bound

## Available scripts

| Script | Purpose |
|---|---|
| `scripts/check.sh [DIR]` | full gate: fmt + clippy -D warnings + test |
| `scripts/verify-invariants.sh [DIR]` | invariants: ban unwrap/expect/panic!/unsafe without comment |
| `scripts/verify-test-discipline.sh [DIR]` | test discipline: a changed .rs must have a test |

## Test discipline

- Write tests before the implementation
- A changed .rs under src/ must have a corresponding test file
- Run the `check.sh` full gate before committing

## Common anti-patterns and their hard constraints

| Anti-pattern | Hard constraint |
|---|---|
| unwrap() everywhere | clippy::unwrap_used + verify-invariants.sh |
| bare panic! | clippy::panic + thiserror/anyhow |
| forgetting tests | verify-test-discipline.sh + hook |
| format drift | cargo fmt --check gate |
```

- [ ] **Step 2: Verify the frontmatter**

Run: `head -5 plugins/narness-rust/skills/narness-rust/SKILL.md`
Expected: the first lines are `---`, `name: narness-rust`, `description: "..."`, `---`.

- [ ] **Step 3: Self-review the content**

Check: does it cover the design doc 5.2 outline (when to use, ladder Rust mapping, sinking steps, script guidance, test discipline)? If anything is missing, add it.

- [ ] **Step 4: Commit**

```bash
git add plugins/narness-rust/skills/narness-rust/SKILL.md
git commit -m "feat: add narness-rust skill"
```

---

### Task 10: hooks.json + post-edit-gate.sh (PostToolUse fast gate)

**Files:**
- Create: `plugins/narness-rust/hooks/hooks.json`
- Create: `plugins/narness-rust/hooks/scripts/post-edit-gate.sh`

- [ ] **Step 1: Write hooks.json**

Create `plugins/narness-rust/hooks/hooks.json`:

```json
{
  "description": "Narness Rust fast gate: verify format and compilation after every .rs file edit",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/post-edit-gate.sh",
            "timeout": 60,
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Verify JSON validity**

Run: `python3 -m json.tool plugins/narness-rust/hooks/hooks.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Write post-edit-gate.sh**

Create `plugins/narness-rust/hooks/scripts/post-edit-gate.sh`:

```bash
#!/usr/bin/env bash
# post-edit-gate.sh — PostToolUse fast gate
# called by a Claude Code hook; hook JSON arrives on stdin.
# does a fast check on .rs files only (fmt + check); on failure, stderr + exit 2 feeds back to Claude.
set -uo pipefail

input="$(cat)"

# extract tool_input.file_path (the input key for Edit/Write/MultiEdit)
file_path="$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)"

# non-.rs files pass through
case "$file_path" in
  *.rs) ;;
  *) exit 0 ;;
esac

# fast gate 1: cargo fmt --check
if ! cargo fmt --check 2>&1; then
  echo "⚠ Narness fast gate: cargo fmt --check failed, please run cargo fmt and retry" >&2
  exit 2
fi

# fast gate 2: cargo check (skip the full test suite to avoid slowing the edit loop)
if ! cargo check 2>&1 | tail -n 30; then
  echo "⚠ Narness fast gate: cargo check failed, please fix the compile errors" >&2
  exit 2
fi

exit 0
```

- [ ] **Step 4: Syntax check**

Run: `bash -n plugins/narness-rust/hooks/scripts/post-edit-gate.sh && chmod +x plugins/narness-rust/hooks/scripts/post-edit-gate.sh && echo OK`
Expected: `OK`

- [ ] **Step 5: Smoke test (non-.rs files should pass through)**

Run:
```bash
echo '{"tool_input":{"file_path":"/tmp/foo.txt"}}' | plugins/narness-rust/hooks/scripts/post-edit-gate.sh; echo "exit=$?"
```
Expected: `exit=0` (no validation triggered)

- [ ] **Step 6: Commit**

```bash
git add plugins/narness-rust/hooks/hooks.json plugins/narness-rust/hooks/scripts/post-edit-gate.sh
git commit -m "feat: add PostToolUse fast-gate hook"
```

---

### Task 11: check.sh (full gate)

**Files:**
- Create: `plugins/narness-rust/scripts/check.sh`

- [ ] **Step 1: Write check.sh**

Create `plugins/narness-rust/scripts/check.sh`:

```bash
#!/usr/bin/env bash
# check.sh — Narness Rust full gate
# usage: check.sh [PROJECT_DIR]
# runs in sequence: cargo fmt --check → cargo clippy -D warnings → cargo test
set -euo pipefail

PROJECT_DIR="${1:-.}"

echo "==> Narness full gate: $PROJECT_DIR"
cd "$PROJECT_DIR"

echo "==> 1/3 cargo fmt --check"
cargo fmt --check

echo "==> 2/3 cargo clippy --all-targets --all-features -- -D warnings"
cargo clippy --all-targets --all-features -- -D warnings

echo "==> 3/3 cargo test"
cargo test

echo "==> all passed"
```

- [ ] **Step 2: Syntax check**

Run: `bash -n plugins/narness-rust/scripts/check.sh && chmod +x plugins/narness-rust/scripts/check.sh && echo OK`
Expected: `OK`

- [ ] **Step 3: Smoke test (temporary cargo project)**

Run:
```bash
tmp=$(mktemp -d)
cd "$tmp"
cargo new --lib smoke >/dev/null 2>&1
bash "$OLDPWD/plugins/narness-rust/scripts/check.sh" "$tmp/smoke"
echo "exit=$?"
rm -rf "$tmp"
```
Expected: the three stages `cargo fmt --check` / `cargo clippy` / `cargo test` output in sequence, ending with `all passed`, `exit=0`. (If cargo is unavailable in the environment, skip this step and note it in the commit message.)

- [ ] **Step 4: Commit**

```bash
git add plugins/narness-rust/scripts/check.sh
git commit -m "feat: add full-gate check script"
```

---

### Task 12: verify-invariants.sh (invariant check)

**Files:**
- Create: `plugins/narness-rust/scripts/verify-invariants.sh`

- [ ] **Step 1: Write verify-invariants.sh**

Create `plugins/narness-rust/scripts/verify-invariants.sh`:

```bash
#!/usr/bin/env bash
# verify-invariants.sh — Narness Rust invariant check
# usage: verify-invariants.sh [PROJECT_DIR]
# scans .rs files under src/ for:
#   - bare unwrap() / expect() (forbidden in production code)
#   - panic! / unreachable! / todo! / unimplemented!
#   - unsafe lacking a SAFETY comment
# zero extra dependencies (POSIX find + grep only), macOS compatible.
set -uo pipefail

PROJECT_DIR="${1:-.}"
SRC_DIR="$PROJECT_DIR/src"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "error: src directory not found: $SRC_DIR" >&2
  exit 1
fi

fail=0
echo "==> Narness invariant check: $SRC_DIR"

# 1. bare unwrap() / expect()
matches="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -nH -E '\.(unwrap|expect)\(' {} + 2>/dev/null || true)"
if [[ -n "$matches" ]]; then
  printf '%s\n' "$matches" >&2
  echo "✗ found unwrap()/expect(); replace with anyhow/thiserror or explicit error handling" >&2
  fail=1
else
  echo "✓ no bare unwrap()/expect()"
fi

# 2. panic! / unreachable! / todo! / unimplemented!
matches="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -nH -E '\b(panic|unreachable|todo|unimplemented)!' {} + 2>/dev/null || true)"
if [[ -n "$matches" ]]; then
  printf '%s\n' "$matches" >&2
  echo "✗ found panic!/unreachable!/todo!/unimplemented!; propagate errors with Result instead" >&2
  fail=1
else
  echo "✓ no panic!/unreachable!/todo!/unimplemented!"
fi

# 3. unsafe blocks lacking a SAFETY comment
unsafe_files="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -lE '\bunsafe\b' {} + 2>/dev/null || true)"
if [[ -n "$unsafe_files" ]]; then
  while IFS= read -r f; do
    if ! grep -q 'SAFETY' "$f"; then
      echo "✗ $f contains unsafe but no SAFETY comment" >&2
      fail=1
    fi
  done <<< "$unsafe_files"
else
  echo "✓ no unsafe code"
fi

if [[ $fail -ne 0 ]]; then
  echo "==> invariant check failed" >&2
  exit 1
fi
echo "==> invariant check passed"
```

- [ ] **Step 2: Syntax check**

Run: `bash -n plugins/narness-rust/scripts/verify-invariants.sh && chmod +x plugins/narness-rust/scripts/verify-invariants.sh && echo OK`
Expected: `OK`

- [ ] **Step 3: Smoke test (fixture with violations)**

Run:
```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/src"
printf 'fn good(x: Option<i32>) -> i32 { match x { Some(v) => v, None => 0 } }\n' > "$tmp/src/good.rs"
printf 'fn bad(x: Option<i32>) -> i32 { x.unwrap() }\nunsafe fn raw() {}\n' > "$tmp/src/bad.rs"
plugins/narness-rust/scripts/verify-invariants.sh "$tmp"; echo "exit=$?"
rm -rf "$tmp"
```
Expected: output contains `✗ found unwrap()/expect()` and `✗ ... contains unsafe but no SAFETY comment`, ending with `invariant check failed`, `exit=1`.

- [ ] **Step 4: Smoke test (clean fixture should pass)**

Run:
```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/src"
printf 'fn good(x: Option<i32>) -> i32 { match x { Some(v) => v, None => 0 } }\n' > "$tmp/src/good.rs"
plugins/narness-rust/scripts/verify-invariants.sh "$tmp"; echo "exit=$?"
rm -rf "$tmp"
```
Expected: three `✓`, ending with `invariant check passed`, `exit=0`.

- [ ] **Step 5: Commit**

```bash
git add plugins/narness-rust/scripts/verify-invariants.sh
git commit -m "feat: add invariant verification script"
```

---

### Task 13: verify-test-discipline.sh (test discipline check)

**Files:**
- Create: `plugins/narness-rust/scripts/verify-test-discipline.sh`

- [ ] **Step 1: Write verify-test-discipline.sh**

Create `plugins/narness-rust/scripts/verify-test-discipline.sh`:

```bash
#!/usr/bin/env bash
# verify-test-discipline.sh — Narness Rust test discipline check
# usage: verify-test-discipline.sh [PROJECT_DIR]
# checks that non-test .rs source files changed since git HEAD have a corresponding test file.
set -uo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

# changed non-test .rs source files (exclude tests/, *_test.rs, etc.)
changed="$(git diff --name-only HEAD -- '*.rs' 2>/dev/null | grep -vE '(^|/)(tests?|benches|examples)/|(_test|\.test)\.rs$' || true)"

if [[ -z "$changed" ]]; then
  echo "✓ no changed non-test .rs source files"
  exit 0
fi

fail=0
while IFS= read -r f; do
  # src/foo/bar.rs → tests/foo/bar.rs or tests/foo/bar_test.rs or src/foo/bar_test.rs
  stem="${f%.rs}"
  stem="${stem#src/}"
  candidates=(
    "tests/${stem}.rs"
    "tests/${stem}_test.rs"
    "src/${stem}_test.rs"
  )
  found=0
  for c in "${candidates[@]}"; do
    if [[ -f "$c" ]]; then found=1; break; fi
  done
  if [[ $found -eq 0 ]]; then
    echo "✗ $f changed but has no corresponding test file" >&2
    fail=1
  else
    echo "✓ $f has test coverage"
  fi
done <<< "$changed"

if [[ $fail -ne 0 ]]; then
  echo "==> test discipline check failed: add tests for the files above" >&2
  exit 1
fi
echo "==> test discipline check passed"
```

- [ ] **Step 2: Syntax check**

Run: `bash -n plugins/narness-rust/scripts/verify-test-discipline.sh && chmod +x plugins/narness-rust/scripts/verify-test-discipline.sh && echo OK`
Expected: `OK`

- [ ] **Step 3: Smoke test (temporary git repo, no test should fail)**

Run:
```bash
tmp=$(mktemp -d)
cd "$tmp"
git init -q
mkdir -p src
printf 'pub fn f() -> i32 { 1 }\n' > src/lib.rs
git add -A && git commit -qm init
printf 'pub fn f() -> i32 { 2 }\n' > src/lib.rs
bash "$OLDPWD/plugins/narness-rust/scripts/verify-test-discipline.sh" "$tmp"; echo "exit=$?"
rm -rf "$tmp"
```
Expected: output contains `✗ src/lib.rs changed but has no corresponding test file`, ending with `test discipline check failed`, `exit=1`.

- [ ] **Step 4: Smoke test (with a test should pass)**

Run:
```bash
tmp=$(mktemp -d)
cd "$tmp"
git init -q
mkdir -p src tests
printf 'pub fn f() -> i32 { 1 }\n' > src/lib.rs
printf 'use mylib::f;\n#[test]\nfn t() { assert_eq!(f(), 1); }\n' > tests/lib_test.rs
git add -A && git commit -qm init
printf 'pub fn f() -> i32 { 2 }\n' > src/lib.rs
printf 'use mylib::f;\n#[test]\nfn t() { assert_eq!(f(), 2); }\n' > tests/lib_test.rs
bash "$OLDPWD/plugins/narness-rust/scripts/verify-test-discipline.sh" "$tmp"; echo "exit=$?"
rm -rf "$tmp"
```
Expected: output contains `✓ src/lib.rs has test coverage`, ending with `test discipline check passed`, `exit=0`.

- [ ] **Step 5: Commit**

```bash
git add plugins/narness-rust/scripts/verify-test-discipline.sh
git commit -m "feat: add test-discipline verification script"
```

---

### Task 14: Final verification and wrap-up

- [ ] **Step 1: Validate all repo JSON**

Run:
```bash
for f in .claude-plugin/marketplace.json plugins/narness-rust/.claude-plugin/plugin.json plugins/narness-rust/hooks/hooks.json; do
  python3 -m json.tool "$f" > /dev/null && echo "OK $f"
done
```
Expected: three `OK ...`

- [ ] **Step 2: Syntax-check all scripts**

Run:
```bash
for f in plugins/narness-rust/hooks/scripts/post-edit-gate.sh plugins/narness-rust/scripts/*.sh; do
  bash -n "$f" && echo "OK $f"
done
```
Expected: four `OK ...`

- [ ] **Step 3: Check each item against design doc section 7 acceptance criteria**

Checklist:
1. Directory structure complete (Task 1)
2. marketplace/plugin JSON format correct (Task 2/3)
3. skill covers the 5.2 outline (Task 9)
4. hook + three scripts present and executable (Task 10–13)
5. Four theory docs present, core proposition threaded through (Task 5–8)
6. README briefly states the philosophy and usage (Task 4)

- [ ] **Step 4: Final directory tree check**

Run: `find . -type f -not -path './.git/*' | sort`
Expected: output contains all 14 target files (1 LICENSE + 1 README + 3 JSON + 1 SKILL.md + 4 scripts + 4 theory docs).

- [ ] **Step 5: Commit (if any files are missing)**

```bash
git status --short
git add -A
git commit -m "chore: finalize Narness scaffold" --allow-empty
```
Expected: clean working tree (`git status` shows no uncommitted changes).
