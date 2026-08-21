#!/usr/bin/env bash
# narness-git-commit-msg.sh — Narness Git commit-message format check
# usage: narness-git-commit-msg.sh COMMIT_MSG_FILE
# single responsibility: does the commit message follow the project's format?
#   - conventional-commit type prefix:  <type>(<scope>): <subject>
#   - no WIP / fixup! / squash! markers
#   - subject (first line) ≤ 72 characters
# exit 0 = pass; non-zero = fail (blocks the commit)
set -uo pipefail

MSG_FILE="${1:-}"
if [[ -z "$MSG_FILE" || ! -f "$MSG_FILE" ]]; then
  echo "error: commit message file not found: ${MSG_FILE:-<none>}" >&2
  exit 1
fi

first="$(head -n 1 "$MSG_FILE")"

# empty message → reject
if [[ -z "$first" ]]; then
  echo "✗ commit message is empty" >&2
  echo "  fix: provide a '<type>(<scope>): <subject>' message" >&2
  exit 1
fi

# git auto-generated messages → exempt (merge, revert, cherry-pick)
if printf '%s\n' "$first" | grep -qE '^(Merge |Revert "|This reverts )'; then
  exit 0
fi

# WIP / autosquash markers → reject
if printf '%s\n' "$first" | grep -qiE '^(wip|fixup!|squash!)'; then
  echo "✗ commit message contains a WIP / fixup! / squash! marker" >&2
  echo "  first line: $first" >&2
  exit 1
fi

# conventional-commit type prefix → reject if absent
if ! printf '%s\n' "$first" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\([^)]*\))?!?: '; then
  echo "✗ commit message must start with a conventional type" >&2
  echo "  got:      $first" >&2
  echo "  expected: <type>(<scope>): <subject>" >&2
  echo "  types:    feat | fix | docs | style | refactor | test | chore | perf | ci | build | revert" >&2
  exit 1
fi

# subject (first line) ≤ 72 chars → reject if too long
if [[ "${#first}" -gt 72 ]]; then
  echo "✗ commit subject is ${#first} characters (max 72)" >&2
  echo "  $first" >&2
  exit 1
fi

echo "✓ commit message format ok"
