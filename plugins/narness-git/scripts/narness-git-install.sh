#!/usr/bin/env bash
# narness-git-install.sh — install narness-git hooks into a repo
# usage: narness-git-install.sh [TARGET_REPO_DIR]
# responsibility: copy the plugin's thin git hooks into the repo's .githooks/
#   and point core.hooksPath at it — one idempotent install step.
# the hooks themselves delegate to narness-rust scripts (see githooks/).
set -euo pipefail

TARGET="${1:-.}"
SOURCE_GITHOOKS="${NARNESS_GIT_GITHOOKS:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/githooks}"

if [[ ! -d "$TARGET/.git" ]]; then
  echo "error: not a git repository: $TARGET" >&2
  exit 1
fi

mkdir -p "$TARGET/.githooks"
for h in pre-commit commit-msg pre-push; do
  cp "$SOURCE_GITHOOKS/$h" "$TARGET/.githooks/$h"
  chmod +x "$TARGET/.githooks/$h"
done

git -C "$TARGET" config core.hooksPath .githooks

echo "✓ installed narness-git hooks into $TARGET/.githooks"
echo "  core.hooksPath = .githooks"
echo "  confirm with: git -C $TARGET config --local core.hooksPath"
