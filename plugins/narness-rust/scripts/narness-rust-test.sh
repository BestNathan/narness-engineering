#!/usr/bin/env bash
# narness-rust-test.sh — do only the tests (cargo test)
# usage: narness-rust-test.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo test"
cargo test
echo "==> tests passed"
