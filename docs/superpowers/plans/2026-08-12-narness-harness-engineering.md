# Narness Harness Engineering 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 Narness 项目骨架——外层 marketplace、narness-rust 插件（skill + hook + 脚本）、以及四篇理论文档，落地「用代码/hook/脚本约束 agent 而非提示词」的工程化理念。

**Architecture:** 约束层级阶梯（L0 提示词 → L5 编译期）是理论内核，贯穿文档与脚本。仓库是「外层 marketplace + 子目录插件」结构：`marketplace.json` 指向 `plugins/narness-rust`；插件内含 skill、PostToolUse hook（快速门禁）、独立校验脚本（完整门禁/不变量/测试纪律）。

**Tech Stack:** Claude Code 插件（marketplace.json / plugin.json / hooks.json / SKILL.md）、bash 脚本（macOS 兼容，零额外依赖，JSON 解析用系统自带 python3）、markdown 理论文档。

**已存在：** `.gitignore`、设计文档 `docs/superpowers/specs/2026-08-12-narness-harness-engineering-design.md`（已 commit）。

**验收（对齐设计文档第 7 节）：** 目录结构完整；marketplace/plugin JSON 格式正确；skill 覆盖 5.2 大纲；hook + 三脚本可执行；四篇理论文档存在且贯穿核心命题；README 简述理念与用法。

---

### Task 1: 项目脚手架与目录结构

**Files:**
- Create: `LICENSE`
- Create: 目录树（`plugins/narness-rust/{skills/narness-rust,hooks/scripts,scripts}`、`docs/theory`、`.claude-plugin`）

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p .claude-plugin \
  plugins/narness-rust/.claude-plugin \
  plugins/narness-rust/skills/narness-rust \
  plugins/narness-rust/hooks/scripts \
  plugins/narness-rust/scripts \
  docs/theory
```

- [ ] **Step 2: 写 LICENSE（MIT）**

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

- [ ] **Step 3: 验证目录结构**

Run: `find . -type d -not -path './.git*' | sort`
Expected: 输出包含 `.claude-plugin`、`plugins/narness-rust/...`、`docs/theory` 等目录。

- [ ] **Step 4: Commit**

```bash
git add LICENSE
git commit -m "chore: scaffold project directories and MIT license"
```

---

### Task 2: marketplace.json（外层 marketplace）

**Files:**
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: 写 marketplace.json**

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

- [ ] **Step 2: 校验 JSON 合法性**

Run: `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: 校验字段**

Run: `python3 -c "import json;d=json.load(open('.claude-plugin/marketplace.json'));print(d['name'], d['version'], d['plugins'][0]['source'])"`
Expected: `narness 0.1.0 ./plugins/narness-rust`

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat: add narness marketplace manifest"
```

---

### Task 3: plugin.json（narness-rust 插件元数据）

**Files:**
- Create: `plugins/narness-rust/.claude-plugin/plugin.json`

- [ ] **Step 1: 写 plugin.json**

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

- [ ] **Step 2: 校验 JSON 合法性**

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

- [ ] **Step 1: 写 README.md**

Create `README.md`:

```markdown
# Narness

Narness 是「研究 + 文档 + Claude Code 工具集」项目，阐述并落地一套工程化思想：

> 能用代码、hook、脚本约束 AI agent 行为的，优先用这些，而非提示词。因为 agent 很可能不按提示词办事；脚本、hook 能让 agent 发现实现有问题，并指导其正确行为，从而保证长程任务的正确性。

## 理念

提示词是软约束，agent 可能忽略；脚本、hook 是硬约束，agent 无法逃避。Narness 用「约束层级阶梯」（L0 提示词 → L5 编译期）组织方法论，并提供插件把约束落地为代码。

## 目录

- `docs/theory/` — 理论研究文档
- `plugins/narness-rust/` — Rust harness 工程化插件（skill + hook + 脚本）
- `.claude-plugin/marketplace.json` — marketplace 定义

## 快速开始

安装 marketplace 后安装 `narness-rust` 插件：

```bash
claude plugin marketplace add <本仓库地址>
claude plugin install narness-rust
```

## 理论文档

