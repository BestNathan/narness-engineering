#!/usr/bin/env bash
# verify-fmt.sh — 只做格式检查（cargo fmt --check）
# 用法: verify-fmt.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo fmt --check"
cargo fmt --check
echo "==> 格式检查通过"
