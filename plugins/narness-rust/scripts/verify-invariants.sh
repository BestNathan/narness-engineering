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
