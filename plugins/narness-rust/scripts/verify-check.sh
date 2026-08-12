#!/usr/bin/env bash
# verify-check.sh — 只做编译检查（cargo check）
# 用法: verify-check.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo check"
cargo check
echo "==> 编译检查通过"
