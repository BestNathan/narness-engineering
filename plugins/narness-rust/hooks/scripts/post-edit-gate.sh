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
