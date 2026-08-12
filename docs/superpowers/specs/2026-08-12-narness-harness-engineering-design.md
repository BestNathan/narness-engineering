# Narness — Harness 工程化设计文档

- 日期：2026-08-12
- 状态：已批准设计方向（方案 A：约束层级阶梯为主线）

## 1. 概述

Narness 是一个「研究 + 文档 + Claude Code 工具集」项目。它阐述并落地一套工程化思想：

> **能用代码、hook、或脚本约束 AI agent 行为的，优先用这些，而非提示词。** 因为 AI agent 很可能不按提示词办事；而脚本、hook 能让 agent 发现实现有问题，并指导 agent 进行正确行为，从而保证长程任务的正确性。

### 1.1 品牌名

「Narness」是**故意的品牌名**，不是「harness」的笔误。所有目录、marketplace、skill、文档标题统一使用 `narness` / `Narness`。

### 1.2 首期范围（纯理论）

首期聚焦理论研究、文档、以及 Claude Code 插件骨架，**不包含示例项目**（examples 后续再扩展）。具体产出：

1. 理论/研究文档（`docs/theory/`）
2. Claude Code marketplace（外层 `.claude-plugin/marketplace.json`）
3. 插件 `narness-rust`（子目录 `plugins/narness-rust/`），含 skills / hooks / scripts
4. 项目总览 `README.md`

### 1.3 明确排除（YAGNI）

以下内容首期**不做**：

- 示例项目（用于演示「有/无 harness 的对比」的 Rust 练习或基准库）
- 其他语言插件（narness-python / narness-js 等）
- CI 集成脚本（首期脚本以「可被 agent 和 CI 共同调用」为目标设计，但不落地具体 CI 配置）

## 2. 核心理论：约束层级阶梯（Constraint Ladder）

这是 Narness 的理论内核，所有文档、skill、脚本都围绕它组织。

### 2.1 阶梯模型（从弱到强）

| 层级 | 名称 | 本质 | 约束力 | 失败后果 |
|---|---|---|---|---|
| L0 | 提示词 | 自然语言指令 | 最弱 | agent 可能直接忽略，无任何强制 |
| L1 | 项目约定 | CLAUDE.md / AGENTS.md 等上下文注入规则 | 弱 | 仍靠 agent 自觉读取并遵守 |
| L2 | Skill | 可主动调用的工作流指令 | 中弱 | agent 可能不调用该 skill |
| L3 | Hook | 事件驱动的强制脚本 | 中强 | 自动执行，失败信息回传给 agent |
| L4 | 脚本校验 | cargo check / test / clippy 等独立 ground truth | 强 | 确定性 pass/fail，agent 被迫修复 |
| L5 | 编译期/类型系统 | 语言与类型层面的物理约束 | 最强 | 违反则无法编译，物理不可能跑偏 |

### 2.2 核心命题

> 约束力越靠上（L0–L2），越依赖 agent 的「善意」，越容易在长程任务中失效；约束力越靠下（L3–L5），越不依赖 agent 的自觉，越能保证长程正确性。**Narness 的目标是把尽可能多的约束从 L0–L2 下沉到 L3–L5。**

### 2.3 阶梯与三个 harness 层的对应

| harness 层 | 对应阶梯 | 具体手段 |
|---|---|---|
| 编译/测试作为 ground truth | L4–L5 | `cargo check`、`cargo test`、`cargo clippy -D warnings`、trait bounds、`#![forbid(unsafe_code)]` |
| 代码规范/不变量强制 | L4 | 禁止裸 `unwrap()`/`expect()`、`unsafe` 必须有 SAFETY 注释、错误用 anyhow/thiserror 而非 `panic!` |
| 测试纪律强制 | L3–L4 | hook 检测「改了 .rs 但没有对应测试」、先写测试后写实现 |

## 3. 仓库目录结构

```
narness-engineering/
├── README.md                              # 项目总览、Narness 理念速览
├── LICENSE                                # MIT
├── .gitignore
├── .claude-plugin/
│   └── marketplace.json                   # 外层 marketplace 定义
├── plugins/
│   └── narness-rust/                      # 插件子目录
│       ├── .claude-plugin/
│       │   └── plugin.json                # 插件元数据
│       ├── skills/
│       │   └── narness-rust/
│       │       └── SKILL.md               # narness-rust skill
│       ├── hooks/
│       │   ├── hooks.json                 # hook 定义
│       │   └── scripts/                   # hook 调用的脚本
│       │       └── post-edit-gate.sh      # PostToolUse 触发的快速门禁
│       └── scripts/                       # 独立校验脚本（agent 与 CI 共用，单一职责）
│           ├── verify-fmt.sh              # 格式检查
│           ├── verify-check.sh            # 编译检查
│           ├── verify-clippy.sh           # lint 检查
│           ├── verify-test.sh             # 测试
│           ├── verify-invariants.sh       # 不变量检查
│           └── verify-test-discipline.sh  # 测试纪律检查
└── docs/
    ├── theory/                            # 理论研究文档
    │   ├── why-not-prompts.md
    │   ├── constraint-ladder.md
    │   ├── decision-guide.md
    │   └── long-running-correctness.md
    └── superpowers/
        └── specs/                         # 设计文档（本文档）
```

### 3.1 各目录职责

