#!/usr/bin/env bash
# verify-clippy.sh — 只做 lint 检查（cargo clippy -D warnings）
# 用法: verify-clippy.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo clippy --all-targets --all-features -- -D warnings"
cargo clippy --all-targets --all-features -- -D warnings
echo "==> lint 检查通过"
