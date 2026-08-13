# Narness CLI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `npx narness` 环境检查器——读取 `.narness.toml`，用 version/exists/mcp 三类检查器验证 agent 运行环境，失败时给出修复引导，输出 human/JSON 报告并以 exit code 反馈。

**Architecture:** TypeScript npm 包放 Narness 仓库 `cli/` 子目录。核心是统一 `Check` 接口（扩展点）+ 引擎遍历 `[[checks]]` 并 dispatch 到注册表里的检查器。`Context` 抽象运行命令/探测工具/读 MCP 配置，便于测试 mock 与真实实现解耦。

**Tech Stack:** TypeScript（`tsc` 构建）、vitest（测试）、`smol-toml`（TOML 解析）、`semver`（版本比较）。运行时零原生依赖。

**设计文档:** `docs/superpowers/specs/2026-08-13-narness-cli-design.md`

---

### Task 1: 脚手架与依赖

**Files:**
- Create: `cli/package.json`
- Create: `cli/tsconfig.json`
- Create: `cli/.gitignore`
- Create: `cli/src/`、`cli/tests/` 目录

- [ ] **Step 1: 创建目录**

```bash
mkdir -p cli/src/checks cli/tests
```

- [ ] **Step 2: 写 package.json**

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

- [ ] **Step 3: 写 tsconfig.json**

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

- [ ] **Step 4: 写 cli/.gitignore**

Create `cli/.gitignore`:

```
node_modules/
dist/
```

- [ ] **Step 5: 安装依赖**

Run: `cd cli && npm install`
Expected: 安装成功，无 peer 冲突报错。

- [ ] **Step 6: Commit**

```bash
git add cli/package.json cli/tsconfig.json cli/.gitignore cli/package-lock.json
git commit -m "chore(cli): scaffold TypeScript package"
```

---

### Task 2: Check 接口与类型

**Files:**
- Create: `cli/src/checks/check.ts`

- [ ] **Step 1: 写类型定义**

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

- [ ] **Step 2: 类型编译检查**

Run: `cd cli && npx tsc --noEmit`
Expected: 无错误（check.ts 是纯类型，能通过编译）。

- [ ] **Step 3: Commit**

```bash
git add cli/src/checks/check.ts
git commit -m "feat(cli): add Check interface and types"
```

---

### Task 3: semver 版本提取与比较

**Files:**
- Create: `cli/tests/semver.test.ts`
- Create: `cli/src/semver.ts`

- [ ] **Step 1: 写失败测试**

Create `cli/tests/semver.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { extractVersion, compareVersion } from "../src/semver.js";

describe("extractVersion", () => {
  it("提取 node 的 v22.14.0", () => {
    expect(extractVersion("v22.14.0")).toBe("22.14.0");
  });
  it("提取 cargo 的 cargo 1.70.0 (...)", () => {
    expect(extractVersion("cargo 1.70.0 (abc123 2023-01-01)")).toBe("1.70.0");
  });
  it("提取 git 的 git version 2.39.2", () => {
    expect(extractVersion("git version 2.39.2")).toBe("2.39.2");
  });
  it("无版本号返回 null", () => {
    expect(extractVersion("not a version")).toBeNull();
  });
});

describe("compareVersion", () => {
  it("22.14.0 满足 min=22", () => {
    expect(compareVersion("22.14.0", "22").ok).toBe(true);
  });
  it("18.0.0 不满足 min=22", () => {
    expect(compareVersion("18.0.0", "22").ok).toBe(false);
  });
  it("22 满足 min=22（宽松格式）", () => {
    expect(compareVersion("22", "22").ok).toBe(true);
  });
  it("30.0.0 不满足 max=22", () => {
    expect(compareVersion("30.0.0", undefined, "22").ok).toBe(false);
  });
  it("无法解析的版本返回不 ok", () => {
    expect(compareVersion("abc", "22").ok).toBe(false);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd cli && npx vitest run tests/semver.test.ts`
Expected: FAIL（`Cannot find module '../src/semver.js'`）