| 路径 | 职责 |
|---|---|
| `.claude-plugin/marketplace.json` | 定义 marketplace 元数据与插件清单，指向 `plugins/narness-rust` |
| `plugins/narness-rust/` | 单个插件的完整实现，可独立安装 |
| `plugins/narness-rust/skills/` | skill 定义，每个 skill 一个目录 + `SKILL.md` |
| `plugins/narness-rust/hooks/` | hook 配置 + 事件触发的脚本 |
| `plugins/narness-rust/scripts/` | 与 hook 解耦的独立校验脚本，可被 agent 手动调用或 CI 复用 |
| `docs/theory/` | 理论文档，是项目的「研究」主体 |

## 4. Marketplace

`/Users/nathan/workspace/narness-engineering/.claude-plugin/marketplace.json`：

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

要点（已对照官方 `$schema` 与 Anthropic 官方多插件 marketplace 验证）：

- `source` 指向插件相对 marketplace 根目录（即包含 `.claude-plugin/` 的目录）的子目录路径，必须以 `./` 开头；`"./plugins/narness-rust"` 正确。
- 每个插件目录必须自带 `.claude-plugin/plugin.json`，Claude Code 在解析出的插件根目录查找该清单。
- 顶层 `version` 是 marketplace 清单版本，与各插件自身的 `version` 相互独立。

## 5. 插件：narness-rust

### 5.1 plugin.json

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

### 5.2 Skills

首期只做**一个**核心 skill：`narness-rust`（`plugins/narness-rust/skills/narness-rust/SKILL.md`）。

**skill 职责**：指导 agent 在 Rust 项目中实施 harness 工程化。

**SKILL.md 内容大纲**：

1. **何时调用** — 当需要在 Rust 项目中建立约束、或发现 agent 反复违反同一类约束时
2. **约束阶梯的 Rust 映射** — 把 L0–L5 映射到具体 Rust 手段（见 2.3 表）
3. **把约束下沉的步骤** — 遇到「靠提示词约束失败」的场景时，如何逐级升级到 hook / 脚本 / 编译期
4. **脚本使用指引** — 何时调用 `verify-fmt.sh` / `verify-check.sh` / `verify-clippy.sh` / `verify-test.sh` / `verify-invariants.sh` / `verify-test-discipline.sh`，如何解读失败输出并修复
5. **测试纪律** — 先写测试、改动 .rs 必须有对应测试、如何满足门禁

### 5.3 Hooks

`plugins/narness-rust/hooks/hooks.json` 定义 `PostToolUse` 钩子：当 agent 用 `Edit` / `Write` 修改 `.rs` 文件后，触发快速门禁脚本，失败信息回传给 agent 供其修复。

- **事件**：`PostToolUse`
- **matcher**：`Edit|Write|MultiEdit`
- **行为**：`post-edit-gate.sh` 作为 hook 入口，判断改动是否为 `.rs`，是则调用 `verify-check.sh` 做编译检查（跳过耗时的全量 test），失败时把 stderr 注入对话
- **设计考量**：hook 只跑**快速**门禁（避免每次编辑都跑全量 `cargo test` 造成卡顿）；其余校验（fmt / clippy / test）由 agent 主动调用对应的单一职责脚本或 CI 执行，实现「快速 hook + 可组合脚本」分层

### 5.4 独立脚本（scripts/）

脚本是「代码约束」的实体，与 hook 解耦，可被 agent 手动调用、被 hook 调用、被 CI 复用。均参数化（接受项目根路径），首期作为「参考实现」存在，不绑定具体示例项目。**每个脚本只做一件事（单一职责）**，可独立调用、独立验证、按需组合。

| 脚本 | 职责 | 对应 harness 层 |
|---|---|---|
| `verify-fmt.sh` | `cargo fmt --check` | 编译/测试 ground truth |
| `verify-check.sh` | `cargo check` | 编译/测试 ground truth |
| `verify-clippy.sh` | `cargo clippy --all-targets --all-features -- -D warnings` | 编译/测试 ground truth |
| `verify-test.sh` | `cargo test` | 编译/测试 ground truth |
| `verify-invariants.sh` | 扫描 `src/` 下的 `.rs`，检查：裸 `unwrap()`/`expect()`、`panic!`、`unsafe` 缺 SAFETY 注释 | 代码规范/不变量 |
| `verify-test-discipline.sh` | 检测最近改动的 `.rs` 是否有对应测试文件 | 测试纪律 |

## 6. 理论文档结构

`docs/theory/` 四篇文档：

| 文档 | 内容 |
|---|---|
| `why-not-prompts.md` | 为什么不能只靠提示词：agent 忽略提示词的原理与实例，引出「代码约束 > 提示词」的必要性 |
| `constraint-ladder.md` | 阶梯模型详述：每层的能力、局限、适用场景、Claude Code 实现方式 |
| `decision-guide.md` | 决策准则（决策树/checklist）：何时把约束从提示词下沉为代码 |
| `long-running-correctness.md` | harness 如何保证长程任务正确性：hook/脚本在长程任务各环节的作用 |

## 7. 验收标准（首期完成判定）

1. 仓库结构符合第 3 节目录，`git` 已初始化
2. `marketplace.json` 与 `plugin.json` 字段完整、格式正确（对齐 Claude Code 插件规范）
3. `narness-rust` skill 的 `SKILL.md` 存在，内容覆盖 5.2 大纲
4. `hooks.json` 与六个单一职责脚本存在且可执行，脚本可被独立调用
5. 四篇理论文档存在，核心命题（第 2.2 节）贯穿全文
6. `README.md` 简述 Narness 理念与使用方式

## 8. 后续步骤

1. 用户审阅本设计文档
2. 通过 `writing-plans` skill 产出实现计划
3. 按计划实现首期内容