- [为什么不能只靠提示词](docs/theory/why-not-prompts.md)
- [约束层级阶梯](docs/theory/constraint-ladder.md)
- [决策准则](docs/theory/decision-guide.md)
- [长程任务的正确性](docs/theory/long-running-correctness.md)
```

- [ ] **Step 2: 内容自审**

检查：README 是否含理念一句话、目录说明、快速开始、四篇理论文档链接。若有缺漏，补上。

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add project README"
```

---

### Task 5: 理论文档 — why-not-prompts.md

**Files:**
- Create: `docs/theory/why-not-prompts.md`

- [ ] **Step 1: 写 why-not-prompts.md**

Create `docs/theory/why-not-prompts.md`:

```markdown
# 为什么不能只靠提示词

## 1. 提示词是软约束

提示词是一段自然语言文本，它「请求」或「建议」agent 做某事，而非「强制」。约束能否生效，取决于 agent 是否：

1. 注意到这段文字
2. 正确理解其含义
3. 在具体决策点想起来要遵守
4. 判断遵守的必要性高于其他目标

任一环节断裂，约束即失效。这四个环节全部依赖 agent 的「善意」，而非任何可验证的机制。

## 2. 三个失效机制

### 2.1 注意力稀释

长上下文里，一段提示词与海量信息竞争注意力。随着对话增长，早期写下的约束（哪怕在 system prompt 或 CLAUDE.md 中）会被逐渐稀释，agent 在具体决策点可能根本「没想到」这条约束。

### 2.2 概率性服从

LLM 是概率模型，不是规则引擎。同一段提示词，在不同上下文、不同采样下，服从程度不同。今天记得写测试，明天可能就忘。

### 2.3 目标冲突时的让步

当「遵守约束」与「完成当前目标」冲突时——例如急着修复一个 bug，跳过测试看起来「更快」——agent 可能理性化地忽略约束。

## 3. 硬约束为什么有效

代码、hook、脚本是硬约束：

- 不依赖 agent 注意到——hook 由事件自动触发
- 不依赖 agent 理解——脚本输出确定性的 pass/fail
- 不依赖 agent 选择遵守——编译失败就是失败，无法「商量」

## 4. 结论

提示词适合表达「意图」和「为什么」，不适合承担「必须遵守的什么」。约束应尽可能下沉到硬约束层。这是 Narness 的核心前提，详见 [约束层级阶梯](constraint-ladder.md)。
```

- [ ] **Step 2: 内容自审**

检查：是否覆盖「软约束定义 → 三个失效机制 → 硬约束为什么有效 → 结论」完整逻辑链，且结论指向 `constraint-ladder.md`。

- [ ] **Step 3: Commit**

```bash
git add docs/theory/why-not-prompts.md
git commit -m "docs: add why-not-prompts theory doc"
```

---

### Task 6: 理论文档 — constraint-ladder.md

**Files:**
- Create: `docs/theory/constraint-ladder.md`

- [ ] **Step 1: 写 constraint-ladder.md**

Create `docs/theory/constraint-ladder.md`:

```markdown
# 约束层级阶梯

## 1. 模型总览

| 层级 | 名称 | 本质 | 约束力 | 失败后果 |
|---|---|---|---|---|
| L0 | 提示词 | 自然语言指令 | 最弱 | agent 可能直接忽略 |
| L1 | 项目约定 | CLAUDE.md / AGENTS.md | 弱 | 靠 agent 自觉读取 |
| L2 | Skill | 可主动调用的工作流 | 中弱 | agent 可能不调用 |
| L3 | Hook | 事件驱动的强制脚本 | 中强 | 自动执行，失败回传 |
| L4 | 脚本校验 | cargo check/test/clippy | 强 | 确定性 pass/fail |
| L5 | 编译期 | 语言与类型系统 | 最强 | 违反无法编译 |

## 2. 各层详解

### L0 提示词

- 能约束什么：表达意图、方向性建议
- 会漏什么：一切需要「必须遵守」的行为
- 何时用：总是作为起点，但绝不作为终点

### L1 项目约定（CLAUDE.md）

- 能约束什么：项目的背景、约定、惯例
- 会漏什么：依赖 agent 主动读取并遵守
- 何时用：写「背景」和「why」，不写「必须」

### L2 Skill

- 能约束什么：复杂工作流的步骤化指导
- 会漏什么：agent 可能不触发该 skill
- 何时用：把「怎么做」沉淀为可复用流程

### L3 Hook

- 能约束什么：事件触发时的自动检查
- 会漏什么：只覆盖触发的事件，不覆盖主动决策
- 何时用：改动后即时校验、失败即时回传

### L4 脚本校验

- 能约束什么：可独立验证的确定性规则
- 会漏什么：需要 agent/CI 主动调用
- 何时用：编译、测试、格式、不变量

### L5 编译期

- 能约束什么：语言层面物理不可能违反的约束
- 会漏什么：只有类型系统能表达的东西
- 何时用：凡是能用类型表达的不变量

## 3. 核心命题

约束力越靠上越依赖 agent 善意，越靠下越能保证长程正确性。目标：**把约束从 L0–L2 下沉到 L3–L5。**
```