- [ ] **Step 3: 实现 semver.ts**

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
  if (!a) return { ok: false, reason: `无法解析版本 "${actual}"` };
  if (min) {
    const m = semver.coerce(min);
    if (!m) return { ok: false, reason: `配置的 min "${min}" 不是合法版本` };
    if (semver.lt(a, m)) return { ok: false, reason: `${actual} < ${min}` };
  }
  if (max) {
    const x = semver.coerce(max);
    if (!x) return { ok: false, reason: `配置的 max "${max}" 不是合法版本` };
    if (semver.gt(a, x)) return { ok: false, reason: `${actual} > ${max}` };
  }
  return { ok: true };
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd cli && npx vitest run tests/semver.test.ts`
Expected: PASS（9 个测试全过）

- [ ] **Step 5: Commit**

```bash
git add cli/src/semver.ts cli/tests/semver.test.ts
git commit -m "feat(cli): add semver extraction and comparison"
```

---

### Task 4: config 定位与解析

**Files:**
- Create: `cli/tests/config.test.ts`
- Create: `cli/src/config.ts`

- [ ] **Step 1: 写失败测试**

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
  it("在当前目录找到 .narness.toml", () => {
    const dir = tmpProject();
    writeFileSync(join(dir, ".narness.toml"), "[[checks]]\ntype=\"exists\"\nname=\"rg\"\n");
    expect(findConfig(dir)).toBe(join(dir, ".narness.toml"));
  });
  it("从子目录向上找到 .narness.toml", () => {
    const dir = tmpProject();
    writeFileSync(join(dir, ".narness.toml"), "[[checks]]\n");
    expect(findConfig(join(dir, "src"))).toBe(join(dir, ".narness.toml"));
  });
  it("找不到返回 null", () => {
    const dir = tmpProject();
    expect(findConfig(dir)).toBeNull();
  });
});

describe("loadConfig", () => {
  it("解析 checks 数组", () => {
    const dir = tmpProject();
    const p = join(dir, ".narness.toml");
    writeFileSync(p, '[[checks]]\ntype = "version"\nname = "node"\nmin = "22"\n');
    const cfg = loadConfig(p);
    expect(cfg.checks).toHaveLength(1);
    expect(cfg.checks[0]).toEqual({ type: "version", name: "node", min: "22" });
  });
  it("缺失 name 抛错", () => {
    const dir = tmpProject();
    const p = join(dir, ".narness.toml");
    writeFileSync(p, '[[checks]]\ntype = "version"\n');
    expect(() => loadConfig(p)).toThrow();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd cli && npx vitest run tests/config.test.ts`
Expected: FAIL（`Cannot find module '../src/config.js'`）

- [ ] **Step 3: 实现 config.ts**

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
    throw new Error(`TOML 解析失败: ${(err as Error).message}`);
  }
  const obj = (parsed ?? {}) as { checks?: unknown[] };
  const checks = (obj.checks ?? []).map(normalizeCheck);
  return { checks };
}

