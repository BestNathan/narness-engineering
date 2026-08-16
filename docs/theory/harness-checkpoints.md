# Harness checkpoints and script design

## 1. What a checkpoint is

A harness is not one big "check". It is a **sequence of checkpoints** — each checkpoint asks a single yes/no question about the code under change, and each is backed by a single-responsibility script that returns a deterministic verdict. The agent's correctness does not come from one all-seeing gate; it comes from many narrow, independently-verifiable questions, each of which a script can answer without judgment.

This decomposition is what makes harness engineering work: a checkpoint is small enough to be **provable** (a binary pass/fail), **localizable** (it points at the exact file:line that failed), and **composable** (a fast form for the after-edit hook, a full form for the pre-commit gate).

## 2. The checkpoint taxonomy

Common checkpoints, ordered from cheapest/most-mechanical to most-expensive/most-behavioral:

| Checkpoint | Question it answers | Tool class | Script design |
|---|---|---|---|
| Format | does the code conform to the fixed style? | formatter (`--check`) | the only checkpoint with a safe auto-fix; decide check-only (gate) vs auto-fix (hook); fix style rules in a config file, never in prompts |
| Compile / type-check | does it compile / type-check? | compiler, check mode | the fastest full check; the after-edit hook's default for immediate feedback; the prerequisite every other checkpoint assumes |
| Lint / static analysis | is it written badly (compiles but shouldn't be)? | linter | escalate warnings to errors so violations exit non-zero; prefer a ready tool-native lint; where possible sink further into a source-level forbid (compile-time) |
| Invariants / conventions | does it obey project-specific rules a linter can't express? | text scan (grep) | only for the gaps the linter can't cover (cross-file rules, comment requirements); a deterministic pattern match; complement, never duplicate, the linter |
| Test | does it do the right thing? | test runner | a full gate (too slow for the hook); demand structured, localizable output so a failure maps to file:line + reason |
| Coverage | is it tested *enough*? | coverage + threshold | a numeric threshold that turns "are tests sufficient" from judgment into pass/fail; feed uncovered locations back to the LLM |
| Test discipline | did the change ship with a test? | VCS diff → test-file mapping | derive the changed source set from version control, map each to its matching test, fail on missing; answers "test exists", not "test passes" |
| Dependency / security audit | are dependencies vulnerable or stale? | package audit | run against the lockfile; deny on known vulnerabilities; schedule on the slow tier (pre-commit/CI), not the hook |
| Environment | are the runtime prerequisites present? | declarative check | declare prerequisites as data (version/exists) and report failures with fix suggestions; a harness for the machine, not for the code under change |

The last two are meta-checkpoints: dependency audit constrains the supply chain, environment check constrains the machine the agent runs on. The first seven constrain the change itself.

## 3. The script-design rubric

Whatever the checkpoint, its script obeys the same six rules. These are the "how to design a check script" answer in general:

1. **Single responsibility** — one script answers one checkpoint. Bundling several checks into a "full-gate" script is forbidden; it hides which check failed and prevents composability.
2. **Deterministic verdict** — the script's only job is to reach pass/fail, expressed through the exit code: `0` pass, `1` fail (script level), `2` fail (hook level, stderr fed back). No "maybe", no human interpretation required.
3. **Diagnostics to stderr** — on failure the script writes its findings to stderr, never stdout. A hook injects stderr into the LLM context; stdout is invisible to it.
4. **Localizable + actionable** — the failure output answers three questions: *where* (file:line), *why* (expected vs actual), *how to fix* (the next step). A verdict of "failed" with no location is a prompt, not a harness.
5. **Layered trigger** — every checkpoint has a fast form for the after-edit hook (immediate feedback) and a full form for the pre-commit/CI gate (complete validation). Cheap checks run often; expensive checks run at the gate.
6. **Sink as low as it will go** — prefer a tool-native check over a hand-rolled scan, and prefer a compile-time forbid over a script that must be invoked. Not every checkpoint can reach compile time (format cannot); sink each to its lowest reachable level and stop.

## 4. Why this taxonomy, not one big gate

A single "run everything" gate fails for two reasons. First, it gives the agent no intermediate feedback: by the time the gate runs, errors have accumulated and the fix is large. Second, it can't be layered: one monolithic check must run at full cost every time, so it can't afford to sit on the after-edit hook.

The checkpoint decomposition solves both: each checkpoint is cheap enough to run where its feedback is most useful, and narrow enough that its failure message tells the agent exactly what to fix. This is the same mechanism as the rest of Narness — the agent discovers its mistake at the moment it makes it, and a script guides it back, rather than being told afterward that "something" went wrong.

## 5. Sink-path summary

| Checkpoint | Sink path | Lowest reachable level |
|---|---|---|
| Format | script `--check` → CI gate | L4 (no compile-time equivalent) |
| Compile / type-check | script wrapper → CI | L4 (type errors themselves are L5) |
| Lint | script `-D warnings` → source-level forbid | L5 |
| Invariants | grep script → CI | L4 (or L5 where a type can express it) |
| Test | runner script → CI | L4 |
| Coverage | threshold script → CI | L4 |
| Test discipline | diff→mapping script → pre-commit | L4 |
| Dependency audit | lockfile audit → CI | L4 |
| Environment | declarative check | L4 (runtime, not compile time) |

See also [tool checkpoints](tool-checkpoints.md) — which tool enforces which checkpoint (git, GitHub, GitLab, Claude Code, Codex).