- [ ] **Step 2: 内容自审**

检查：六层表格与设计文档 2.1 表一致；每层有「能约束什么/会漏什么/何时用」；核心命题明确。

- [ ] **Step 3: Commit**

```bash
git add docs/theory/constraint-ladder.md
git commit -m "docs: add constraint-ladder theory doc"
```

---

### Task 7: 理论文档 — decision-guide.md

**Files:**
- Create: `docs/theory/decision-guide.md`

- [ ] **Step 1: 写 decision-guide.md**

Create `docs/theory/decision-guide.md`:

```markdown
# 决策准则：何时把约束下沉

## 1. 决策树

遇到一条「希望 agent 遵守」的规则时，按以下顺序判断：

```
这条规则，agent 违反过一次吗？
├── 否 → 可以先用提示词（L0/L1）表达，观察
└── 是 → 违反了两次及以上吗？
    ├── 否 → 升级到 Skill（L2）或 Hook（L3）
    └── 是 → 能否用脚本（L4）或编译期（L5）表达？
        ├── 能 → 下沉到 L4/L5（优先编译期）
        └── 不能 → 下沉到 Hook（L3），用脚本反馈失败
```

## 2. 经验法则

- 能用 `clippy` lint 表达的规则，直接上 `clippy -D warnings`（L5）
- 能用类型系统表达的不变量，用类型（L5），如 newtype、trait bound
- 需要「改动后即时反馈」的，用 Hook（L3）
- 需要「提交前/CI 校验」的，用脚本（L4）
- 只剩「意图和背景」时，才留在提示词（L0/L1）

## 3. 反模式清单

| 反模式 | 问题 | 正确做法 |
|---|---|---|
| 在 CLAUDE.md 写「务必写测试」 | 软约束，长程必然失效 | verify-test-discipline 脚本 + hook |
| 提示词要求「别用 unwrap」 | agent 总会忘 | clippy::unwrap_used（L5） |
| 口头要求「记得格式化」 | 无人执行 | cargo fmt --check 门禁（L4） |
| 把不变量写成注释 | 注释不强制 | 类型系统或断言（L5/L4） |
```

- [ ] **Step 2: 内容自审**

检查：决策树逻辑自洽；经验法则覆盖 L3–L5；反模式清单与「代码约束 > 提示词」命题一致。

- [ ] **Step 3: Commit**

```bash
git add docs/theory/decision-guide.md
git commit -m "docs: add decision-guide theory doc"
```

---

### Task 8: 理论文档 — long-running-correctness.md

**Files:**
- Create: `docs/theory/long-running-correctness.md`

- [ ] **Step 1: 写 long-running-correctness.md**

Create `docs/theory/long-running-correctness.md`:

```markdown
# 长程任务的正确性

## 1. 什么是长程任务

单次对话内无法完成、需要多轮往返或跨会话的任务：从零实现一个模块、重构整个子系统、修复跨文件的 bug。特征：上下文持续增长、早期约束被稀释、错误不断累积。

## 2. 为什么长程任务最容易跑偏

- 早期提示词被后续上下文淹没
- 每一步的小偏差累积成大的方向错误
- 没有外部 checkpoint，agent 自己难以察觉「已经错了」

## 3. harness 在各环节的作用

| 环节 | 对应 harness | 作用 |
|---|---|---|
| 任务启动 | L1/L2（CLAUDE.md + skill） | 明确 ground truth 和验收标准 |
| 编码中 | L3（hook） | 每次改动即时校验，偏差不过夜 |
| 阶段性提交 | L4（脚本） | 完整门禁，阻止累积错误进入下一步 |
| 集成/回归 | L5（编译期）+ CI | 物理约束 + 回归保护 |

## 4. 核心洞察

长程任务正确性不靠 agent「一直记得规则」，而靠：每一步改动都经过硬约束校验，错误在产生的那一刻就被脚本/hook 捕获并回传，agent 被迫在错误还小时就修正。这就是「让 agent 自己发现问题」的机制。
```