function normalizeCheck(c: unknown): CheckConfig {
  if (typeof c !== "object" || c === null) {
    throw new Error(`无效的 check 条目: ${JSON.stringify(c)}`);
  }
  const o = c as Record<string, unknown>;
  if (typeof o.type !== "string" || typeof o.name !== "string") {
    throw new Error(`check 缺少 type/name: ${JSON.stringify(c)}`);
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

- [ ] **Step 4: 跑测试确认通过**

Run: `cd cli && npx vitest run tests/config.test.ts`
Expected: PASS（5 个测试全过）

- [ ] **Step 5: Commit**

```bash
git add cli/src/config.ts cli/tests/config.test.ts
git commit -m "feat(cli): add config location and TOML parsing"
```

---

### Task 5: exists 检查器

**Files:**
- Create: `cli/tests/checks/exists.test.ts`
- Create: `cli/src/checks/exists.ts`

- [ ] **Step 1: 写失败测试**

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
  it("工具存在则 pass", async () => {
    const r = await existsCheck.run({ type: "exists", name: "rg" }, ctx((c) => c === "rg"));
    expect(r.status).toBe("pass");
  });
  it("工具缺失则 fail 且带 fix", async () => {
    const r = await existsCheck.run(
      { type: "exists", name: "rg", fix: "brew install ripgrep" },
      ctx(() => false)
    );
    expect(r.status).toBe("fail");
    expect(r.fix).toBe("brew install ripgrep");
  });
  it("names 数组一次检查多个", async () => {
    const r = await existsCheck.run(
      { type: "exists", name: "rg", names: ["jq", "git"] },
      ctx((c) => c === "rg" || c === "git")
    );
    expect(r.status).toBe("fail");
    expect(r.message).toContain("jq");
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd cli && npx vitest run tests/checks/exists.test.ts`
Expected: FAIL（`Cannot find module '../../src/checks/exists.js'`）

- [ ] **Step 3: 实现 exists.ts**

Create `cli/src/checks/exists.ts`:

```ts
import type { Check, CheckConfig, CheckResult, Context } from "./check.js";

export const existsCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const targets = [check.name, ...(check.names ?? [])];
    const missing = targets.filter((t) => !ctx.which(t));
    if (missing.length === 0) {
      return { status: "pass", check, detail: targets.join(", ") + " 已安装" };
    }
    const list = missing.join(", ");
    return {
      status: "fail",
      check,
      message: `缺少工具: ${list}`,
      fix: check.fix ?? `请安装 ${list}`,
    };
  },
};
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd cli && npx vitest run tests/checks/exists.test.ts`
Expected: PASS（3 个测试全过）

- [ ] **Step 5: Commit**

```bash
git add cli/src/checks/exists.ts cli/tests/checks/exists.test.ts
git commit -m "feat(cli): add exists checker"
```

---

### Task 6: version 检查器

**Files:**
- Create: `cli/tests/checks/version.test.ts`
- Create: `cli/src/checks/version.ts`

- [ ] **Step 1: 写失败测试**

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
  it("版本满足则 pass", async () => {
    const r = await versionCheck.run({ type: "version", name: "node", min: "22" }, ctx("v22.14.0"));
    expect(r.status).toBe("pass");
    expect(r.detail).toContain("22.14.0");
  });
  it("版本过低则 fail", async () => {
    const r = await versionCheck.run({ type: "version", name: "node", min: "22" }, ctx("v18.0.0"));
    expect(r.status).toBe("fail");
  });
  it("命令执行失败则 error", async () => {
    const r = await versionCheck.run({ type: "version", name: "node", min: "22" }, ctx("", 127));
    expect(r.status).toBe("error");
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd cli && npx vitest run tests/checks/version.test.ts`
Expected: FAIL（`Cannot find module '../../src/checks/version.js'`）

- [ ] **Step 3: 实现 version.ts**

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
        message: `${check.name} --version 执行失败`,
        fix: check.fix ?? `请先安装 ${check.name}`,
      };
    }
    const actual = extractVersion(res.stdout);
    if (!actual) {
      return { status: "error", check, message: `无法从 "${res.stdout.trim()}" 解析版本号` };
    }
    const cmp = compareVersion(actual, check.min, check.max);
    if (!cmp.ok) {
      const want = [check.min ? `>= ${check.min}` : "", check.max ? `<= ${check.max}` : ""]
        .filter(Boolean)
        .join(" 且 ");
      return {
        status: "fail",
        check,
        message: `${check.name} 版本 ${actual} 不满足要求（需 ${want}）`,
        fix: check.fix ?? `请升级 ${check.name}`,
        detail: cmp.reason,
      };
    }
    return { status: "pass", check, detail: `${check.name} ${actual}` };
  },
};
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd cli && npx vitest run tests/checks/version.test.ts`
Expected: PASS（3 个测试全过）

- [ ] **Step 5: Commit**

```bash
git add cli/src/checks/version.ts cli/tests/checks/version.test.ts
git commit -m "feat(cli): add version checker"
```

---

### Task 7: mcp 检查器

**Files:**
- Create: `cli/tests/checks/mcp.test.ts`
- Create: `cli/src/checks/mcp.ts`

- [ ] **Step 1: 写失败测试**

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
  it("已声明则 pass", async () => {
    const r = await mcpCheck.run({ type: "mcp", name: "filesystem" }, ctx(["filesystem", "github"]));
    expect(r.status).toBe("pass");
  });
  it("未声明则 fail 且带 fix", async () => {
    const r = await mcpCheck.run({ type: "mcp", name: "filesystem" }, ctx(["github"]));
    expect(r.status).toBe("fail");
    expect(r.fix).toContain(".mcp.json");
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd cli && npx vitest run tests/checks/mcp.test.ts`
Expected: FAIL（`Cannot find module '../../src/checks/mcp.js'`）

