#!/usr/bin/env bash
# narness-rust-test-e2e.sh — e2e-test gate (tier 3): full-system scenarios, gap-filling (补位)
# runs e2e tests (feature-gated behind `e2e`); no coverage threshold — e2e is scenario-driven, not line-driven.
# usage: narness-rust-test-e2e.sh [PROJECT_DIR]
# trigger: CI (slowest, separate stage) — e2e needs real/containerized dependencies and env setup.
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "==> cargo test --features e2e"
if ! cargo test --features e2e; then
  echo "⚠ e2e-test gate failed: an end-to-end scenario did not pass" >&2
  echo "   fix: inspect the failing scenario above; e2e covers what unit/integration cannot reach" >&2
  exit 1
fi
echo "==> e2e tests passed"