- [ ] **Step 2: 内容自审**

检查：长程任务定义、跑偏原因、harness 各环节作用表、核心洞察四部分完整。

- [ ] **Step 3: Commit**

```bash
git add docs/theory/long-running-correctness.md
git commit -m "docs: add long-running-correctness theory doc"
```

---

### Task 9: narness-rust skill

**Files:**
- Create: `plugins/narness-rust/skills/narness-rust/SKILL.md`

- [ ] **Step 1: 写 SKILL.md**

Create `plugins/narness-rust/skills/narness-rust/SKILL.md`:

```markdown
---
name: narness-rust
description: "指导在 Rust 项目中实施 harness 工程化——用 cargo/clippy/hook/脚本约束 AI agent，而非提示词。当需要为 Rust 项目建立约束、或将靠提示词反复失效的约束下沉为代码时调用。"
---

# Narness Rust — Rust Harness 工程化

把对 AI agent 的约束从「提示词」下沉为「代码、hook、脚本」，保证长程任务的正确性。

## 核心思想

能用代码、hook、脚本约束 agent 的，优先用它们，而非提示词。提示词是软约束，agent 可能忽略；脚本是硬约束，agent 无法逃避。

## 约束层级阶梯（Rust 映射）

| 层级 | 手段 | 约束力 |
|---|---|---|
| L0 提示词 | 口头/文档要求 | 最弱 |
| L1 项目约定 | CLAUDE.md | 弱 |
| L2 Skill | 本 skill | 中弱 |
| L3 Hook | PostToolUse 校验 | 中强 |
| L4 脚本 | check.sh / verify-invariants.sh | 强 |
| L5 编译期 | clippy -D warnings、#![forbid] | 最强 |

## 何时调用本 skill

- 需要为 Rust 项目建立 harness 约束时
- 发现 agent 反复违反同一类约束（如总写 unwrap、总忘测试）时
- 需要把某个「靠提示词约束失效」的规则下沉为代码时

## 把约束下沉的步骤

1. 识别：哪条规则 agent 反复违反？
2. 定位层级：这条规则最适合落到 L3–L5 哪层？
3. 落地：
   - L3 → 配置 PostToolUse hook 跑校验脚本
   - L4 → 调用 scripts/ 下的校验脚本
   - L5 → 加 clippy lint / `#![forbid(...)]` / trait bound

## 可用脚本

| 脚本 | 用途 |
|---|---|
| `scripts/check.sh [DIR]` | 完整门禁：fmt + clippy -D warnings + test |
| `scripts/verify-invariants.sh [DIR]` | 不变量：禁 unwrap/expect/panic!/unsafe 无注释 |
| `scripts/verify-test-discipline.sh [DIR]` | 测试纪律：改 .rs 必有测试 |

## 测试纪律

- 先写测试，再写实现
- 改动 src/ 下的 .rs 必须有对应测试文件
- 提交前跑 `check.sh` 完整门禁

## 常见反模式与对应硬约束

