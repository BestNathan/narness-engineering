#!/usr/bin/env bash
# verify-test.sh — 只做测试（cargo test）
# 用法: verify-test.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo test"
cargo test
echo "==> 测试通过"
