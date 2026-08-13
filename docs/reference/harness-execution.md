# Harness 脚本的执行机制与时机

## 1. 总览

校验脚本是「代码约束」的实体，但**脚本本身不会自动生效**——它只有挂到工具的「事件钩子」上，才会在特定时机被自动执行。本文档说明三种执行层面：

| 层面 | 工具 | 时机 | 约束粒度 |
|---|---|---|---|
| 版本控制 | git hooks | commit / push 时 | 提交级（粗） |
| 编码 agent | Claude Code hooks | 工具调用 / 会话生命周期 | 编辑级（细） |
| 编码 agent | Codex hooks | 工具调用 / 会话生命周期 | 编辑级（细） |

核心命题：**一个 harness 脚本可以挂到多个时机**，形成分层防线——编辑后即时反馈（细粒度）+ 提交前门禁（阻止坏代码入库）+ 推送/CI（回归保护）。

## 2. Git hooks（提交/推送时机）

### 2.1 机制

git 在特定动作前后执行 `.git/hooks/` 下的脚本：

| 钩子 | 时机 | 典型用途 |
|---|---|---|
| `pre-commit` | `git commit` 前，提交信息编辑器弹出前 | 格式、lint、测试 |
| `commit-msg` | 提交信息编辑后 | 校验提交信息格式 |
| `pre-push` | `git push` 前 | 全量测试、较重门禁 |

配置方式：
- 直接写 `.git/hooks/pre-commit`（需 `chmod +x`，但 `.git/` 不入库，无法共享）
- 用 `git config core.hooksPath` 指向仓库内目录（如 `.githooks/`，可共享）
- 用 pre-commit 框架（`.pre-commit-config.yaml`，跨语言，自动管理）

### 2.2 示例：把 verify 脚本挂到 pre-commit

```bash
#!/usr/bin/env bash
# .githooks/pre-commit — 提交前跑格式 + lint（单一职责脚本，逐个调用）
set -euo pipefail
bash plugins/narness-rust/scripts/verify-fmt.sh
bash plugins/narness-rust/scripts/verify-clippy.sh
```

启用：`git config core.hooksPath .githooks`

**注意**：pre-commit 阶段应跑**快**的检查（fmt、lint），全量测试留给 pre-push 或 CI——否则每次提交都跑全量测试会拖慢开发。

## 3. Claude Code hooks（agent 工具调用时机）

### 3.1 事件总览

Claude Code 在 agent 生命周期各节点触发 hook。对 harness 最有价值的事件：

| 事件 | 时机 | 用途 |
|---|---|---|
| `PreToolUse` | 工具执行**前** | **阻止**（exit 2）不该发生的调用；改写输入 |
| `PostToolUse` | 工具执行**后** | **反馈**（exit 2）把校验失败回传给 Claude |
| `PostToolUseFailure` | 工具失败后 | 错误分诊、日志 |
| `Stop` | Claude 即将结束响应 | 强制继续（如「测试没过不许停」） |
| `SessionStart` | 会话开始/恢复 | 注入上下文、设置环境 |
| `UserPromptSubmit` | 用户提交提示词时 | 注入/校验用户输入 |
| `PreCompact` | 上下文压缩前 | 阻止/暂存自定义指令 |

（其余：`PostToolBatch`、`UserPromptExpansion`、`SubagentStop`、`SessionEnd`、`Setup`、`Notification`、`PermissionRequest`、`PermissionDenied`。）

### 3.2 退出码与反馈机制（关键）

这是 Claude Code hook 的核心契约：

| 退出码 | 含义 |
|---|---|
| `0` | 通过（happy path 应静默，无 stdout） |
| `2` | **阻止**（PreToolUse）或**反馈**（PostToolUse 等） |
| `1` / 其他 | 非阻塞警告，不阻止 |

**反馈路径**：`PostToolUse` 退出码 2 时，hook 的 **stderr 会作为系统消息注入 Claude 上下文**，让 agent 看到失败并修复。这是 Narness 的「让 agent 自己发现问题」的落地点。

规则：**stdout = JSON 控制通道；stderr = 反馈文本；exit 2 = 触发反馈/阻止**。所以校验失败时，脚本必须把诊断写到 **stderr**（不是 stdout），否则 agent 看不到。

### 3.3 配置位置

