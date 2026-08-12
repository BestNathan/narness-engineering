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
