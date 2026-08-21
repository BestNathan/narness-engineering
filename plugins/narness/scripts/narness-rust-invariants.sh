#!/usr/bin/env bash
# narness-rust-invariants.sh — Narness Rust invariant check
# usage: narness-rust-invariants.sh [PROJECT_DIR]
# scans .rs files under src/ for:
#   - bare unwrap() / expect() (forbidden in production code)
#   - panic! / unreachable! / todo! / unimplemented!
#   - unsafe lacking a SAFETY comment
# zero extra dependencies (POSIX find + grep only), macOS compatible.
set -uo pipefail

PROJECT_DIR="${1:-.}"
SRC_DIR="$PROJECT_DIR/src"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "error: src directory not found: $SRC_DIR" >&2
  exit 1
fi

fail=0
echo "==> Narness invariant check: $SRC_DIR"

# 1. bare unwrap() / expect()
matches="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -nH -E '\.(unwrap|expect)\(' {} + 2>/dev/null || true)"
if [[ -n "$matches" ]]; then
  printf '%s\n' "$matches" >&2
  echo "✗ found unwrap()/expect(); replace with anyhow/thiserror or explicit error handling" >&2
  fail=1
else
  echo "✓ no bare unwrap()/expect()"
fi

# 2. panic! / unreachable! / todo! / unimplemented!
matches="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -nH -E '\b(panic|unreachable|todo|unimplemented)!' {} + 2>/dev/null || true)"
if [[ -n "$matches" ]]; then
  printf '%s\n' "$matches" >&2
  echo "✗ found panic!/unreachable!/todo!/unimplemented!; propagate errors with Result instead" >&2
  fail=1
else
  echo "✓ no panic!/unreachable!/todo!/unimplemented!"
fi

# 3. unsafe blocks lacking a SAFETY comment
unsafe_files="$(find "$SRC_DIR" -name '*.rs' -type f -exec grep -lE '\bunsafe\b' {} + 2>/dev/null || true)"
if [[ -n "$unsafe_files" ]]; then
  while IFS= read -r f; do
    if ! grep -q 'SAFETY' "$f"; then
      echo "✗ $f contains unsafe but no SAFETY comment" >&2
      fail=1
    fi
  done <<< "$unsafe_files"
else
  echo "✓ no unsafe code"
fi

if [[ $fail -ne 0 ]]; then
  echo "==> invariant check failed" >&2
  exit 1
fi
echo "==> invariant check passed"
