#!/usr/bin/env bash
# narness-repo-english.sh — verify that tracked repository text contains no Han characters.
# usage: narness-repo-english.sh [REPOSITORY_DIR]
set -euo pipefail

ROOT="${1:-$(git rev-parse --show-toplevel)}"
cd "$ROOT"

if ! command -v rg >/dev/null 2>&1; then
  echo "English-content gate cannot run: ripgrep (rg) is required." >&2
  echo "Fix: install ripgrep, then rerun scripts/narness-repo-english.sh." >&2
  exit 1
fi

failed=0
while IFS= read -r -d '' file; do
  [[ -f "$file" ]] || continue
  matches="$(rg -n --no-heading --color=never '\p{Han}' -- "$file" 2>/dev/null || true)"
  if [[ -n "$matches" ]]; then
    echo "Non-English repository content detected in $file:" >&2
    printf '%s\n' "$matches" >&2
    failed=1
  fi
done < <(git ls-files -z)

if [[ "$failed" -ne 0 ]]; then
  echo "Repository-authored content must be English. Translate the lines above." >&2
  exit 1
fi

echo "==> repository English-content gate passed"
