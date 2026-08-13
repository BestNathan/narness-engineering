#!/usr/bin/env bash
# narness-rust-fmt.sh — do only a format check (cargo fmt --check)
# usage: narness-rust-fmt.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo fmt --check"
cargo fmt --check
echo "==> format check passed"
