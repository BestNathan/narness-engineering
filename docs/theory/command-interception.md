# Command interception: replacing and normalizing agent commands

## 1. The problem: the agent's default command is wrong

Two recurring failure modes:

1. **Wrong command** — the agent habitually runs `xxx yyy`, but this project wants `my-script.sh`.
2. **Wrong arguments** — the agent runs the right command with the wrong flags: it drops a required `-z`, adds a forbidden `--force`, or uses a deprecated `-x`.

Both are the *same* problem stated twice: **the agent's default execution behavior is wrong, and the constraint that would fix it is exactly the kind a prompt cannot hold.** A prompt ("please run Y instead of X") asks the agent to change its decision; the agent keeps re-issuing the wrong call because nothing at the execution layer stops it.

## 2. The core idea: intercept, don't argue

A prompt tries to change the agent's *decision*. Interception changes the *outcome*: the agent may keep "succeeding" at typing `xxx yyy`, but what actually executes is your command. The wrong invocation is not argued with — it is made harmless or impossible at the moment of execution.

This is the same move as the rest of the ladder: sink a constraint from the agent's goodwill (L0) to a deterministic mechanism at execution time (L3/L4). See [the constraint ladder](constraint-ladder.md).

## 3. Two interception primitives

| Primitive | Target | Effect | Fixes |
|---|---|---|---|
| **Replace** | command name | substitute the whole command for another | "agent runs `xxx`, project wants `my-script`" |
| **Normalize** | command arguments | rewrite flags — substitute `-x`→`-y`, append required `-z`, strip forbidden `--force` | "agent drops or abuses a flag" |

They compose: one rule can replace the command *and* normalize its arguments.

## 4. The one real decision: silent rewrite vs. block-and-teach

Everything else is plumbing; this is the choice that matters:

| Mode | Mechanism | Result |
|---|---|---|
| **rewrite** | the interpreter silently substitutes the command/args and lets it run | guaranteed correctness, zero friction — but the agent never learns the canonical form; transcripts stay dirty |
| **block** | the interpreter exits 2 with a stderr message naming the correct form | the agent sees the mistake, retries correctly, and the context converges — but each mistake costs a retry and it is probabilistic |

Pick by what you are trying to fix:

- Fix the *behavior* → `rewrite`. (This is a config-declared shim: the same guarantee as dropping a same-named script into `PATH`, but declared as data rather than as a file that shadows a name.)
- Fix the *vocabulary* — transcripts, docs, teammates → `block`.

A forbidden *safety* flag (e.g. `--force`) should always `block`: silently rewriting a destructive flag hides the intent instead of correcting it.

## 5. Delivery: config + a fixed interpreter, not a plugin script

This is where interception differs from the narness-rust validation scripts. A validation gate (`cargo check`, `clippy`) is a *fixed* check — it belongs in a plugin script shared by every project. But command interception is **per-project**: which command is "wrong" and what to replace it with is a property of *this* project, not of the language or tool.

So the rules should be **declarative configuration**, not imperative code:

- The project declares its rules in `.narness.toml`.
- A single fixed interpreter — the `narness` CLI — reads them and enforces them.
- The hook is one thin line: `narness intercept`. All logic lives in the CLI plus the config.

This extends the "thin hook entrypoint" convention one step further: the hook no longer delegates to a per-project script; it delegates to a fixed binary that reads the project's own rules. The surface that can drift (copy-pasted scripts) shrinks to a data file, and the logic is tested once in the CLI instead of re-audited per project.

### 5.1 Config shape

```toml
[[intercept]]
match = "xxx"           # command name the agent habitually runs
replace = "my-script"   # what to run instead (command replacement)

[[intercept]]
match = "build"
args = { "-x" = "-y" }  # substitute a flag
append = ["-z"]         # add a required flag
remove = ["--force"]    # strip a forbidden flag
mode = "block"          # default "rewrite"; use "block" for safety flags or to teach
```

### 5.2 Execution flow

```
PreToolUse(Bash)
   └─ narness intercept                # thin, fixed entrypoint
        ├─ read hook JSON from stdin   # extract the command line
        ├─ load .narness.toml          # the project's own rules
        ├─ match against [[intercept]]
        ├─ decide per rule:
        │    rewrite → emit the corrected command, exit 0
        │    block   → stderr diagnostic, exit 2 (fed back to the agent)
        └─ no match → passthrough, exit 0
```

The `narness` CLI is already this project's fixed interpreter — it reads `.narness.toml` today for environment checks. Interception is a second command for the same interpreter, not a new tool. See [Claude Code hooks](../reference/claude-code-hooks.md) for the hook contract (`PreToolUse`, exit-2 blocks, stderr feedback) the CLI plugs into.

## 6. Where it sits on the ladder

| Piece | Ladder level | Why |
|---|---|---|
| `.narness.toml` rules | declared like a convention (L1) | readable, per-project, diffable — but inert until interpreted |
| `narness intercept` | L3 trigger + L4 enforcement | fired by the PreToolUse hook; deterministically rewrites or blocks |
| the hook registration | L3 | the event that makes interception automatic |

The interesting property: the *rule* reads like a project convention, but it is *enforced* at L3/L4. Config is how you get a convention's expressiveness with a script's guarantee — deterministic, no goodwill required.

## 7. Core insight

Command interception is the ladder applied to what the agent *does*, rather than what it *produces*. Validation gates (`cargo check`, tests) constrain the agent's output; interception constrains its execution. The principle is identical: when a behavior is wrong, don't describe the right behavior — make the wrong behavior unable to take effect, and let the mechanism (rewrite or feedback) close the gap.
