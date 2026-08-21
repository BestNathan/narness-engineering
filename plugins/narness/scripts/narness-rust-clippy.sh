#!/usr/bin/env bash
# narness-rust-clippy.sh — do only a lint check (cargo clippy -D warnings)
# usage: narness-rust-clippy.sh [PROJECT_DIR] [--scope=changed|full]
#   --scope=changed  lint only the crates changed since the last push (fast pre-commit gate)
#   --scope=full     lint the whole workspace (default; CI / long-running)
set -euo pipefail

SCOPE="full"
PROJECT_DIR="."
for arg in "$@"; do
  case "$arg" in
    --scope=changed) SCOPE="changed" ;;
    --scope=full) SCOPE="full" ;;
    *) PROJECT_DIR="$arg" ;;
  esac
done
cd "$PROJECT_DIR"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

selector="--workspace"
if [[ "$SCOPE" == "changed" ]]; then
  pkgs="$(bash "$DIR/narness-rust-changed-packages.sh" .)"
  if [[ -z "$pkgs" ]]; then
    echo "✓ no changed crates — lint skipped"
    exit 0
  fi
  if [[ "$pkgs" != "WORKSPACE" ]]; then
    selector="$(printf '%s\n' "$pkgs" | sed 's/^/-p /' | tr '\n' ' ' | sed 's/ $//')"
  fi
fi

echo "==> cargo clippy $selector --all-targets --all-features -- -D warnings"
cargo clippy $selector --all-targets --all-features -- -D warnings
echo "==> lint check passed"
