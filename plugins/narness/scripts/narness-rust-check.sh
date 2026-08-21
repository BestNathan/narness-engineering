#!/usr/bin/env bash
# narness-rust-check.sh — do only a compile check (cargo check)
# usage: narness-rust-check.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo check"
cargo check
echo "==> compile check passed"