| 反模式 | 硬约束 |
|---|---|
| 到处 unwrap() | clippy::unwrap_used + verify-invariants.sh |
| 裸 panic! | clippy::panic + thiserror/anyhow |
| 忘写测试 | verify-test-discipline.sh + hook |
| 格式漂移 | cargo fmt --check 门禁 |
```

- [ ] **Step 2: 校验 frontmatter**

Run: `head -5 plugins/narness-rust/skills/narness-rust/SKILL.md`
Expected: 前三行是 `---`、`name: narness-rust`、`description: "..."`、`---`。

- [ ] **Step 3: 内容自审**

检查：是否覆盖设计文档 5.2 大纲（何时调用、阶梯 Rust 映射、下沉步骤、脚本指引、测试纪律）。若有缺漏，补上。

- [ ] **Step 4: Commit**

```bash
git add plugins/narness-rust/skills/narness-rust/SKILL.md
git commit -m "feat: add narness-rust skill"
```

---

### Task 10: hooks.json + post-edit-gate.sh（PostToolUse 快速门禁）

**Files:**
- Create: `plugins/narness-rust/hooks/hooks.json`
- Create: `plugins/narness-rust/hooks/scripts/post-edit-gate.sh`

- [ ] **Step 1: 写 hooks.json**

Create `plugins/narness-rust/hooks/hooks.json`:

```json
{
  "description": "Narness Rust 快速门禁：每次编辑 .rs 文件后校验格式与编译",
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

- [ ] **Step 2: 校验 JSON 合法性**

Run: `python3 -m json.tool plugins/narness-rust/hooks/hooks.json > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: 写 post-edit-gate.sh**

Create `plugins/narness-rust/hooks/scripts/post-edit-gate.sh`:

```bash
#!/usr/bin/env bash
# post-edit-gate.sh — PostToolUse 快速门禁
# 由 Claude Code hook 调用，stdin 传入 hook JSON。
# 只对 .rs 文件做快速校验（fmt + check）；失败时 stderr + exit 2 反馈给 Claude。
set -uo pipefail

input="$(cat)"

# 提取 tool_input.file_path（Edit/Write/MultiEdit 的输入键名）
file_path="$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)"

# 非 .rs 文件直接放行
case "$file_path" in
  *.rs) ;;
  *) exit 0 ;;
esac

# 快速门禁 1: cargo fmt --check
if ! cargo fmt --check 2>&1; then
  echo "⚠ Narness 快速门禁: cargo fmt --check 失败，请运行 cargo fmt 后重试" >&2
  exit 2
fi

# 快速门禁 2: cargo check（不跑全量 test，避免拖慢编辑循环）
if ! cargo check 2>&1 | tail -n 30; then
  echo "⚠ Narness 快速门禁: cargo check 失败，请修复编译错误" >&2
  exit 2
fi

exit 0
```

- [ ] **Step 4: 语法检查**

Run: `bash -n plugins/narness-rust/hooks/scripts/post-edit-gate.sh && chmod +x plugins/narness-rust/hooks/scripts/post-edit-gate.sh && echo OK`
Expected: `OK`

- [ ] **Step 5: 冒烟测试（非 .rs 文件应放行）**

Run:
```bash
echo '{"tool_input":{"file_path":"/tmp/foo.txt"}}' | plugins/narness-rust/hooks/scripts/post-edit-gate.sh; echo "exit=$?"
```
Expected: `exit=0`（不触发校验）

- [ ] **Step 6: Commit**

```bash
git add plugins/narness-rust/hooks/hooks.json plugins/narness-rust/hooks/scripts/post-edit-gate.sh
git commit -m "feat: add PostToolUse fast-gate hook"
```

---

### Task 11: check.sh（完整门禁）

**Files:**
- Create: `plugins/narness-rust/scripts/check.sh`

- [ ] **Step 1: 写 check.sh**

Create `plugins/narness-rust/scripts/check.sh`:

```bash
#!/usr/bin/env bash
# check.sh — Narness Rust 完整门禁
# 用法: check.sh [PROJECT_DIR]
# 依次运行: cargo fmt --check → cargo clippy -D warnings → cargo test
set -euo pipefail

PROJECT_DIR="${1:-.}"

echo "==> Narness 完整门禁: $PROJECT_DIR"
cd "$PROJECT_DIR"

echo "==> 1/3 cargo fmt --check"
cargo fmt --check

echo "==> 2/3 cargo clippy --all-targets --all-features -- -D warnings"
cargo clippy --all-targets --all-features -- -D warnings

echo "==> 3/3 cargo test"
cargo test

