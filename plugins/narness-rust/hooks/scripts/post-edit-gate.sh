#!/usr/bin/env bash
# post-edit-gate.sh — PostToolUse fast gate (hook entrypoint)
# called by a Claude Code hook; hook JSON arrives on stdin.
# responsibility: judge whether the change is a .rs file; if so, call narness-rust-check.sh for a compile check.
# on failure: stderr + exit 2 to feed back to Claude.
set -uo pipefail

input="$(cat)"

# extract tool_input.file_path (the input key for Edit/Write/MultiEdit)
file_path="$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)"

# non-.rs files pass through
case "$file_path" in
  *.rs) ;;
  *) exit 0 ;;
esac

# call the single-responsibility script for a compile check; on failure write output to stderr (exit 2 feeds back to Claude)
if ! out="$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/narness-rust-check.sh" 2>&1)"; then
  printf '%s\n' "$out" | tail -n 30 >&2
  echo "⚠ Narness fast gate: cargo check failed, please fix the compile errors" >&2
  exit 2
fi

exit 0