| 作用域 | 路径 |
|---|---|
| 用户 | `~/.claude/settings.json` |
| 项目（共享） | `<project>/.claude/settings.json` |
| 项目（本地） | `<project>/.claude/settings.local.json`（git-ignore） |
| 插件 | `<plugin>/hooks/hooks.json`（启用插件即加载） |

### 3.4 示例：PostToolUse 挂校验脚本

```json
{
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

要点：`matcher` 用工具名（正则，`|` 交替）；`async: false` 保证失败能反馈回 agent；`${CLAUDE_PLUGIN_ROOT}` 定位插件目录。

## 4. Codex hooks（agent 工具调用时机）

OpenAI Codex CLI 也有 hook 机制（v0.124 起稳定）。

### 4.1 机制与配置

- 配置：`.codex/hooks.json`，或 `config.toml` 里的 `[[hooks.<Event>]]` 块
- 需启用 feature flag：`codex_hooks = true`（`[features]` 表）
- 事件：`SessionStart`、`PreToolUse`、`PostToolUse`、`SubagentStop`、`Stop`、`UserPromptSubmit`、`PermissionRequest`

```toml
# config.toml
[features]
codex_hooks = true

[[hooks.PostToolUse]]
matcher = "^Bash$"

[[hooks.PostToolUse.hooks]]
type = "command"
command = '/usr/bin/bash ~/.codex/hooks/post-edit-gate.sh'
timeout = 30
```

### 4.2 关键限制

`PreToolUse` / `PostToolUse` 只拦截 **`Bash`、`apply_patch`（Edit/Write 的别名）、MCP 工具**——不是所有工具路径。

### 4.3 输出契约（与 Claude Code 不同）

Codex 的反馈机制与 Claude Code 有本质区别：

- **注入上下文**：用 **stdout JSON**，而非 exit 2 + stderr：

```json
{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "测试失败：src/lib.rs 第 3 行 …"}}
```

- **阻止工具**（PreToolUse）：`permissionDecision: "deny"`
- **阻止结果**（PostToolUse / Stop）：顶层 `{"decision": "block"}`

退出码：`0` = 成功（stdout JSON 被解析）；`2` = 特殊行为（PreToolUse 阻止工具 / PostToolUse 阻止结果，原因从 stderr 读）。

### 4.4 Claude Code vs Codex 对比

| 维度 | Claude Code | Codex |
|---|---|---|
| 配置 | `settings.json` / 插件 `hooks.json` | `.codex/hooks.json` + feature flag |
| 反馈给 LLM | **exit 2 + stderr** 注入 | **stdout JSON** `additionalContext` 注入 |
| 阻止工具 | PreToolUse exit 2 | PreToolUse `permissionDecision: deny` |
| 拦截范围 | 所有工具 | 仅 Bash / apply_patch / MCP |
| 约定文件 | CLAUDE.md | AGENTS.md |

**Narness 含义**：同一个 harness 脚本，挂到不同工具时需要不同的「反馈适配层」——Claude Code 用 exit 2 + stderr，Codex 用 stdout JSON。脚本的核心校验逻辑可复用，适配层按工具写。

## 5. 分层组合

把 harness 脚本挂到多个时机，形成分层防线：

| 时机 | 挂载点 | 跑什么 | 失败后果 |
|---|---|---|---|
| 编辑后 | Claude Code `PostToolUse` / Codex `PostToolUse` | `verify-check.sh`（编译） | 即时反馈，agent 修复 |
| 提交前 | git `pre-commit` | `verify-fmt.sh` + `verify-clippy.sh` | 阻止提交 |
| 推送前 | git `pre-push` | `verify-test.sh` + 覆盖率 | 阻止推送 |
| CI | CI pipeline | 全量 nextest + llvm-cov 阈值 + 不变量 + 测试纪律 | 回归保护 |

**设计原则**：越靠前的时机越要快（hook 跑编译，不跑全量测试）；越靠后的时机越重（CI 跑全量 + 覆盖率）。同一个脚本在不同时机复用，核心逻辑不变，只有「反馈方式」随工具不同而变。

## 6. 与 narness-rust 的关系

narness-rust 插件的 `post-edit-gate.sh` 就是「Claude Code 适配层」——它解析 PostToolUse 的 stdin JSON、判断是否 `.rs`、委派给 `verify-check.sh`、失败时写 stderr + exit 2。如果要把同样的校验挂到 Codex 或 git，只需写对应工具的适配层，复用 `verify-*.sh` 核心逻辑。
