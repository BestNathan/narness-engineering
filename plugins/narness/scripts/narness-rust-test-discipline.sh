#!/usr/bin/env bash
# narness-rust-test-discipline.sh — Narness Rust test discipline check
# usage: narness-rust-test-discipline.sh [PROJECT_DIR]
# checks that non-test .rs source files changed since git HEAD have a corresponding test file.
set -uo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

# changed non-test .rs source files (tracked changes + untracked new files; exclude tests/, *_test.rs, etc.)
changed="$( { git diff --name-only HEAD -- '*.rs'; git ls-files --others --exclude-standard -- '*.rs'; } 2>/dev/null | sort -u | grep -vE '(^|/)(tests?|benches|examples)/|(_test|\.test)\.rs$' || true)"

if [[ -z "$changed" ]]; then
  echo "✓ no changed non-test .rs source files"
  exit 0
fi

fail=0
while IFS= read -r f; do
  # src/foo/bar.rs → tests/foo/bar.rs or tests/foo/bar_test.rs or src/foo/bar_test.rs
  stem="${f%.rs}"
  stem="${stem#src/}"
  candidates=(
    "tests/${stem}.rs"
    "tests/${stem}_test.rs"
    "src/${stem}_test.rs"
  )
  found=0
  for c in "${candidates[@]}"; do
    if [[ -f "$c" ]]; then found=1; break; fi
  done
  if [[ $found -eq 0 ]]; then
    echo "✗ $f changed but has no corresponding test file" >&2
    fail=1
  else
    echo "✓ $f has test coverage"
  fi
done <<< "$changed"

if [[ $fail -ne 0 ]]; then
  echo "==> test discipline check failed: add tests for the files above" >&2
  exit 1
fi
echo "==> test discipline check passed"