echo "==> 全部通过"
```

- [ ] **Step 2: 语法检查**

Run: `bash -n plugins/narness-rust/scripts/check.sh && chmod +x plugins/narness-rust/scripts/check.sh && echo OK`
Expected: `OK`

- [ ] **Step 3: 冒烟测试（临时 cargo 项目）**

Run:
```bash
tmp=$(mktemp -d)
cd "$tmp"
cargo new --lib smoke >/dev/null 2>&1
bash "$OLDPWD/plugins/narness-rust/scripts/check.sh" "$tmp/smoke"
echo "exit=$?"
rm -rf "$tmp"
```
Expected: 三阶段 `cargo fmt --check` / `cargo clippy` / `cargo test` 依次输出，末尾 `全部通过`，`exit=0`。（若环境无 cargo，此步跳过并在提交信息中说明。）

- [ ] **Step 4: Commit**

```bash
git add plugins/narness-rust/scripts/check.sh
git commit -m "feat: add full-gate check script"
```

---

### Task 12: verify-invariants.sh（不变量检查）

**Files:**
- Create: `plugins/narness-rust/scripts/verify-invariants.sh`

- [ ] **Step 1: 写 verify-invariants.sh**

Create `plugins/narness-rust/scripts/verify-invariants.sh`:

```bash
#!/usr/bin/env bash
# verify-invariants.sh — Narness Rust 不变量检查
# 用法: verify-invariants.sh [PROJECT_DIR]
# 扫描 src/ 下 .rs 文件，检查:
#   - 裸 unwrap() / expect()（生产代码禁止）
#   - panic! / unreachable! / todo! / unimplemented!
#   - unsafe 缺少 SAFETY 注释
# 零额外依赖（仅用 POSIX find + grep），macOS 兼容。
set -uo pipefail

PROJECT_DIR="${1:-.}"
SRC_DIR="$PROJECT_DIR/src"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "错误: 未找到 src 目录: $SRC_DIR" >&2
  exit 1
fi

fail=0
echo "==> Narness 不变量检查: $SRC_DIR"

# 1. 裸 unwrap() / expect()
matches="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -nH -E '\.(unwrap|expect)\(' {} + 2>/dev/null || true)"
if [[ -n "$matches" ]]; then
  printf '%s\n' "$matches" >&2
  echo "✗ 发现 unwrap()/expect()，请用 anyhow/thiserror 或显式错误处理替代" >&2
  fail=1
else
  echo "✓ 无裸 unwrap()/expect()"
fi

# 2. panic! / unreachable! / todo! / unimplemented!
matches="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -nH -E '\b(panic|unreachable|todo|unimplemented)!' {} + 2>/dev/null || true)"
if [[ -n "$matches" ]]; then
  printf '%s\n' "$matches" >&2
  echo "✗ 发现 panic!/unreachable!/todo!/unimplemented!，请用 Result 错误传播" >&2
  fail=1
else
  echo "✓ 无 panic!/unreachable!/todo!/unimplemented!"
fi

# 3. unsafe 块缺少 SAFETY 注释
unsafe_files="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -lE '\bunsafe\b' {} + 2>/dev/null || true)"
if [[ -n "$unsafe_files" ]]; then
  while IFS= read -r f; do
    if ! grep -q 'SAFETY' "$f"; then
      echo "✗ $f 含 unsafe 但无 SAFETY 注释" >&2
      fail=1
    fi
  done <<< "$unsafe_files"
else
  echo "✓ 无 unsafe 代码"
fi

if [[ $fail -ne 0 ]]; then
  echo "==> 不变量检查失败" >&2
  exit 1
fi
echo "==> 不变量检查通过"
```

- [ ] **Step 2: 语法检查**

Run: `bash -n plugins/narness-rust/scripts/verify-invariants.sh && chmod +x plugins/narness-rust/scripts/verify-invariants.sh && echo OK`
Expected: `OK`

- [ ] **Step 3: 冒烟测试（含违规的夹具）**

Run:
```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/src"
printf 'fn good(x: Option<i32>) -> i32 { match x { Some(v) => v, None => 0 } }\n' > "$tmp/src/good.rs"
printf 'fn bad(x: Option<i32>) -> i32 { x.unwrap() }\nunsafe fn raw() {}\n' > "$tmp/src/bad.rs"
plugins/narness-rust/scripts/verify-invariants.sh "$tmp"; echo "exit=$?"
rm -rf "$tmp"
```
Expected: 输出含 `✗ 发现 unwrap()/expect()` 和 `✗ ... 含 unsafe 但无 SAFETY 注释`，末尾 `不变量检查失败`，`exit=1`。

- [ ] **Step 4: 冒烟测试（干净的夹具应通过）**

Run:
```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/src"
printf 'fn good(x: Option<i32>) -> i32 { match x { Some(v) => v, None => 0 } }\n' > "$tmp/src/good.rs"
plugins/narness-rust/scripts/verify-invariants.sh "$tmp"; echo "exit=$?"
rm -rf "$tmp"
```
Expected: 三个 `✓`，末尾 `不变量检查通过`，`exit=0`。

- [ ] **Step 5: Commit**

```bash
git add plugins/narness-rust/scripts/verify-invariants.sh
git commit -m "feat: add invariant verification script"
```

---

### Task 13: verify-test-discipline.sh（测试纪律检查）

**Files:**
- Create: `plugins/narness-rust/scripts/verify-test-discipline.sh`

- [ ] **Step 1: 写 verify-test-discipline.sh**

Create `plugins/narness-rust/scripts/verify-test-discipline.sh`:

```bash
#!/usr/bin/env bash
# verify-test-discipline.sh — Narness Rust 测试纪律检查
# 用法: verify-test-discipline.sh [PROJECT_DIR]
# 检查相对 git HEAD 改动过的非测试 .rs 源文件是否有对应测试文件。
set -uo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

