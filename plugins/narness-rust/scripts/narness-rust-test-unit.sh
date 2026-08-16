#!/usr/bin/env bash
# narness-rust-test-unit.sh — unit-test gate (tier 1): #[cfg(test)] mod tests under src/
# runs unit tests and enforces >= 95% line coverage in a single llvm-cov pass.
# requires: cargo-llvm-cov
# usage: narness-rust-test-unit.sh [PROJECT_DIR]
# trigger: every push (pre-push) — unit tests are in-process and fast (no I/O/network), so they run often.
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo llvm-cov --lib --fail-under-lines 95"
if ! cargo llvm-cov --lib --fail-under-lines 95; then
  echo "⚠ unit-test gate failed: a unit test failed, or unit coverage < 95%" >&2
  echo "   fix: add unit tests for the uncovered lines above, then re-push" >&2
  exit 1
fi
echo "==> unit tests passed (coverage >= 95%)"
