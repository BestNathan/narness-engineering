# Codex hooks: harness execution in the OpenAI Codex CLI

## 1. Mechanism

The OpenAI Codex CLI also has a hook mechanism (stable since v0.124). Like Claude Code, it fires external scripts at agent lifecycle nodes, but **the feedback mechanism is fundamentally different**.

Hooks must be enabled via a feature flag:

```toml
# config.toml
[features]
codex_hooks = true
```

## 2. Configuration

Two equivalent forms:

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

### 2.2 Inline in `config.toml`

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

## 3. Event list

| Event | Timing | Use |
|---|---|---|
| `SessionStart` | session start/resume/clear/compact | inject context |
| `PreToolUse` | before a tool executes | block/rewrite calls |
| `PostToolUse` | after a tool executes | validate, feedback |
| `SubagentStop` | subagent ends | subagent continuation logic |
| `Stop` | session ends | end-of-session validation |
| `UserPromptSubmit` | user submits a prompt | inject/validate input |
| `PermissionRequest` | permission request | automate permissions |

## 4. Key limitation

**`PreToolUse` / `PostToolUse` only intercept three kinds of tools**:

- `Bash`
- `apply_patch` (an alias for Edit/Write)
- MCP tools (`mcp__…`)

Not every tool path can mount a hook — an important difference between Codex and Claude Code.

## 5. Output contract (the fundamental difference from Claude Code)

Codex's feedback mechanism **differs** from Claude Code's. Claude Code uses "exit 2 + stderr"; Codex uses **stdout JSON**:

### 5.1 Inject context (let the model see it)

```json
{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "test failed: src/lib.rs line 3 …"}}
```

`additionalContext` is text the **model can see**, used to feed back failure info.

### 5.2 Block a tool (PreToolUse)

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "dangerous command"}}
```

### 5.3 Block a result (PostToolUse / Stop)

```json
{"decision": "block", "reason": "tests did not pass"}
```

### 5.4 Exit codes

| Exit code | Meaning |
|---|---|
| `0` | success, stdout JSON is parsed |
| `2` | special behavior (PreToolUse blocks the tool / PostToolUse blocks the result; reason read from stderr) |
| other non-zero | hook failed; an error is reported but processing continues |

**Constraint**: `permissionDecisionReason` / `reason` are **required** on deny/block; the schema is strictly validated, and extra fields invalidate the whole output so the action isn't intercepted.

## 6. Relationship to AGENTS.md

- **AGENTS.md** is Codex's conventions file (like Claude Code's CLAUDE.md), discovered hierarchically: global `~/.codex/AGENTS.md` + per-project walking
- Default size cap 32 KiB; silently truncated beyond it
- AGENTS.md is the **static instruction layer** (project conventions, test commands, code style); hooks are the **dynamic execution layer** — complementary: AGENTS.md says "what you should do", hooks enforce "what you must do"

## 7. Concrete example: PostToolUse mounts a compile check

The Codex-side adapter layer (distinct from Claude Code's stderr mechanism):

```bash
#!/usr/bin/env bash
# ~/.codex/hooks/post-edit-gate.sh
# read stdin JSON, judge whether a .rs file changed; if so run narness-rust-check.sh;
# on failure feed back to the model via stdout JSON's additionalContext
input="$(cat)"
file_path="$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)"

case "$file_path" in
  *.rs) ;;
  *) exit 0 ;;
esac

if ! out="$(bash /path/to/narness-rust-check.sh 2>&1)"; then
  # Codex injects via stdout JSON, not stderr
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"cargo check failed:\n" + sys.argv[1]}}))' "$out"
  exit 0
fi
exit 0
```

Note: injecting context uses **stdout JSON + exit 0** (not exit 2 + stderr).

## 8. Codex vs Claude Code comparison

| Dimension | Claude Code | Codex |
|---|---|---|
| Config | `settings.json` / plugin `hooks.json` | `.codex/hooks.json` + feature flag |
| Feedback to LLM | **exit 2 + stderr** | **stdout JSON** `additionalContext` |
| Block a tool | PreToolUse exit 2 | PreToolUse `permissionDecision: deny` |
| Block a result | Stop exit 2 | `{"decision": "block"}` |
| Interception scope | all tools | only Bash / apply_patch / MCP |
| Conventions file | CLAUDE.md | AGENTS.md |

**Narness meaning**: the same harness validation script — the core logic (`narness-rust-check.sh`) — is reusable, but the "feedback adapter layer" differs per tool: Claude Code uses exit 2 + stderr, Codex uses stdout JSON.

## 9. Position in the layered harness

Codex hooks are "edit-level" constraints, same tier as Claude Code hooks, adapted differently:

```
After edit (Codex PostToolUse) → pre-commit (git) → pre-push (git) → CI
  compile error fed back to model   block bad code   full test gate   regression protection
```

Key engineering decision: **write validation logic once** (`narness-rust-*.sh`); write a thin adapter per tool.
