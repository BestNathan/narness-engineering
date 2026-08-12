#!/usr/bin/env bash
# check.sh — Narness Rust 完整门禁
# 用法: check.sh [PROJECT_DIR]
# 依次运行: cargo fmt --check → cargo clippy -D warnings → cargo test
set -euo pipefail

PROJECT_DIR="${1:-.}"

echo "==> Narness 完整门禁: $PROJECT_DIR"
cd "$PROJECT_DIR"

echo "==> 1/3 cargo fmt --check"
cargo fmt --check

echo "==> 2/3 cargo clippy --all-targets --all-features -- -D warnings"
cargo clippy --all-targets --all-features -- -D warnings

echo "==> 3/3 cargo test"
cargo test

echo "==> 全部通过"
