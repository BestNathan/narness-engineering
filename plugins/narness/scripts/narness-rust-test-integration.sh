#!/usr/bin/env bash
# narness-rust-test-integration.sh — integration-test gate (tier 2): tests/ dir, public API only
# usage: narness-rust-test-integration.sh [PROJECT_DIR] [--scope=changed|full] [--coverage]
#   --scope=changed  run integration tests for only the crates changed since the last push
#   --scope=full     run integration tests for the whole workspace (default; CI)
#   --coverage       enforce the ≥80% line-coverage threshold via llvm-cov; default is run-only
# requires cargo-llvm-cov only when --coverage is passed.
set -euo pipefail

SCOPE="full"
COVERAGE=0
PROJECT_DIR="."
for arg in "$@"; do
  case "$arg" in
    --scope=changed) SCOPE="changed" ;;
    --scope=full) SCOPE="full" ;;
    --coverage) COVERAGE=1 ;;
    *) PROJECT_DIR="$arg" ;;
  esac
done
cd "$PROJECT_DIR"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

selector="--workspace"
if [[ "$SCOPE" == "changed" ]]; then
  pkgs="$(bash "$DIR/narness-rust-changed-packages.sh" .)"
  if [[ -z "$pkgs" ]]; then
    echo "✓ no changed crates — integration tests skipped"
    exit 0
  fi
  if [[ "$pkgs" != "WORKSPACE" ]]; then
    selector="$(printf '%s\n' "$pkgs" | sed 's/^/-p /' | tr '\n' ' ' | sed 's/ $//')"
  fi
fi

if [[ "$COVERAGE" == 1 ]]; then
  echo "==> cargo llvm-cov $selector --tests --fail-under-lines 80"
  if ! cargo llvm-cov $selector --tests --fail-under-lines 80; then
    echo "⚠ integration-test gate failed: an integration test failed, or integration coverage < 80%" >&2
    echo "   fix: add integration tests for the uncovered paths above, then re-run CI" >&2
    exit 1
  fi
  echo "==> integration tests passed (coverage >= 80%)"
else
  echo "==> cargo test $selector --tests"
  cargo test $selector --tests
  echo "==> integration tests passed"
fi