# 改动过的非测试 .rs 源文件（排除 tests/、*_test.rs 等）
changed="$(git diff --name-only HEAD -- '*.rs' 2>/dev/null | grep -vE '(^|/)(tests?|benches|examples)/|(_test|\.test)\.rs$' || true)"

if [[ -z "$changed" ]]; then
  echo "✓ 没有改动非测试 .rs 源文件"
  exit 0
fi

fail=0
while IFS= read -r f; do
  # src/foo/bar.rs → tests/foo/bar.rs 或 tests/foo/bar_test.rs 或 src/foo/bar_test.rs
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
    echo "✗ $f 有改动但无对应测试文件" >&2
    fail=1
  else
    echo "✓ $f 有测试覆盖"
  fi
done <<< "$changed"

if [[ $fail -ne 0 ]]; then
  echo "==> 测试纪律检查失败: 请为上述文件补充测试" >&2
  exit 1
fi
echo "==> 测试纪律检查通过"
```

- [ ] **Step 2: 语法检查**

Run: `bash -n plugins/narness-rust/scripts/verify-test-discipline.sh && chmod +x plugins/narness-rust/scripts/verify-test-discipline.sh && echo OK`
Expected: `OK`

- [ ] **Step 3: 冒烟测试（临时 git 仓库，无测试应失败）**

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
Expected: 输出含 `✗ src/lib.rs 有改动但无对应测试文件`，末尾 `测试纪律检查失败`，`exit=1`。

- [ ] **Step 4: 冒烟测试（有测试应通过）**

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
Expected: 输出含 `✓ src/lib.rs 有测试覆盖`，末尾 `测试纪律检查通过`，`exit=0`。

- [ ] **Step 5: Commit**

```bash
git add plugins/narness-rust/scripts/verify-test-discipline.sh
git commit -m "feat: add test-discipline verification script"
```

---

### Task 14: 最终验证与收尾

- [ ] **Step 1: 全仓库 JSON 校验**

Run:
```bash
for f in .claude-plugin/marketplace.json plugins/narness-rust/.claude-plugin/plugin.json plugins/narness-rust/hooks/hooks.json; do
  python3 -m json.tool "$f" > /dev/null && echo "OK $f"
done
```
Expected: 三个 `OK ...`

- [ ] **Step 2: 全脚本语法检查**

Run:
```bash
for f in plugins/narness-rust/hooks/scripts/post-edit-gate.sh plugins/narness-rust/scripts/*.sh; do
  bash -n "$f" && echo "OK $f"
done
```
Expected: 四个 `OK ...`

- [ ] **Step 3: 对照设计文档第 7 节验收标准逐条核对**

核对清单：
1. 目录结构完整（Task 1）
2. marketplace/plugin JSON 格式正确（Task 2/3）
3. skill 覆盖 5.2 大纲（Task 9）
4. hook + 三脚本存在且可执行（Task 10–13）
5. 四篇理论文档存在，核心命题贯穿（Task 5–8）
6. README 简述理念与用法（Task 4）

- [ ] **Step 4: 最终目录树检查**

Run: `find . -type f -not -path './.git/*' | sort`
Expected: 输出包含全部 14 个目标文件（1 LICENSE + 1 README + 3 JSON + 1 SKILL.md + 4 脚本 + 4 理论文档）。

- [ ] **Step 5: Commit（如有遗漏文件）**

```bash
git status --short
git add -A
git commit -m "chore: finalize Narness scaffold" --allow-empty
```
Expected: 工作区干净（`git status` 无未提交变更）。
