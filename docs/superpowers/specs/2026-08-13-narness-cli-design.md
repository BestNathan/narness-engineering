# Narness CLI — 环境检查器设计文档

- 日期：2026-08-13
- 状态：已批准设计（方案 A：声明式 TOML + 内置检查器 + 统一 Check 接口）

## 1. 概述

Narness CLI 是一个 **preflight 环境检查器**：项目根目录放一个 `.narness.toml` 配置文件，声明 agent 运行环境必须满足的要求；运行 `npx narness` 逐项检查，检查失败时给出「哪里失败 + 为什么 + 怎么修」的修复引导，并以结构化输出（human + JSON）和明确 exit code 反馈。

**核心理念**（延续 Narness 的 harness 工程化思想）：环境约束不应停留在文档里（「你需要 node 22」），而应下沉为可执行、可验证、能给 LLM 反馈的检查器。

**定位**：环境检查为主，harness 配置检查作为可扩展类型（架构上通过 `Check` 接口预留，首期不实现）。

## 2. 技术栈与依赖

- **TypeScript / Node.js**，`npx narness` 直接运行
- 依赖（最小化）：
  - `smol-toml` — TOML 解析
  - `semver` — 版本比较
- 无运行时原生依赖，纯 JS

## 3. 配置 schema（`.narness.toml`）

项目根目录放 `.narness.toml`，顶层 `[[checks]]` 数组，每项一个检查。

```toml
# .narness.toml

# 版本检查：命令版本需满足 min/max（semver）
[[checks]]
type = "version"
name = "node"
min = "22"

# 存在性检查：shell 工具必须可执行
[[checks]]
type = "exists"
name = "rg"

[[checks]]
type = "exists"
name = "jq"

# MCP 检查：MCP 配置里必须声明该 server
[[checks]]
type = "mcp"
name = "filesystem"
```

### 3.1 字段定义

每个 check 的通用字段：

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `type` | string | 是 | `"version"` / `"exists"` / `"mcp"` |
| `name` | string | 是 | 目标（version=命令名；exists=命令名；mcp=server 名） |

各类型专属字段：

| 类型 | 字段 | 说明 |
|---|---|---|
| `version` | `min` | 最低版本（semver 宽松格式，如 `"22"`、`"22.14"`、`"22.14.0"`） |
| `version` | `max`（可选） | 最高版本 |
| `exists` | `names`（可选） | 字符串数组，一次声明多个工具；可与 `name` 同时提供（都会检查） |

### 3.2 检查器语义

- **`version`**：运行 `<name> --version`，从输出中提取 semver 版本号（正则匹配第一个 `\d+\.\d+(\.\d+)?`，兼容 `node` 的 `v22.14.0`、`cargo` 的 `cargo 1.70.0 (…)` 等不同格式），与 `min`/`max` 比较。失败时 `detail` 记录实际版本。
- **`exists`**：`command -v <name>` 探测命令是否可执行。失败时 `fix` 建议安装方式（通用提示「请安装 <name>」，具体包名由用户写进配置的 `fix` 字段——见 3.3）。
- **`mcp`**：检查 `.mcp.json`（项目级）的 `mcpServers` 键是否声明了 `name`。失败时 `fix` 建议添加该 server。

### 3.3 自定义修复提示（可选）

每个 check 可带 `fix` 字段覆盖默认的修复建议：

```toml
[[checks]]
type = "exists"
name = "rg"
fix = "brew install ripgrep"
```

若未提供 `fix`，检查器用默认建议（如 `version` 失败提示「请升级 <name> 到 >= <min>」）。

## 4. 包结构

npm 包放 Narness 仓库 **`cli/` 子目录**，独立 `package.json`（`name: "narness"`，`bin` 暴露 `narness`），可 `npm publish`。

```
cli/
├── package.json           # name: narness, bin, dependencies (smol-toml, semver)
├── tsconfig.json
├── src/
│   ├── index.ts           # CLI 入口：解析 --json / --config，调用引擎，设置 exit code
│   ├── config.ts          # 从 cwd 向上定位 .narness.toml，解析为类型化 Config
│   ├── engine.ts          # 遍历 checks，按 type dispatch 到检查器，收集 CheckResult[]
│   ├── checks/
│   │   ├── check.ts       # Check 接口 + CheckResult 类型（扩展点）
│   │   ├── version.ts     # 版本检查器
│   │   ├── exists.ts      # 存在性检查器
│   │   └── mcp.ts         # MCP 声明检查器
│   ├── report.ts          # human / JSON 输出格式化
│   └── registry.ts        # type → Check 的注册表（引擎 dispatch 用）
└── tests/                 # 单元 + 集成 + CLI 测试
```

