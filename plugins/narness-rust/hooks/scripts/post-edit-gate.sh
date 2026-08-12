#!/usr/bin/env bash
# post-edit-gate.sh — PostToolUse 快速门禁（hook 入口）
# 由 Claude Code hook 调用，stdin 传入 hook JSON。
# 职责：判断改动是否为 .rs 文件；是则调用 verify-check.sh 做编译检查。
# 失败时 stderr + exit 2 反馈给 Claude。
set -uo pipefail

input="$(cat)"

# 提取 tool_input.file_path（Edit/Write/MultiEdit 的输入键名）
file_path="$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)"

# 非 .rs 文件直接放行
case "$file_path" in
  *.rs) ;;
  *) exit 0 ;;
esac

# 调用单一职责脚本做编译检查；失败时把输出写到 stderr（exit 2 回传 Claude）
if ! out="$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/verify-check.sh" 2>&1)"; then
  printf '%s\n' "$out" | tail -n 30 >&2
  echo "⚠ Narness 快速门禁: cargo check 失败，请修复编译错误" >&2
  exit 2
fi

exit 0
