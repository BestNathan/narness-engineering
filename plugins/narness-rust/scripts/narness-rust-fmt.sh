#!/usr/bin/env bash
# narness-rust-fmt.sh — do only a format check (cargo fmt --all -- --check)
# usage: narness-rust-fmt.sh [PROJECT_DIR]
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo fmt --all -- --check"
if ! cargo fmt --all -- --check; then
  echo "⚠ format drift detected: the files above are not rustfmt-clean" >&2
  echo "   fix: run 'cargo fmt --all' to auto-format, then re-commit" >&2
  exit 1
fi
echo "==> format check passed"
