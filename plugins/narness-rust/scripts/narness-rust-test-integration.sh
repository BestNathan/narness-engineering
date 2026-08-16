#!/usr/bin/env bash
# narness-rust-test-integration.sh — integration-test gate (tier 2): tests/ dir, public API only
# runs integration tests and enforces >= 80% line coverage in a single llvm-cov pass.
# requires: cargo-llvm-cov
# usage: narness-rust-test-integration.sh [PROJECT_DIR]
# trigger: CI — integration tests are slower than unit and only reach the pub surface; they stay out of the push path.
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo llvm-cov --tests --fail-under-lines 80"
if ! cargo llvm-cov --tests --fail-under-lines 80; then
  echo "⚠ integration-test gate failed: an integration test failed, or integration coverage < 80%" >&2
  echo "   fix: add integration tests for the uncovered paths above, then re-run CI" >&2
  exit 1
fi
echo "==> integration tests passed (coverage >= 80%)"