- [ ] **Step 3: 实现 mcp.ts**

Create `cli/src/checks/mcp.ts`:

```ts
import type { Check, CheckConfig, CheckResult, Context } from "./check.js";

export const mcpCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const servers = ctx.readMcpServers();
    if (servers.includes(check.name)) {
      return { status: "pass", check, detail: `MCP '${check.name}' 已声明` };
    }
    return {
      status: "fail",
      check,
      message: `MCP '${check.name}' 未声明`,
      fix: check.fix ?? `请在 .mcp.json 的 mcpServers 中添加 '${check.name}'`,
    };
  },
};
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd cli && npx vitest run tests/checks/mcp.test.ts`
Expected: PASS（2 个测试全过）

- [ ] **Step 5: Commit**

```bash
git add cli/src/checks/mcp.ts cli/tests/checks/mcp.test.ts
git commit -m "feat(cli): add mcp checker"
```

---

### Task 8: registry 与 engine

**Files:**
- Create: `cli/tests/engine.test.ts`
- Create: `cli/src/registry.ts`
- Create: `cli/src/engine.ts`

- [ ] **Step 1: 写失败测试**

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
  it("遍历所有 checks", async () => {
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
  it("未知 type 标记 error", async () => {
    const cfg: Config = { checks: [{ type: "nope", name: "x" }] };
    const results = await runChecks(cfg, ctx());
    expect(results[0].status).toBe("error");
    expect(results[0].message).toContain("未知检查类型");
  });
  it("检查器抛异常标记 error 且继续", async () => {
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

- [ ] **Step 2: 跑测试确认失败**

Run: `cd cli && npx vitest run tests/engine.test.ts`
Expected: FAIL（`Cannot find module '../src/engine.js'`）

- [ ] **Step 3: 实现 registry.ts**

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

- [ ] **Step 4: 实现 engine.ts**

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
      results.push({ status: "error", check, message: `未知检查类型 "${check.type}"` });
      continue;
    }
    try {
      results.push(await impl.run(check, ctx));
    } catch (err) {
      results.push({ status: "error", check, message: `检查器异常: ${(err as Error).message}` });
    }
  }
  return results;
}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd cli && npx vitest run tests/engine.test.ts`
Expected: PASS（3 个测试全过）

- [ ] **Step 6: Commit**

```bash
git add cli/src/registry.ts cli/src/engine.ts cli/tests/engine.test.ts
git commit -m "feat(cli): add registry and engine"
```

---

### Task 9: 报告格式化

**Files:**
- Create: `cli/tests/report.test.ts`
- Create: `cli/src/report.ts`

- [ ] **Step 1: 写失败测试**

Create `cli/tests/report.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { reportHuman, reportJson } from "../src/report.js";
import type { CheckResult } from "../src/checks/check.js";

const results: CheckResult[] = [
  { status: "pass", check: { type: "version", name: "node" }, detail: "node 22.14.0" },
  { status: "fail", check: { type: "exists", name: "rg" }, message: "缺少工具: rg", fix: "brew install ripgrep" },
];

describe("reportHuman", () => {
  it("含 pass/fail 标记与修复建议", () => {
    const out = reportHuman(results);
    expect(out).toContain("✔");
    expect(out).toContain("✗");
    expect(out).toContain("brew install ripgrep");
    expect(out).toContain("1 passed, 1 failed");
  });
});

describe("reportJson", () => {
  it("输出可解析的结构化 JSON", () => {
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

- [ ] **Step 2: 跑测试确认失败**

Run: `cd cli && npx vitest run tests/report.test.ts`
Expected: FAIL（`Cannot find module '../src/report.js'`）

- [ ] **Step 3: 实现 report.ts**

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

- [ ] **Step 4: 跑测试确认通过**

Run: `cd cli && npx vitest run tests/report.test.ts`
Expected: PASS（3 个测试全过）

- [ ] **Step 5: Commit**

```bash
git add cli/src/report.ts cli/tests/report.test.ts
git commit -m "feat(cli): add report formatting"
```

---

### Task 10: CLI 入口与真实 Context

**Files:**
- Create: `cli/src/index.ts`

- [ ] **Step 1: 实现真实 Context 与 CLI 入口**

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
    console.error("未找到 .narness.toml（已从当前目录向上查找）");
    process.exit(2);
  }

  let config;
  try {
    config = loadConfig(path);
  } catch (err) {
    console.error(`配置解析失败: ${(err as Error).message}`);
    process.exit(2);
  }

  const results = await runChecks(config, realContext(cwd));
  console.log(json ? reportJson(results) : reportHuman(results));

  const failed = results.some((r) => r.status !== "pass");
  process.exit(failed ? 1 : 0);
}

main();
```

- [ ] **Step 2: 构建**

Run: `cd cli && npm run build`
Expected: 编译成功，生成 `cli/dist/index.js`。

- [ ] **Step 3: 手工冒烟测试**

Run:
```bash
tmp=$(mktemp -d)
cd "$tmp"
printf '[[checks]]\ntype = "version"\nname = "node"\nmin = "18"\n\n[[checks]]\ntype = "exists"\nname = "git"\n' > .narness.toml
node /Users/nathan/workspace/narness-engineering/cli/dist/index.js; echo "exit=$?"
rm -rf "$tmp"
```
Expected: 输出 `✔ node`、`✔ git`，末尾 `2 passed, 0 failed`，`exit=0`。

- [ ] **Step 4: Commit**

```bash
git add cli/src/index.ts
git commit -m "feat(cli): add CLI entrypoint with real context"
```

---

### Task 11: CLI 集成测试与收尾

**Files:**
- Create: `cli/tests/cli.test.ts`

- [ ] **Step 1: 写集成测试**

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

describe("CLI 集成", () => {
  let dir: string;
  beforeAll(() => {
    dir = mkdtempSync(join(tmpdir(), "narness-cli-"));
  });

  it("全部通过则 exit 0", () => {
    writeFileSync(join(dir, ".narness.toml"), '[[checks]]\ntype = "version"\nname = "node"\nmin = "18"\n');
    const r = runIn(dir);
    expect(r.code).toBe(0);
    expect(r.stdout).toContain("✔");
  });

  it("有失败则 exit 1", () => {
    writeFileSync(join(dir, ".narness.toml"), '[[checks]]\ntype = "exists"\nname = "definitely-not-a-real-cmd-xyz"\n');
    const r = runIn(dir);
    expect(r.code).toBe(1);
    expect(r.stdout).toContain("✗");
  });

  it("--json 输出结构化", () => {
    writeFileSync(join(dir, ".narness.toml"), '[[checks]]\ntype = "exists"\nname = "git"\n');
    const r = runIn(dir, ["--json"]);
    expect(r.code).toBe(0);
    const obj = JSON.parse(r.stdout);
    expect(obj.ok).toBe(true);
    expect(obj.results[0].name).toBe("git");
  });

  it("无配置则 exit 2", () => {
    const empty = mkdtempSync(join(tmpdir(), "narness-empty-"));
    const r = runIn(empty);
    expect(r.code).toBe(2);
  });
});
```

- [ ] **Step 2: 构建后跑集成测试**

Run: `cd cli && npm run build && npx vitest run tests/cli.test.ts`
Expected: PASS（4 个测试全过）

- [ ] **Step 3: 跑全量测试**

Run: `cd cli && npm test`
Expected: 全部测试通过（semver 9 + config 5 + exists 3 + version 3 + mcp 2 + engine 3 + report 3 + cli 4 = 32 个）

- [ ] **Step 4: Commit**

```bash
git add cli/tests/cli.test.ts
git commit -m "test(cli): add CLI integration tests"
```

---

### Task 12: 文档同步与最终验证

- [ ] **Step 1: README 加 CLI 说明**

两处修改：

1. 「目录」列表加一行：`- \`cli/\` — narness 环境检查器（npm 包）`
2. 文件末尾追加「环境检查」一节，包含：说明 `cli/` 是 npm 包；`.narness.toml` 示例（一个 `version` check + 一个 `exists` check）；`npx narness`（human 报告）与 `npx narness --json`（结构化输出，供 hook/CI）两个命令及用途。

- [ ] **Step 2: 最终验证**

Run:
```bash
cd cli && npm run build && npm test
git status --short
```
Expected: 构建成功、32 个测试全过、工作区无遗漏（除待提交的 README 变更）。

- [ ] **Step 3: Commit 并推送**

```bash
git add README.md
git commit -m "docs: document narness CLI in README"
git push origin main
```
