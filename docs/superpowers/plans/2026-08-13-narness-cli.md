# Narness CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `npx narness` environment checker — read `.narness.toml`, verify the agent's runtime environment with three checker types (version/exists/mcp), give fix guidance on failure, output a human/JSON report and signal the result via exit code.

**Architecture:** A TypeScript npm package in the `cli/` subdirectory of the Narness repo. The core is a unified `Check` interface (extension point) + an engine that iterates `[[checks]]` and dispatches to checkers in a registry. `Context` abstracts running commands / probing tools / reading MCP config, decoupling test mocks from the real implementation.

**Tech Stack:** TypeScript (`tsc` build), vitest (tests), `smol-toml` (TOML parsing), `semver` (version comparison). Zero native runtime dependencies.

**Design doc:** `docs/superpowers/specs/2026-08-13-narness-cli-design.md`

---

### Task 1: Scaffold and dependencies

**Files:**
- Create: `cli/package.json`
- Create: `cli/tsconfig.json`
- Create: `cli/.gitignore`
- Create: `cli/src/`, `cli/tests/` directories

- [ ] **Step 1: Create directories**

```bash
mkdir -p cli/src/checks cli/tests
```

- [ ] **Step 2: Write package.json**

Create `cli/package.json`:

```json
{
  "name": "narness",
  "version": "0.1.0",
  "description": "Narness environment checker — verify agent runtime environment via .narness.toml",
  "type": "module",
  "bin": { "narness": "./dist/index.js" },
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "prepublishOnly": "npm run build"
  },
  "dependencies": {
    "semver": "^7.6.3",
    "smol-toml": "^1.3.1"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "@types/semver": "^7.5.8",
    "typescript": "^5.7.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 3: Write tsconfig.json**

Create `cli/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Write cli/.gitignore**

Create `cli/.gitignore`:

```
node_modules/
dist/
```

- [ ] **Step 5: Install dependencies**

Run: `cd cli && npm install`
Expected: installs successfully with no peer conflict errors.

- [ ] **Step 6: Commit**

```bash
git add cli/package.json cli/tsconfig.json cli/.gitignore cli/package-lock.json
git commit -m "chore(cli): scaffold TypeScript package"
```

---

### Task 2: Check interface and types

**Files:**
- Create: `cli/src/checks/check.ts`

- [ ] **Step 1: Write the type definitions**

Create `cli/src/checks/check.ts`:

```ts
export interface CheckConfig {
  type: string;
  name: string;
  min?: string;
  max?: string;
  names?: string[];
  fix?: string;
}

export type CheckStatus = "pass" | "fail" | "error";

export interface CheckResult {
  status: CheckStatus;
  check: CheckConfig;
  message?: string;
  fix?: string;
  detail?: string;
}

export interface CommandResult {
  code: number;
  stdout: string;
  stderr: string;
}

export interface Context {
  cwd: string;
  runCommand(cmd: string, args: string[]): Promise<CommandResult>;
  which(cmd: string): boolean;
  readMcpServers(): string[];
}

export interface Check {
  run(check: CheckConfig, ctx: Context): Promise<CheckResult>;
}
```

- [ ] **Step 2: Type compile check**

Run: `cd cli && npx tsc --noEmit`
Expected: no errors (check.ts is pure types, so it compiles).

- [ ] **Step 3: Commit**

```bash
git add cli/src/checks/check.ts
git commit -m "feat(cli): add Check interface and types"
```

---

### Task 3: semver version extraction and comparison

**Files:**
- Create: `cli/tests/semver.test.ts`
- Create: `cli/src/semver.ts`

- [ ] **Step 1: Write failing tests**