## 5. 核心接口

```ts
// checks/check.ts — 所有检查器的统一契约（扩展点）
interface Check {
  run(check: CheckConfig, ctx: Context): Promise<CheckResult>;
}

interface CheckResult {
  status: "pass" | "fail" | "error";  // error = 检查器自身出错（如命令无法执行）
  check: CheckConfig;
  message?: string;   // 失败时：哪里失败 + 为什么
  fix?: string;       // 失败时：怎么修（修复引导）
  detail?: string;    // 额外信息（如实际版本号）
}
```

`registry.ts` 维护 `type → Check` 映射。新增检查器类型 = 新增一个模块 + 注册一行，不改引擎——这就是可扩展架构的落点。

## 6. 数据流

1. `npx narness [--json] [--config <path>]` → 解析 CLI 参数
2. `config.ts` 从 cwd 向上查找 `.narness.toml`（支持 `--config` 指定路径），解析为 `Config`
3. `engine.ts` 遍历 checks：查 registry 得到检查器 → `await check.run(...)` → `CheckResult`
4. 汇总 `CheckResult[]`
5. `report.ts` 输出（human 或 `--json`）
6. 设置 exit code

## 7. 输出格式

**human-readable**（默认）：

```
✔ node >= 22            (实际 v22.14.0)
✗ rg 未安装              → brew install ripgrep
✗ MCP 'filesystem' 未声明 → 请在 .mcp.json 中添加该 server

2 passed, 2 failed
```

**JSON**（`--json`，供 hook/CI 消费）：

```json
{
  "ok": false,
  "passed": 2,
  "failed": 2,
  "results": [
    { "type": "version", "name": "node", "status": "pass", "detail": "v22.14.0" },
    { "type": "exists", "name": "rg", "status": "fail", "message": "rg 未安装", "fix": "brew install ripgrep" }
  ]
}
```

**exit code**：

| 值 | 含义 |
|---|---|
| `0` | 全部通过 |
| `1` | 有检查失败 |
| `2` | 配置或工具错误（找不到 .narness.toml、TOML 语法错误、未知 type） |

## 8. 错误处理

| 场景 | 行为 |
|---|---|
| 找不到 `.narness.toml` | 提示「未找到 .narness.toml」+ exit 2 |
| TOML 语法错误 | 提示错误位置 + exit 2 |
| 未知 `type` | 提示「未知检查类型 <type>」+ exit 2 |
| 单个检查器异常（如 `node` 不存在却检查版本） | 标记 `status: "error"`，继续其余检查，最终 exit 1 |

## 9. 测试

- **单元测试**：`semver` 比较（`"22"` vs `"22.14.0"`、`v` 前缀剥离）；`exists` 探测；`mcp` 解析 `.mcp.json`；每个检查器对 pass/fail/error 的 `CheckResult`
- **集成测试**：fixture `.narness.toml` + mock 环境（注入假的 `command -v` / 版本命令 / `.mcp.json`），验证引擎汇总结果与 exit code
- **CLI 测试**：`--json` 输出结构、`--config` 指定路径、无配置时的 exit 2

## 10. 验收标准

1. `cli/` 目录有可构建的 TypeScript 包（`package.json` + `tsconfig.json` + 依赖）
2. `npx narness` 能解析 `.narness.toml`，对三类检查器（version/exists/mcp）正确判定 pass/fail
3. 失败项输出含「哪里 + 为什么 + 怎么修」；`--json` 输出结构化结果
4. exit code 符合第 7 节（0/1/2）
5. 错误处理符合第 8 节
6. 测试覆盖三类检查器 + 引擎 + CLI
7. 设计文档与 README/CLAUDE.md 同步（README 加 CLI 说明）

## 11. 明确排除（YAGNI）

- 插件系统（加载本地自定义检查器 JS 文件）—— 通过 `Check` 接口预留，首期不实现
- harness 配置检查（hook/脚本存在性）—— 作为后续检查器类型，首期不实现
- 命令检查器（`[[checks.command]]`）—— 首期不实现
- 自动修复（检查失败自动执行安装/修复）—— 只报告 + 引导，不自动改环境
- MCP 实际连接验证 —— 只做配置声明检查

## 12. 后续步骤

1. 用户审阅本设计文档
2. 通过 `writing-plans` skill 产出实现计划
3. 按计划实现
