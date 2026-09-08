#!/usr/bin/env bash
# narness-repo-english.sh — reject CJK-language text in tracked UTF-8 repository files.
# usage: narness-repo-english.sh [REPOSITORY_DIR]
set -euo pipefail

ROOT="${1:-$(git rev-parse --show-toplevel)}"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "English-content gate cannot run: python3 is required." >&2
  echo "Fix: install Python 3, then rerun scripts/narness-repo-english.sh." >&2
  exit 1
fi

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
tracked = subprocess.check_output(
    ["git", "ls-files", "-z"],
    cwd=root,
).decode("utf-8").split("\0")

ranges = (
    (0x3040, 0x30FF),  # Hiragana and Katakana
    (0x3400, 0x4DBF),  # CJK Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xAC00, 0xD7AF),  # Hangul syllables
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
)

def contains_cjk(text: str) -> bool:
    return any(
        start <= ord(char) <= end
        for char in text
        for start, end in ranges
    )

failed = False
for relative in tracked:
    if not relative:
        continue

    path = root / relative
    if not path.is_file():
        continue

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue

    for line_number, line in enumerate(text.splitlines(), start=1):
        if contains_cjk(line):
            print(
                f"{relative}:{line_number}: non-English CJK text: {line}",
                file=sys.stderr,
            )
            failed = True

if failed:
    print(
        "Repository-authored content must be English. Translate the lines above.",
        file=sys.stderr,
    )
    raise SystemExit(1)

print("==> repository English-content gate passed")
PY
