# Claude Code hooks: harness execution at agent tool-call time

## 1. Mechanism

Claude Code fires hooks at each node of the agent's lifecycle, executing external scripts. A hook is a constraint at the "agent layer" — it intercepts or feeds back when the agent edits files, calls tools, or starts/ends a session.

This is Narness's most important execution layer: **a hook can feed a validation failure directly back to the LLM**, letting the agent discover and fix problems itself.

## 2. Full event table

| Event | Timing | exit-2 effect | Use |
|---|---|---|---|
| `PreToolUse` | before a tool executes | **block** the tool call | block/rewrite calls that shouldn't happen |
| `PostToolUse` | after a tool executes | non-blocking, stderr fed back to Claude | validate, auto-format, feedback |
| `PostToolUseFailure` | after a tool fails | non-blocking, stderr feedback | error triage, logging |
| `PostToolBatch` | after a batch of parallel tool calls resolves | **block** (halt the agentic loop) | batch-level validation |
| `UserPromptSubmit` | when the user submits a prompt | **block** and erase the prompt | inject/validate user input |
| `UserPromptExpansion` | when a prompt expands | **block** the expansion | gate slash commands |
| `Stop` | when Claude is about to end its response | **block** (force it to continue) | "don't stop until tests pass" |
| `SubagentStop` | when a subagent is about to end | **block** the subagent's stop | subagent continuation logic |
| `SessionStart` | session start/resume | non-blocking, stderr to user | inject context, set env |
| `SessionEnd` | session end | non-blocking | cleanup, logging |
| `PreCompact` | before context compaction | **block** compaction | stash custom instructions |
| `Setup` | during `claude` setup | non-blocking | install-time guidance |
| `Notification` | when a system notification is produced | non-blocking | custom reminders |
| `PermissionRequest` | at the permission prompt | **block** (deny permission) | automated permission policy |
| `PermissionDenied` | after permission is denied | ignored (JSON `retry`) | respond to denial |

For a harness, the most useful are `PreToolUse` (block) and `PostToolUse` (feedback).

## 3. Exit codes and feedback mechanism (core contract)

This is the core of Claude Code hooks — it directly determines whether a harness can "let the agent discover problems":

| Exit code | Meaning |
|---|---|
| `0` | passed (happy path should be silent, no stdout) |
| `2` | **block** (blocking events like PreToolUse) or **feedback** (events like PostToolUse) |
| `1` / other | non-blocking warning, does **not** block |

**Feedback path**: when `PostToolUse` exits 2, the hook's **stderr is injected into Claude's context as a system message**. This is where Narness's "let the agent discover its own problems" lands.

Three iron rules:

1. **stdout = JSON control channel** (with exit 0, if stdout is produced it's parsed as JSON)
2. **stderr = feedback text** (what the agent actually sees)
3. **exit 2 = trigger feedback/block**; exit 1 is just a warning, no block

So on validation failure, the script must write diagnostics to **stderr**, or the agent won't see them:

```bash
# Right: write diagnostics to stderr; the hook feeds them back to Claude
if ! out="$(cargo check 2>&1)"; then
  printf '%s\n' "$out" >&2
  exit 2
fi
```

## 4. stdin input

Each hook command receives JSON on **stdin**. Common fields: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `permission_mode`.

Tool events (PreToolUse / PostToolUse) additionally contain:

```json
{
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_use_id": "toolu_01...",
  "tool_input": { "file_path": "/path/src/lib.rs", "old_string": "...", "new_string": "..." },
  "tool_response": { "...": "..." }
}
```

Extract `tool_input.file_path` to tell which file changed.

## 5. Configuration locations

| Scope | Path |
|---|---|
| User | `~/.claude/settings.json` |
| Project (shared) | `<project>/.claude/settings.json` |
| Project (local) | `<project>/.claude/settings.local.json` (git-ignored) |
| Plugin | `<plugin>/hooks/hooks.json` (loaded when the plugin is enabled) |

Priority (on conflict): managed/enterprise → CLI args → local project → shared project → user.

## 6. matcher semantics

`matcher` filters hook firing:

| Event | matcher matches |
|---|---|
| Tool events (Pre/PostToolUse, etc.) | **tool name** (regex): `Bash`, `Write\|Edit`, `mcp__.*`, `*` |
| `UserPromptSubmit` | **prompt text** (regex) |
| `SessionStart` etc. lifecycle | unused (`true` or `""`) |

## 7. Concrete examples

### 7.1 PostToolUse: compile feedback after edit

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

Points: `matcher` restricts to file-editing tools; `async: false` guarantees the failure can be fed back; `${CLAUDE_PLUGIN_ROOT}` locates the plugin directory.

### 7.2 PreToolUse: block dangerous commands

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

`guard-bash.sh` checks whether the command contains dangerous patterns like `rm -rf /`; on a hit, stderr + exit 2 **blocks** execution.

### 7.3 Stop: don't stop until tests pass

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/narness-rust-test.sh",
            "timeout": 300
          }
        ]
      }
    ]
  }
}
```

A failing test exits 2, forcing Claude to keep fixing until it passes.

## 8. Relationship to the narness-rust plugin

narness-rust's `post-edit-gate.sh` is the Claude Code adapter layer: parse stdin JSON → judge whether it's a `.rs` file → delegate to `narness-rust-check.sh` → on failure write stderr + exit 2. It is the bridge between "the Claude Code hook contract" and "single-responsibility validation scripts".

## 9. Position in the layered harness

Claude Code hooks are "edit-level" constraints — finest granularity, most immediate feedback:

```
After edit (Claude Code PostToolUse) → pre-commit (git) → pre-push (git) → CI
  compile error fed back immediately   block bad code   full test gate   regression protection
```

They answer Narness's core question: **how to let the agent see and fix errors while they're still small**.
