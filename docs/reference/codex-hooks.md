# Codex Hooks：OpenAI Codex CLI 的 harness 执行

## 1. 机制原理

OpenAI Codex CLI 也有 hook 机制（v0.124 起稳定）。与 Claude Code 类似，它在 agent 生命周期节点触发外部脚本，但**反馈机制有本质区别**。

hooks 需通过 feature flag 启用：

```toml
# config.toml
[features]
codex_hooks = true
```

## 2. 配置方式

两种等价写法：

### 2.1 `.codex/hooks.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^Bash$",
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/bash ~/.codex/hooks/post-edit-gate.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### 2.2 `config.toml` 内联

```toml
[features]
codex_hooks = true

[[hooks.PostToolUse]]
matcher = "^Bash$"

[[hooks.PostToolUse.hooks]]
type = "command"
command = '/usr/bin/bash ~/.codex/hooks/post-edit-gate.sh'
timeout = 30
statusMessage = "Validating after Bash"
```

## 3. 事件列表

| 事件 | 时机 | 用途 |
|---|---|---|
| `SessionStart` | 会话开始/恢复/clear/compact | 注入上下文 |
| `PreToolUse` | 工具执行前 | 阻止/改写调用 |
| `PostToolUse` | 工具执行后 | 校验、反馈 |
| `SubagentStop` | 子 agent 结束 | 子 agent 继续逻辑 |
| `Stop` | 会话结束 | 结束前校验 |
| `UserPromptSubmit` | 用户提交提示词 | 注入/校验输入 |
| `PermissionRequest` | 权限请求 | 自动化权限 |

## 4. 关键限制

**`PreToolUse` / `PostToolUse` 只拦截三种工具**：
- `Bash`
- `apply_patch`（Edit/Write 的别名）
- MCP 工具（`mcp__…`）

不是所有工具路径都能挂 hook——这是 Codex 与 Claude Code 的一个重要差异。

## 5. 输出契约（与 Claude Code 的本质区别）

Codex 的反馈机制与 Claude Code **不同**。Claude Code 用「exit 2 + stderr」，Codex 用 **stdout JSON**：

### 5.1 注入上下文（让模型看到）

```json
{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "测试失败：src/lib.rs 第 3 行 …"}}
```

`additionalContext` 是**模型可见**的文本，用于反馈失败信息。

### 5.2 阻止工具（PreToolUse）

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "危险命令"}}
```

### 5.3 阻止结果（PostToolUse / Stop）

```json
{"decision": "block", "reason": "测试未通过"}
```

### 5.4 退出码

| 退出码 | 含义 |
|---|---|
| `0` | 成功，stdout JSON 被解析 |
| `2` | 特殊行为（PreToolUse 阻止工具 / PostToolUse 阻止结果，原因从 stderr 读） |
| 其他非零 | hook 失败，报错但处理继续 |

**约束**：`permissionDecisionReason` / `reason` 在 deny/block 时**必填**；schema 严格校验，多余字段会导致整个输出失效、动作不拦截。

## 6. 与 AGENTS.md 的关系

- **AGENTS.md** 是 Codex 的约定文件（类似 Claude Code 的 CLAUDE.md），分层发现：全局 `~/.codex/AGENTS.md` + 项目逐级 walk
- 默认大小上限 32 KiB，超限静默截断
- AGENTS.md 是**静态指令层**（项目约定、测试命令、代码风格），hooks 是**动态执行层**——两者互补：AGENTS.md 说「应该怎么做」，hooks 强制「必须这么做」

## 7. 具体示例：PostToolUse 挂编译检查

Codex 侧适配层（区别于 Claude Code 的 stderr 机制）：

```bash
#!/usr/bin/env bash
# ~/.codex/hooks/post-edit-gate.sh
# 读取 stdin JSON，判断是否改 .rs，是则跑 verify-check.sh，
# 失败时用 stdout JSON 的 additionalContext 反馈给模型
input="$(cat)"
file_path="$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)"

case "$file_path" in
  *.rs) ;;
  *) exit 0 ;;
esac

if ! out="$(bash /path/to/verify-check.sh 2>&1)"; then
  # Codex 用 stdout JSON 注入，而非 stderr
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"cargo check 失败：\n" + sys.argv[1]}}))' "$out"
  exit 0
fi
exit 0
```

注意：注入上下文用 **stdout JSON + exit 0**（不是 exit 2 + stderr）。

## 8. Codex vs Claude Code 对比

| 维度 | Claude Code | Codex |
|---|---|---|
| 配置 | `settings.json` / 插件 `hooks.json` | `.codex/hooks.json` + feature flag |
| 反馈给 LLM | **exit 2 + stderr** | **stdout JSON** `additionalContext` |
| 阻止工具 | PreToolUse exit 2 | PreToolUse `permissionDecision: deny` |
| 阻止结果 | Stop exit 2 | `{"decision": "block"}` |
| 拦截范围 | 所有工具 | 仅 Bash / apply_patch / MCP |
| 约定文件 | CLAUDE.md | AGENTS.md |

**Narness 含义**：同一个 harness 校验脚本，核心逻辑（`verify-check.sh`）可复用，但「反馈适配层」因工具而异——Claude Code 用 exit 2 + stderr，Codex 用 stdout JSON。

## 9. 在分层 harness 中的位置

Codex hook 是「编辑级」约束，与 Claude Code hook 同层，但适配方式不同：

```
编辑后（Codex PostToolUse）→ 提交前（git pre-commit）→ 推送前（git pre-push）→ CI
  编译错误即时反馈模型      阻止坏代码入库          全量测试门禁          回归保护
```

关键工程决策：**校验逻辑只写一次**（`verify-*.sh`），每个工具写一层薄的适配器。
