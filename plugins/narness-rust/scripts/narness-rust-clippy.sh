#!/usr/bin/env bash
# narness-rust-clippy.sh — do only a lint check (cargo clippy -D warnings)
# usage: narness-rust-clippy.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo clippy --all-targets --all-features -- -D warnings"
cargo clippy --all-targets --all-features -- -D warnings
echo "==> lint check passed"