Create `cli/tests/semver.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { extractVersion, compareVersion } from "../src/semver.js";

describe("extractVersion", () => {
  it("extracts v22.14.0 from node", () => {
    expect(extractVersion("v22.14.0")).toBe("22.14.0");
  });
  it("extracts cargo 1.70.0 (...) from cargo", () => {
    expect(extractVersion("cargo 1.70.0 (abc123 2023-01-01)")).toBe("1.70.0");
  });
  it("extracts git version 2.39.2 from git", () => {
    expect(extractVersion("git version 2.39.2")).toBe("2.39.2");
  });
  it("returns null when no version", () => {
    expect(extractVersion("not a version")).toBeNull();
  });
});

describe("compareVersion", () => {
  it("22.14.0 satisfies min=22", () => {
    expect(compareVersion("22.14.0", "22").ok).toBe(true);
  });
  it("18.0.0 does not satisfy min=22", () => {
    expect(compareVersion("18.0.0", "22").ok).toBe(false);
  });
  it("22 satisfies min=22 (loose format)", () => {
    expect(compareVersion("22", "22").ok).toBe(true);
  });
  it("30.0.0 does not satisfy max=22", () => {
    expect(compareVersion("30.0.0", undefined, "22").ok).toBe(false);
  });
  it("unparseable version returns not ok", () => {
    expect(compareVersion("abc", "22").ok).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd cli && npx vitest run tests/semver.test.ts`
Expected: FAIL (`Cannot find module '../src/semver.js'`)

- [ ] **Step 3: Implement semver.ts**

Create `cli/src/semver.ts`:

```ts
import semver from "semver";

export function extractVersion(output: string): string | null {
  const m = output.match(/\d+\.\d+(\.\d+)?/);
  return m ? m[0] : null;
}

export function compareVersion(
  actual: string,
  min?: string,
  max?: string
): { ok: boolean; reason?: string } {
  const a = semver.coerce(actual);
  if (!a) return { ok: false, reason: `Unable to parse version "${actual}"` };
  if (min) {
    const m = semver.coerce(min);
    if (!m) return { ok: false, reason: `configured min "${min}" is not a valid version` };
    if (semver.lt(a, m)) return { ok: false, reason: `${actual} < ${min}` };
  }
  if (max) {
    const x = semver.coerce(max);
    if (!x) return { ok: false, reason: `configured max "${max}" is not a valid version` };
    if (semver.gt(a, x)) return { ok: false, reason: `${actual} > ${max}` };
  }
  return { ok: true };
}
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `cd cli && npx vitest run tests/semver.test.ts`
Expected: PASS (all 9 tests pass)

- [ ] **Step 5: Commit**

```bash
git add cli/src/semver.ts cli/tests/semver.test.ts
git commit -m "feat(cli): add semver extraction and comparison"
```

---

### Task 4: config location and parsing

**Files:**
- Create: `cli/tests/config.test.ts`
- Create: `cli/src/config.ts`

- [ ] **Step 1: Write failing tests**

Create `cli/tests/config.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { findConfig, loadConfig } from "../src/config.js";

function tmpProject() {
  const dir = mkdtempSync(join(tmpdir(), "narness-"));
  mkdirSync(join(dir, "src"), { recursive: true });
  return dir;
}

describe("findConfig", () => {
  it("finds .narness.toml in the current directory", () => {
    const dir = tmpProject();
    writeFileSync(join(dir, ".narness.toml"), "[[checks]]\ntype=\"exists\"\nname=\"rg\"\n");
    expect(findConfig(dir)).toBe(join(dir, ".narness.toml"));
  });
  it("finds .narness.toml by walking up from a subdirectory", () => {
    const dir = tmpProject();
    writeFileSync(join(dir, ".narness.toml"), "[[checks]]\n");
    expect(findConfig(join(dir, "src"))).toBe(join(dir, ".narness.toml"));
  });
  it("returns null when not found", () => {
    const dir = tmpProject();
    expect(findConfig(dir)).toBeNull();
  });
});

