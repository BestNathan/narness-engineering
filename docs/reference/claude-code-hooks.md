# Claude Code Hooks：agent 工具调用时机的 harness 执行

## 1. 机制原理

Claude Code 在 agent 生命周期各节点触发 hook，执行外部脚本。hook 是「编码 agent 层」的约束——在 agent 编辑文件、调用工具、开始/结束会话时拦截或反馈。

这是 Narness 最核心的执行层：**hook 能把校验失败直接反馈给 LLM**，让 agent 自己发现问题并修复。

## 2. 完整事件表

| 事件 | 时机 | exit 2 效果 | 用途 |
|---|---|---|---|
| `PreToolUse` | 工具执行**前** | **阻止**工具调用 | 阻止/改写不该发生的调用 |
| `PostToolUse` | 工具执行**后** | 非阻塞，stderr 反馈给 Claude | 校验、自动格式化、反馈 |
| `PostToolUseFailure` | 工具失败后 | 非阻塞，stderr 反馈 | 错误分诊、日志 |
| `PostToolBatch` | 一批并行工具调用解析后 | **阻止**（停下 agentic loop） | 批级校验 |
| `UserPromptSubmit` | 用户提交提示词时 | **阻止**并擦除提示词 | 注入/校验用户输入 |
| `UserPromptExpansion` | 提示词展开时 | **阻止**展开 | 门控快捷指令 |
| `Stop` | Claude 即将结束响应 | **阻止**（强制继续） | 「测试没过不许停」 |
| `SubagentStop` | 子 agent 即将结束 | **阻止**子 agent 停止 | 子 agent 继续逻辑 |
| `SessionStart` | 会话开始/恢复 | 非阻塞，stderr 给用户 | 注入上下文、设环境 |
| `SessionEnd` | 会话结束 | 非阻塞 | 清理、日志 |
| `PreCompact` | 上下文压缩前 | **阻止**压缩 | 暂存自定义指令 |
| `Setup` | `claude` setup 时 | 非阻塞 | 安装时引导 |
| `Notification` | 系统通知产生时 | 非阻塞 | 自定义提醒 |
| `PermissionRequest` | 权限弹窗时 | **阻止**（拒绝权限） | 自动化权限策略 |
| `PermissionDenied` | 权限被拒后 | 忽略（用 JSON `retry`） | 响应拒绝 |

对 harness 最有用的是 `PreToolUse`（阻止）和 `PostToolUse`（反馈）。

## 3. 退出码与反馈机制（核心契约）

这是 Claude Code hook 的核心，直接决定 harness 能否「让 agent 发现问题」：

| 退出码 | 含义 |
|---|---|
| `0` | 通过（happy path 应静默，无 stdout） |
| `2` | **阻止**（PreToolUse 等阻塞事件）或**反馈**（PostToolUse 等） |
| `1` / 其他 | 非阻塞警告，**不**阻止 |

**反馈路径**：`PostToolUse` 退出码 2 时，hook 的 **stderr 会作为系统消息注入 Claude 上下文**。这是 Narness 的「让 agent 自己发现问题」的落地点。

三条铁律：

1. **stdout = JSON 控制通道**（exit 0 时若输出 stdout，会被当作 JSON 解析）
2. **stderr = 反馈文本**（agent 实际看到的）
3. **exit 2 = 触发反馈/阻止**；exit 1 只是警告，不阻止

所以校验失败时，脚本必须把诊断写到 **stderr**，否则 agent 看不到：

```bash
# 正确：诊断写 stderr，hook 回传给 Claude
if ! out="$(cargo check 2>&1)"; then
  printf '%s\n' "$out" >&2
  exit 2
fi
```

## 4. stdin 输入

每个 hook 命令从 **stdin** 接收 JSON。通用字段：`session_id`、`transcript_path`、`cwd`、`hook_event_name`、`permission_mode`。

工具事件（PreToolUse / PostToolUse）额外含：

```json
{
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_use_id": "toolu_01...",
  "tool_input": { "file_path": "/path/src/lib.rs", "old_string": "...", "new_string": "..." },
  "tool_response": { "...": "..." }
}
```

提取 `tool_input.file_path` 即可判断改动的文件。

## 5. 配置位置

| 作用域 | 路径 |
|---|---|
| 用户 | `~/.claude/settings.json` |
| 项目（共享） | `<project>/.claude/settings.json` |
| 项目（本地） | `<project>/.claude/settings.local.json`（git-ignore） |
| 插件 | `<plugin>/hooks/hooks.json`（启用插件即加载） |

优先级（冲突时）：managed/enterprise → CLI 参数 → 本地项目 → 共享项目 → 用户。

## 6. matcher 语义

`matcher` 用于过滤 hook 触发：

| 事件 | matcher 匹配 |
|---|---|
| 工具事件（Pre/PostToolUse 等） | **工具名**（正则）：`Bash`、`Write\|Edit`、`mcp__.*`、`*` |
| `UserPromptSubmit` | **提示词文本**（正则） |
| `SessionStart` 等生命周期 | 不用（`true` 或 `""`） |

## 7. 具体示例

### 7.1 PostToolUse：编辑后编译反馈

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

要点：`matcher` 限定改文件工具；`async: false` 保证失败能反馈；`${CLAUDE_PLUGIN_ROOT}` 定位插件目录。

### 7.2 PreToolUse：阻止危险命令

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/guard-bash.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

`guard-bash.sh` 检查命令是否含 `rm -rf /` 等危险模式，命中则 stderr + exit 2 **阻止**执行。

### 7.3 Stop：测试没过不许停

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/verify-test.sh",
            "timeout": 300
          }
        ]
      }
    ]
  }
}
```

测试失败则 exit 2，强制 Claude 继续修，直到通过。

## 8. 与 narness-rust 插件的关系

narness-rust 的 `post-edit-gate.sh` 就是 Claude Code 适配层：解析 stdin JSON → 判断是否 `.rs` → 委派给 `verify-check.sh` → 失败写 stderr + exit 2。它是「Claude Code hook 契约」与「单一职责校验脚本」之间的桥。

## 9. 在分层 harness 中的位置

Claude Code hook 是「编辑级」约束，粒度最细、反馈最即时：

```
编辑后（Claude Code PostToolUse）→ 提交前（git pre-commit）→ 推送前（git pre-push）→ CI
  编译错误即时反馈 agent         阻止坏代码入库          全量测试门禁          回归保护
```

它回答 Narness 的核心问题：**如何让 agent 在错误还小时就看到并修复**。
