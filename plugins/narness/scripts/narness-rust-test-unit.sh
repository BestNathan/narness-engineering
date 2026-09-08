#!/usr/bin/env bash
# narness-rust-test-unit.sh — unit-test gate (tier 1): #[cfg(test)] mod tests under src/
# usage: narness-rust-test-unit.sh [PROJECT_DIR] [--scope=changed|full] [--coverage]
#   --scope=changed  run unit tests for only the crates changed since the last push (pre-push fast gate)
#   --scope=full     run unit tests for the whole workspace (default; CI)
#   --coverage       enforce the ≥95% line-coverage threshold via llvm-cov; default is run-only
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

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

selector="--workspace"
if [[ "$SCOPE" == "changed" ]]; then
  pkgs="$(bash "$DIR/narness-rust-changed-packages.sh" .)"
  if [[ -z "$pkgs" ]]; then
    echo "✓ no changed crates — unit tests skipped"
    exit 0
  fi
  if [[ "$pkgs" != "WORKSPACE" ]]; then
    selector="$(printf '%s
' "$pkgs" | sed 's/^/-p /' | tr '
' ' ' | sed 's/ $//')"
  fi
fi

if [[ "$COVERAGE" == 1 ]]; then
  echo "==> cargo llvm-cov $selector --lib --fail-under-lines 95"
  if ! cargo llvm-cov $selector --lib --fail-under-lines 95; then
    echo "⚠ unit-test gate failed: a unit test failed, or unit coverage < 95%" >&2
    echo "   fix: add unit tests for the uncovered lines above, then re-run" >&2
    exit 1
  fi
  echo "==> unit tests passed (coverage >= 95%)"
else
  echo "==> cargo test $selector --lib"
  cargo test $selector --lib
  echo "==> unit tests passed"
fi