describe("loadConfig", () => {
  it("parses the checks array", () => {
    const dir = tmpProject();
    const p = join(dir, ".narness.toml");
    writeFileSync(p, '[[checks]]\ntype = "version"\nname = "node"\nmin = "22"\n');
    const cfg = loadConfig(p);
    expect(cfg.checks).toHaveLength(1);
    expect(cfg.checks[0]).toEqual({ type: "version", name: "node", min: "22" });
  });
  it("throws when name is missing", () => {
    const dir = tmpProject();
    const p = join(dir, ".narness.toml");
    writeFileSync(p, '[[checks]]\ntype = "version"\n');
    expect(() => loadConfig(p)).toThrow();
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd cli && npx vitest run tests/config.test.ts`
Expected: FAIL (`Cannot find module '../src/config.js'`)

- [ ] **Step 3: Implement config.ts**

Create `cli/src/config.ts`:

```ts
import { parse } from "smol-toml";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import type { CheckConfig } from "./checks/check.js";

export interface Config {
  checks: CheckConfig[];
}

export function findConfig(startDir: string): string | null {
  let dir = startDir;
  for (;;) {
    const p = join(dir, ".narness.toml");
    if (existsSync(p)) return p;
    const parent = dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

export function loadConfig(path: string): Config {
  const raw = readFileSync(path, "utf8");
  let parsed: unknown;
  try {
    parsed = parse(raw);
  } catch (err) {
    throw new Error(`TOML parse failed: ${(err as Error).message}`);
  }
  const obj = (parsed ?? {}) as { checks?: unknown[] };
  const checks = (obj.checks ?? []).map(normalizeCheck);
  return { checks };
}

function normalizeCheck(c: unknown): CheckConfig {
  if (typeof c !== "object" || c === null) {
    throw new Error(`invalid check entry: ${JSON.stringify(c)}`);
  }
  const o = c as Record<string, unknown>;
  if (typeof o.type !== "string" || typeof o.name !== "string") {
    throw new Error(`check is missing type/name: ${JSON.stringify(c)}`);
  }
  return {
    type: o.type,
    name: o.name,
    min: typeof o.min === "string" ? o.min : undefined,
    max: typeof o.max === "string" ? o.max : undefined,
    names: Array.isArray(o.names) ? (o.names as string[]) : undefined,
    fix: typeof o.fix === "string" ? o.fix : undefined,
  };
}
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `cd cli && npx vitest run tests/config.test.ts`
Expected: PASS (all 5 tests pass)

- [ ] **Step 5: Commit**

```bash
git add cli/src/config.ts cli/tests/config.test.ts
git commit -m "feat(cli): add config location and TOML parsing"
```

---

### Task 5: exists checker

**Files:**
- Create: `cli/tests/checks/exists.test.ts`
- Create: `cli/src/checks/exists.ts`

- [ ] **Step 1: Write failing tests**

Create `cli/tests/checks/exists.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { existsCheck } from "../../src/checks/exists.js";
import type { Context } from "../../src/checks/check.js";

function ctx(which: (c: string) => boolean): Context {
  return {
    cwd: "/tmp",
    runCommand: async () => ({ code: 0, stdout: "", stderr: "" }),
    which,
    readMcpServers: () => [],
  };
}

describe("existsCheck", () => {
  it("passes when the tool exists", async () => {
    const r = await existsCheck.run({ type: "exists", name: "rg" }, ctx((c) => c === "rg"));
    expect(r.status).toBe("pass");
  });
  it("fails with a fix when the tool is missing", async () => {
    const r = await existsCheck.run(
      { type: "exists", name: "rg", fix: "brew install ripgrep" },
      ctx(() => false)
    );
    expect(r.status).toBe("fail");
    expect(r.fix).toBe("brew install ripgrep");
  });
  it("checks multiple with a names array", async () => {
    const r = await existsCheck.run(
      { type: "exists", name: "rg", names: ["jq", "git"] },
      ctx((c) => c === "rg" || c === "git")
    );
    expect(r.status).toBe("fail");
    expect(r.message).toContain("jq");
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd cli && npx vitest run tests/checks/exists.test.ts`
Expected: FAIL (`Cannot find module '../../src/checks/exists.js'`)

- [ ] **Step 3: Implement exists.ts**

Create `cli/src/checks/exists.ts`:

```ts
import type { Check, CheckConfig, CheckResult, Context } from "./check.js";

export const existsCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const targets = [check.name, ...(check.names ?? [])];
    const missing = targets.filter((t) => !ctx.which(t));
    if (missing.length === 0) {
      return { status: "pass", check, detail: targets.join(", ") + " installed" };
    }
    const list = missing.join(", ");
    return {
      status: "fail",
      check,
      message: `missing tool(s): ${list}`,
      fix: check.fix ?? `please install ${list}`,
    };
  },
};
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `cd cli && npx vitest run tests/checks/exists.test.ts`
Expected: PASS (all 3 tests pass)

- [ ] **Step 5: Commit**

```bash
git add cli/src/checks/exists.ts cli/tests/checks/exists.test.ts
git commit -m "feat(cli): add exists checker"
```

---

### Task 6: version checker

**Files:**
- Create: `cli/tests/checks/version.test.ts`
- Create: `cli/src/checks/version.ts`

- [ ] **Step 1: Write failing tests**

Create `cli/tests/checks/version.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { versionCheck } from "../../src/checks/version.js";
import type { Context } from "../../src/checks/check.js";

function ctx(stdout: string, code = 0): Context {
  return {
    cwd: "/tmp",
    runCommand: async () => ({ code, stdout, stderr: "" }),
    which: () => true,
    readMcpServers: () => [],
  };
}

describe("versionCheck", () => {
  it("passes when the version satisfies", async () => {
    const r = await versionCheck.run({ type: "version", name: "node", min: "22" }, ctx("v22.14.0"));
    expect(r.status).toBe("pass");
    expect(r.detail).toContain("22.14.0");
  });
  it("fails when the version is too low", async () => {
    const r = await versionCheck.run({ type: "version", name: "node", min: "22" }, ctx("v18.0.0"));
    expect(r.status).toBe("fail");
  });
  it("errors when the command fails", async () => {
    const r = await versionCheck.run({ type: "version", name: "node", min: "22" }, ctx("", 127));
    expect(r.status).toBe("error");
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd cli && npx vitest run tests/checks/version.test.ts`
Expected: FAIL (`Cannot find module '../../src/checks/version.js'`)

- [ ] **Step 3: Implement version.ts**

Create `cli/src/checks/version.ts`:

```ts
import type { Check, CheckConfig, CheckResult, Context } from "./check.js";
import { extractVersion, compareVersion } from "../semver.js";

export const versionCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const res = await ctx.runCommand(check.name, ["--version"]);
    if (res.code !== 0) {
      return {
        status: "error",
        check,
        message: `${check.name} --version failed`,
        fix: check.fix ?? `please install ${check.name} first`,
      };
    }
    const actual = extractVersion(res.stdout);
    if (!actual) {
      return { status: "error", check, message: `unable to parse a version number from "${res.stdout.trim()}"` };
    }
    const cmp = compareVersion(actual, check.min, check.max);
    if (!cmp.ok) {
      const want = [check.min ? `>= ${check.min}` : "", check.max ? `<= ${check.max}` : ""]
        .filter(Boolean)
        .join(" and ");
      return {
        status: "fail",
        check,
        message: `version ${actual} does not meet requirements (needs ${want})`,
        fix: check.fix ?? `please upgrade ${check.name}`,
        detail: cmp.reason,
      };
    }
    return { status: "pass", check, detail: `${check.name} ${actual}` };
  },
};
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `cd cli && npx vitest run tests/checks/version.test.ts`
Expected: PASS (all 3 tests pass)

- [ ] **Step 5: Commit**

```bash
git add cli/src/checks/version.ts cli/tests/checks/version.test.ts
git commit -m "feat(cli): add version checker"
```

---

### Task 7: mcp checker

**Files:**
- Create: `cli/tests/checks/mcp.test.ts`
- Create: `cli/src/checks/mcp.ts`

- [ ] **Step 1: Write failing tests**

Create `cli/tests/checks/mcp.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { mcpCheck } from "../../src/checks/mcp.js";
import type { Context } from "../../src/checks/check.js";

function ctx(servers: string[]): Context {
  return {
    cwd: "/tmp",
    runCommand: async () => ({ code: 0, stdout: "", stderr: "" }),
    which: () => true,
    readMcpServers: () => servers,
  };
}

describe("mcpCheck", () => {
  it("passes when declared", async () => {
    const r = await mcpCheck.run({ type: "mcp", name: "filesystem" }, ctx(["filesystem", "github"]));
    expect(r.status).toBe("pass");
  });
  it("fails with a fix when not declared", async () => {
    const r = await mcpCheck.run({ type: "mcp", name: "filesystem" }, ctx(["github"]));
    expect(r.status).toBe("fail");
    expect(r.fix).toContain(".mcp.json");
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd cli && npx vitest run tests/checks/mcp.test.ts`
Expected: FAIL (`Cannot find module '../../src/checks/mcp.js'`)

- [ ] **Step 3: Implement mcp.ts**

Create `cli/src/checks/mcp.ts`:

```ts
import type { Check, CheckConfig, CheckResult, Context } from "./check.js";

export const mcpCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const servers = ctx.readMcpServers();
    if (servers.includes(check.name)) {
      return { status: "pass", check, detail: `MCP '${check.name}' declared` };
    }
    return {
      status: "fail",
      check,
      message: `MCP '${check.name}' not declared`,
      fix: check.fix ?? `add '${check.name}' to mcpServers in .mcp.json`,
    };
  },
};
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `cd cli && npx vitest run tests/checks/mcp.test.ts`
Expected: PASS (all 2 tests pass)

- [ ] **Step 5: Commit**

```bash
git add cli/src/checks/mcp.ts cli/tests/checks/mcp.test.ts
git commit -m "feat(cli): add mcp checker"
```

---

### Task 8: registry and engine

**Files:**
- Create: `cli/tests/engine.test.ts`
- Create: `cli/src/registry.ts`
- Create: `cli/src/engine.ts`

- [ ] **Step 1: Write failing tests**

Create `cli/tests/engine.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { runChecks } from "../src/engine.js";
import type { Config } from "../src/config.js";
import type { Context } from "../src/checks/check.js";

function ctx(over: Partial<Context> = {}): Context {
  return {
    cwd: "/tmp",
    runCommand: async () => ({ code: 0, stdout: "v22.14.0", stderr: "" }),
    which: () => true,
    readMcpServers: () => ["filesystem"],
    ...over,
  };
}

describe("runChecks", () => {
  it("runs all checks", async () => {
    const cfg: Config = {
      checks: [
        { type: "version", name: "node", min: "22" },
        { type: "exists", name: "rg" },
      ],
    };
    const results = await runChecks(cfg, ctx());
    expect(results).toHaveLength(2);
    expect(results.every((r) => r.status === "pass")).toBe(true);
  });
  it("marks error on unknown type", async () => {
    const cfg: Config = { checks: [{ type: "nope", name: "x" }] };
    const results = await runChecks(cfg, ctx());
    expect(results[0].status).toBe("error");
    expect(results[0].message).toContain("unknown check type");
  });
  it("marks error and continues when a checker throws", async () => {
    const cfg: Config = {
      checks: [
        { type: "exists", name: "a" },
        { type: "exists", name: "b" },
      ],
    };
    const throwing: Context = ctx({ which: (c) => {
      if (c === "a") throw new Error("boom");
      return true;
    }});
    const results = await runChecks(cfg, throwing);
    expect(results[0].status).toBe("error");
    expect(results[1].status).toBe("pass");
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd cli && npx vitest run tests/engine.test.ts`
Expected: FAIL (`Cannot find module '../src/engine.js'`)

- [ ] **Step 3: Implement registry.ts**

Create `cli/src/registry.ts`:

```ts
import type { Check } from "./checks/check.js";
import { versionCheck } from "./checks/version.js";
import { existsCheck } from "./checks/exists.js";
import { mcpCheck } from "./checks/mcp.js";

export const registry: Record<string, Check> = {
  version: versionCheck,
  exists: existsCheck,
  mcp: mcpCheck,
};

export function getCheck(type: string): Check | undefined {
  return registry[type];
}
```

- [ ] **Step 4: Implement engine.ts**

Create `cli/src/engine.ts`:

```ts
import type { Config } from "./config.js";
import type { CheckResult, Context } from "./checks/check.js";
import { getCheck } from "./registry.js";

export async function runChecks(config: Config, ctx: Context): Promise<CheckResult[]> {
  const results: CheckResult[] = [];
  for (const check of config.checks) {
    const impl = getCheck(check.type);
    if (!impl) {
      results.push({ status: "error", check, message: `unknown check type "${check.type}"` });
      continue;
    }
    try {
      results.push(await impl.run(check, ctx));
    } catch (err) {
      results.push({ status: "error", check, message: `checker error: ${(err as Error).message}` });
    }
  }
  return results;
}
```

- [ ] **Step 5: Run tests to confirm they pass**

Run: `cd cli && npx vitest run tests/engine.test.ts`
Expected: PASS (all 3 tests pass)

- [ ] **Step 6: Commit**

```bash
git add cli/src/registry.ts cli/src/engine.ts cli/tests/engine.test.ts
git commit -m "feat(cli): add registry and engine"
```

---

### Task 9: Report formatting

**Files:**
- Create: `cli/tests/report.test.ts`
- Create: `cli/src/report.ts`

- [ ] **Step 1: Write failing tests**

Create `cli/tests/report.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { reportHuman, reportJson } from "../src/report.js";
import type { CheckResult } from "../src/checks/check.js";

const results: CheckResult[] = [
  { status: "pass", check: { type: "version", name: "node" }, detail: "node 22.14.0" },
  { status: "fail", check: { type: "exists", name: "rg" }, message: "missing tool(s): rg", fix: "brew install ripgrep" },
];

describe("reportHuman", () => {
  it("includes pass/fail marks and fix suggestions", () => {
    const out = reportHuman(results);
    expect(out).toContain("✔");
    expect(out).toContain("✗");
    expect(out).toContain("brew install ripgrep");
    expect(out).toContain("1 passed, 1 failed");
  });
});

describe("reportJson", () => {
  it("emits parseable structured JSON", () => {
    const out = reportJson(results);
    const obj = JSON.parse(out);
    expect(obj.ok).toBe(false);
    expect(obj.passed).toBe(1);
    expect(obj.failed).toBe(1);
    expect(obj.results).toHaveLength(2);
    expect(obj.results[1].fix).toBe("brew install ripgrep");
  });
});
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd cli && npx vitest run tests/report.test.ts`
Expected: FAIL (`Cannot find module '../src/report.js'`)

- [ ] **Step 3: Implement report.ts**

Create `cli/src/report.ts`:

```ts
import type { CheckResult } from "./checks/check.js";

export function reportHuman(results: CheckResult[]): string {
  const lines = results.map((r) => {
    const name = r.check.name;
    if (r.status === "pass") {
      return `✔ ${name}${r.detail ? " (" + r.detail + ")" : ""}`;
    }
    const mark = r.status === "error" ? "⚠" : "✗";
    const parts = [`${mark} ${name}`];
    if (r.message) parts.push(r.message);
    if (r.fix) parts.push(`→ ${r.fix}`);
    return parts.join("  ");
  });
  const passed = results.filter((r) => r.status === "pass").length;
  const failed = results.length - passed;
  lines.push("", `${passed} passed, ${failed} failed`);
  return lines.join("\n");
}

export function reportJson(results: CheckResult[]): string {
  const passed = results.filter((r) => r.status === "pass").length;
  const failed = results.length - passed;
  return JSON.stringify(
    {
      ok: failed === 0,
      passed,
      failed,
      results: results.map((r) => ({
        type: r.check.type,
        name: r.check.name,
        status: r.status,
        message: r.message,
        fix: r.fix,
        detail: r.detail,
      })),
    },
    null,
    2
  );
}
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `cd cli && npx vitest run tests/report.test.ts`
Expected: PASS (all 3 tests pass)

- [ ] **Step 5: Commit**

```bash
git add cli/src/report.ts cli/tests/report.test.ts
git commit -m "feat(cli): add report formatting"
```

---

### Task 10: CLI entrypoint and real Context

**Files:**
- Create: `cli/src/index.ts`

- [ ] **Step 1: Implement the real Context and the CLI entrypoint**

Create `cli/src/index.ts`:

```ts
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { findConfig, loadConfig } from "./config.js";
import { runChecks } from "./engine.js";
import { reportHuman, reportJson } from "./report.js";
import type { Context } from "./checks/check.js";

function realContext(cwd: string): Context {
  return {
    cwd,
    runCommand(cmd, args) {
      try {
        const stdout = execFileSync(cmd, args, { encoding: "utf8" });
        return Promise.resolve({ code: 0, stdout, stderr: "" });
      } catch (err) {
        const e = err as { status?: number; stdout?: string; stderr?: string };
        return Promise.resolve({ code: e.status ?? 1, stdout: e.stdout ?? "", stderr: e.stderr ?? "" });
      }
    },
    which(cmd) {
      try {
        execFileSync("command", ["-v", cmd], { stdio: "ignore" });
        return true;
      } catch {
        return false;
      }
    },
    readMcpServers() {
      const p = resolve(cwd, ".mcp.json");
      if (!existsSync(p)) return [];
      try {
        const data = JSON.parse(readFileSync(p, "utf8")) as { mcpServers?: Record<string, unknown> };
        return Object.keys(data.mcpServers ?? {});
      } catch {
        return [];
      }
    },
  };
}

function parseArgs(argv: string[]) {
  const json = argv.includes("--json");
  const configFlag = argv.find((a) => a.startsWith("--config="));
  const configPath = configFlag ? configFlag.slice("--config=".length) : undefined;
  return { json, configPath };
}

async function main() {
  const { json, configPath } = parseArgs(process.argv.slice(2));
  const cwd = process.cwd();

  const path = configPath ? resolve(configPath) : findConfig(cwd);
  if (!path) {
    console.error("Could not find .narness.toml (searched upward from the current directory)");
    process.exit(2);
  }

  let config;
  try {
    config = loadConfig(path);
  } catch (err) {
    console.error(`Config parse failed: ${(err as Error).message}`);
    process.exit(2);
  }

  const results = await runChecks(config, realContext(cwd));
  console.log(json ? reportJson(results) : reportHuman(results));

  const failed = results.some((r) => r.status !== "pass");
  process.exit(failed ? 1 : 0);
}

main();
```

- [ ] **Step 2: Build**

Run: `cd cli && npm run build`
Expected: compiles successfully, producing `cli/dist/index.js`.

- [ ] **Step 3: Manual smoke test**

Run:
```bash
tmp=$(mktemp -d)
cd "$tmp"
printf '[[checks]]\ntype = "version"\nname = "node"\nmin = "18"\n\n[[checks]]\ntype = "exists"\nname = "git"\n' > .narness.toml
node /Users/nathan/workspace/narness-engineering/cli/dist/index.js; echo "exit=$?"
rm -rf "$tmp"
```
Expected: output `✔ node`, `✔ git`, ending with `2 passed, 0 failed`, `exit=0`.

- [ ] **Step 4: Commit**

```bash
git add cli/src/index.ts
git commit -m "feat(cli): add CLI entrypoint with real context"
```

---

### Task 11: CLI integration tests and wrap-up

**Files:**
- Create: `cli/tests/cli.test.ts`

- [ ] **Step 1: Write integration tests**

Create `cli/tests/cli.test.ts`:

```ts
import { describe, it, expect, beforeAll } from "vitest";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const distIndex = fileURLToPath(new URL("../dist/index.js", import.meta.url));

function runIn(fixture: string, args: string[] = []) {
  try {
    const stdout = execFileSync("node", [distIndex, ...args], { cwd: fixture, encoding: "utf8" });
    return { code: 0, stdout, stderr: "" };
  } catch (err) {
    const e = err as { status?: number; stdout?: string; stderr?: string };
    return { code: e.status ?? 1, stdout: e.stdout ?? "", stderr: e.stderr ?? "" };
  }
}

describe("CLI integration", () => {
  let dir: string;
  beforeAll(() => {
    dir = mkdtempSync(join(tmpdir(), "narness-cli-"));
  });

  it("exits 0 when all pass", () => {
    writeFileSync(join(dir, ".narness.toml"), '[[checks]]\ntype = "version"\nname = "node"\nmin = "18"\n');
    const r = runIn(dir);
    expect(r.code).toBe(0);
    expect(r.stdout).toContain("✔");
  });

  it("exits 1 on failure", () => {
    writeFileSync(join(dir, ".narness.toml"), '[[checks]]\ntype = "exists"\nname = "definitely-not-a-real-cmd-xyz"\n');
    const r = runIn(dir);
    expect(r.code).toBe(1);
    expect(r.stdout).toContain("✗");
  });

  it("--json emits structured output", () => {
    writeFileSync(join(dir, ".narness.toml"), '[[checks]]\ntype = "exists"\nname = "git"\n');
    const r = runIn(dir, ["--json"]);
    expect(r.code).toBe(0);
    const obj = JSON.parse(r.stdout);
    expect(obj.ok).toBe(true);
    expect(obj.results[0].name).toBe("git");
  });

  it("exits 2 with no config", () => {
    const empty = mkdtempSync(join(tmpdir(), "narness-empty-"));
    const r = runIn(empty);
    expect(r.code).toBe(2);
  });
});
```

- [ ] **Step 2: Build then run integration tests**

Run: `cd cli && npm run build && npx vitest run tests/cli.test.ts`
Expected: PASS (all 4 tests pass)

- [ ] **Step 3: Run the full test suite**

Run: `cd cli && npm test`
Expected: all tests pass (semver 9 + config 5 + exists 3 + version 3 + mcp 2 + engine 3 + report 3 + cli 4 = 32)

- [ ] **Step 4: Commit**

```bash
git add cli/tests/cli.test.ts
git commit -m "test(cli): add CLI integration tests"
```

---

### Task 12: Docs sync and final verification

- [ ] **Step 1: Add CLI documentation to README**

Two edits:

1. Add one line to the "Layout" list: `- \`cli/\` — the narness environment checker (npm package)`
2. Append an "Environment check" section at the end of the file, containing: a note that `cli/` is an npm package; a `.narness.toml` example (one `version` check + one `exists` check); the two commands and their purposes — `npx narness` (human report) and `npx narness --json` (structured output, for hooks/CI).

- [ ] **Step 2: Final verification**

Run:
```bash
cd cli && npm run build && npm test
git status --short
```
Expected: build succeeds, all 32 tests pass, working tree has nothing left out (except the README change to be committed).

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: document narness CLI in README"
git push origin main
```
