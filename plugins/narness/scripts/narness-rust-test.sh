#!/usr/bin/env bash
# narness-rust-test.sh — do only the tests, full suite (cargo test --workspace)
# usage: narness-rust-test.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo test --workspace"
cargo test --workspace
echo "==> tests passed"
