# Narness CLI — environment checker design doc

- Date: 2026-08-13
- Status: design approved (Option A: declarative TOML + built-in checkers + a unified Check interface)

## 1. Overview

The Narness CLI is a **preflight environment checker**: a `.narness.toml` config in the project root declares the requirements the agent's runtime environment must satisfy; running `npx narness` checks each one, and on failure gives a "where it failed + why + how to fix" remediation, feeding back via structured output (human + JSON) and a clear exit code.

**Core idea** (continuing Narness's harness-engineering philosophy): environment constraints shouldn't stay in docs ("you need node 22"), but sink into an executable, verifiable checker that can feed the LLM.

**Positioning**: environment checks first; harness-config checks as an extensible type (reserved architecturally via the `Check` interface, not implemented in the initial phase).

## 2. Tech stack and dependencies

- **TypeScript / Node.js**, run directly via `npx narness`
- Dependencies (minimized):
  - `smol-toml` — TOML parsing
  - `semver` — version comparison
- No runtime native dependencies; pure JS

## 3. Config schema (`.narness.toml`)

A `.narness.toml` in the project root with a top-level `[[checks]]` array, one check per entry.

```toml
# .narness.toml

# version check: the command's version must satisfy min/max (semver)
[[checks]]
type = "version"
name = "node"
min = "22"

# existence check: the shell tool must be executable
[[checks]]
type = "exists"
name = "rg"

[[checks]]
type = "exists"
name = "jq"

# MCP check: the MCP config must declare this server
[[checks]]
type = "mcp"
name = "filesystem"
```

### 3.1 Field definitions

Common fields per check:

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | yes | `"version"` / `"exists"` / `"mcp"` |
| `name` | string | yes | target (version=command name; exists=command name; mcp=server name) |

Type-specific fields:

| Type | Field | Description |
|---|---|---|
| `version` | `min` | minimum version (loose semver, e.g. `"22"`, `"22.14"`, `"22.14.0"`) |
| `version` | `max` (optional) | maximum version |
| `exists` | `names` (optional) | string array declaring multiple tools at once; may be provided alongside `name` (both are checked) |

### 3.2 Checker semantics

- **`version`**: run `<name> --version`, extract a semver from the output (regex for the first `\d+\.\d+(\.\d+)?`, compatible with `node`'s `v22.14.0`, `cargo`'s `cargo 1.70.0 (…)`, etc.), compare against `min`/`max`. On failure, `detail` records the actual version.
- **`exists`**: `command -v <name>` probes whether the command is executable. On failure, `fix` suggests an install (generic "please install <name>"; the concrete package name is written by the user into the config's `fix` field — see 3.3).
- **`mcp`**: checks whether the `mcpServers` key of `.mcp.json` (project-level) declares `name`. On failure, `fix` suggests adding that server.

### 3.3 Custom fix hint (optional)

Each check may carry a `fix` field overriding the default remediation:

```toml
[[checks]]
type = "exists"
name = "rg"
fix = "brew install ripgrep"
```

Without a `fix`, the checker uses a default suggestion (e.g. a `version` failure suggests "please upgrade <name> to >= <min>").

## 4. Package structure

The npm package lives in the Narness repo's **`cli/` subdirectory**, its own `package.json` (`name: "narness"`, `bin` exposes `narness`), publishable via `npm publish`.

```
cli/
├── package.json           # name: narness, bin, dependencies (smol-toml, semver)
├── tsconfig.json
├── src/
│   ├── index.ts           # CLI entrypoint: parse --json / --config, call the engine, set exit code
│   ├── config.ts          # locate .narness.toml upward from cwd, parse into a typed Config
│   ├── engine.ts          # iterate checks, dispatch to checkers by type, collect CheckResult[]
│   ├── checks/
│   │   ├── check.ts       # Check interface + CheckResult type (extension point)
│   │   ├── version.ts     # version checker
│   │   ├── exists.ts      # existence checker
│   │   └── mcp.ts         # MCP declaration checker
│   ├── report.ts          # human / JSON output formatting
│   └── registry.ts        # type → Check registry (used by the engine's dispatch)
└── tests/                 # unit + integration + CLI tests
```

## 5. Core interface

```ts
// checks/check.ts — the unified contract for all checkers (extension point)
interface Check {
  run(check: CheckConfig, ctx: Context): Promise<CheckResult>;
}

interface CheckResult {
  status: "pass" | "fail" | "error";  // error = the checker itself errored (e.g. command couldn't run)
  check: CheckConfig;
  message?: string;   // on failure: where it failed + why
  fix?: string;       // on failure: how to fix (remediation)
  detail?: string;    // extra info (e.g. the actual version)
}
```

`registry.ts` maintains the `type → Check` mapping. Adding a checker type = adding one module + one registry line, without touching the engine — the landing point of the extensible architecture.

## 6. Data flow

1. `npx narness [--json] [--config <path>]` → parse CLI args
2. `config.ts` finds `.narness.toml` upward from cwd (or via `--config`), parses it into `Config`
3. `engine.ts` iterates checks: look up the checker in the registry → `await check.run(...)` → `CheckResult`
4. collect `CheckResult[]`
5. `report.ts` outputs (human or `--json`)
6. set exit code

## 7. Output format

**human-readable** (default):

```
✔ node >= 22            (actual v22.14.0)
✗ rg not installed       → brew install ripgrep
✗ MCP 'filesystem' not declared → add it to .mcp.json

2 passed, 2 failed
```

**JSON** (`--json`, for hook/CI consumption):

```json
{
  "ok": false,
  "passed": 2,
  "failed": 2,
  "results": [
    { "type": "version", "name": "node", "status": "pass", "detail": "v22.14.0" },
    { "type": "exists", "name": "rg", "status": "fail", "message": "rg not installed", "fix": "brew install ripgrep" }
  ]
}
```

**exit code**:

| Value | Meaning |
|---|---|
| `0` | all passed |
| `1` | some check failed |
| `2` | config or tool error (no .narness.toml, TOML syntax error, unknown type) |

## 8. Error handling

| Scenario | Behavior |
|---|---|
| no `.narness.toml` found | prompt "could not find .narness.toml" + exit 2 |
| TOML syntax error | report the error position + exit 2 |
| unknown `type` | report "unknown check type <type>" + exit 2 |
| a single checker throws (e.g. `node` absent while checking version) | mark `status: "error"`, continue the rest, final exit 1 |

## 9. Testing

- **Unit tests**: `semver` comparison (`"22"` vs `"22.14.0"`, `v` prefix stripping); `exists` probing; `mcp` parsing `.mcp.json`; each checker's `CheckResult` for pass/fail/error
- **Integration tests**: fixture `.narness.toml` + mocked environment (inject fake `command -v` / version command / `.mcp.json`), verifying the engine's aggregation and exit code
- **CLI tests**: `--json` output structure, `--config` path, exit 2 when no config

## 10. Acceptance criteria

1. `cli/` has a buildable TypeScript package (`package.json` + `tsconfig.json` + dependencies)
2. `npx narness` parses `.narness.toml` and correctly judges pass/fail for the three checkers (version/exists/mcp)
3. failures include "where + why + how to fix"; `--json` emits structured results
4. exit code matches section 7 (0/1/2)
5. error handling matches section 8
6. tests cover the three checkers + engine + CLI
7. design doc synced with README/CLAUDE.md (README gains a CLI section)

## 11. Explicitly excluded (YAGNI)

- plugin system (loading local custom checker JS files) — reserved via the `Check` interface, not implemented in the initial phase
- harness-config checks (hook/script existence) — a future checker type, not implemented in the initial phase
- command checker (`[[checks.command]]`) — not implemented in the initial phase
- auto-fix (auto-run install/fix on failure) — report + guide only, no automatic environment mutation
- actual MCP connection verification — config-declaration check only

## 12. Next steps

1. User reviews this design doc
2. Produce an implementation plan via the `writing-plans` skill
3. Implement per the plan
