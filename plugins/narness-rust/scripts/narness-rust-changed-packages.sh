#!/usr/bin/env bash
# narness-rust-changed-packages.sh — emit the workspace packages changed since the last push
# usage: narness-rust-changed-packages.sh [PROJECT_DIR]
# output (on stdout, one line per entry):
#   (empty)            → no compile-relevant changes; the caller should skip
#   WORKSPACE          → a workspace-wide change, or the base couldn't be resolved; run full
#   <package>          → a changed member package; pass each as `-p <package>`
# exit code is always 0 — the verdict is communicated on stdout, never via exit status,
# so a caller can capture it under `set -e` without aborting.
set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1. resolve the "not yet pushed" base: merge-base of HEAD and the tracked upstream.
upstream="${NARNESS_RUST_BASE_REF:-}"
if [[ -z "$upstream" ]]; then
  upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
fi
base=""
if [[ -n "$upstream" ]]; then
  base="$(git merge-base HEAD "$upstream" 2>/dev/null || true)"
fi
if [[ -z "$base" ]]; then
  echo "WORKSPACE"
  exit 0
fi

# 2. everything not yet pushed (committed-ahead + staged + unstaged) + untracked.
changed="$(
  {
    git diff --name-only "$base" 2>/dev/null || true
    git ls-files --others --exclude-standard 2>/dev/null || true
  } | sort -u
)"

# 3. keep only compile-relevant paths; ignore docs / .github / etc.
relevant="$(printf '%s\n' "$changed" | grep -E '(\.rs$|Cargo\.toml$|Cargo\.lock$|rust-toolchain(\.toml)?$|/\.cargo/|^\.cargo/)' || true)"
if [[ -z "$relevant" ]]; then
  exit 0
fi

# 4. map each relevant file to its owning member package (deepest manifest dir wins).
metadata="$(cargo metadata --no-deps --format-version 1 2>/dev/null || true)"
if [[ -z "$metadata" ]]; then
  echo "WORKSPACE"
  exit 0
fi
meta_file="$(mktemp)"
trap 'rm -f "$meta_file"' EXIT
printf '%s' "$metadata" > "$meta_file"

RELEVANT="$relevant" REPO_ROOT="$root" META_FILE="$meta_file" python3 2>/dev/null <<'PY' || { echo "WORKSPACE"; exit 0; }
import json, os

relevant = [l for l in os.environ.get("RELEVANT", "").splitlines() if l.strip()]
repo_root = os.environ["REPO_ROOT"]
meta = json.load(open(os.environ["META_FILE"]))
workspace_root = os.path.normpath(meta.get("workspace_root", repo_root))

pkgs = []
for p in meta.get("packages", []):
    mp = p.get("manifest_path", "")
    if mp:
        pkgs.append((p.get("name"), os.path.normpath(os.path.dirname(mp))))
pkgs.sort(key=lambda nd: -len(nd[1]))  # deepest manifest dir first

def abspath(rel):
    return os.path.normpath(os.path.join(repo_root, rel))

full = False
names = []
for f in relevant:
    a = abspath(f)
    base_name = os.path.basename(a)
    if base_name in ("Cargo.lock", "rust-toolchain", "rust-toolchain.toml"):
        full = True
        break
    if "/.cargo/" in (a + "/"):
        full = True
        break
    if base_name == "Cargo.toml" and os.path.dirname(a) == workspace_root:
        full = True
        break
    owner = None
    for name, d in pkgs:
        if a == d or a.startswith(d + os.sep):
            owner = name
            break
    if owner is None:
        full = True
        break
    names.append(owner)

if full:
    print("WORKSPACE")
else:
    for n in sorted(set(names)):
        print(n)
PY
