#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 /path/to/nession [output-dir]" >&2
  exit 64
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_REPO="$(cd "$1" && pwd)"
OUTPUT_DIR="${2:-$ROOT/research-runs/pilots}"
EXP="$ROOT/docs/topics/agent-native-repository-architecture/research/experiments/nession-terminal-session-reconnect-2026-09"
PROFILE_OUT="$EXP/runner/execution-profile-r1.json"
SCHEDULE_OUT="$EXP/runner/formal-schedule-r1.json"

mkdir -p "$OUTPUT_DIR"

python3 "$ROOT/scripts/preflight-ai-native-codex-pilots.py" \
  --source-repo "$SOURCE_REPO" \
  --output-dir "$OUTPUT_DIR"

run_pilot() {
  local task="$1"
  local treatment="$2"
  local run_id="${task}-${treatment}-01"

  echo "==> pilot ${task}/${treatment}"

  set +e
  python3 "$ROOT/scripts/ai-native-repo-experiment.py" \
    --source-repo "$SOURCE_REPO" \
    --task "$EXP/runner/manifests/${task}.json" \
    --treatments "$EXP/runner/treatments.json" \
    --treatment "$treatment" \
    --attempt 1 \
    --setup-cmd 'cd web && npm ci' \
    --agent-cmd "python3 '$ROOT/scripts/ai-native-codex-adapter.py' --model gpt-5.6-sol --effort high" \
    --output-dir "$OUTPUT_DIR"
  local runner_rc=$?
  set -e

  # 0 = task success, 2 = task semantic failure. Both can still validate pilot
  # instrumentation. 3 means the harness itself failed.
  if [[ "$runner_rc" -eq 3 ]]; then
    echo "pilot runner infrastructure failed: $run_id" >&2
    exit 3
  fi

  python3 "$ROOT/scripts/score-ai-native-run.py" \
    --run-dir "$OUTPUT_DIR/$run_id" \
    --gold "$EXP/runner/gold.json" \
    --treatment "$treatment" \
    --update-run-json \
    > "$OUTPUT_DIR/$run_id/score.stdout.json"

  python3 "$ROOT/scripts/validate-ai-native-pilot.py" \
    --run-dir "$OUTPUT_DIR/$run_id"
}

run_pilot T05 A
run_pilot T08 B
run_pilot T20 C

python3 "$ROOT/scripts/freeze-ai-native-execution-profile.py" \
  --pilot "$OUTPUT_DIR/T05-A-01" \
  --pilot "$OUTPUT_DIR/T08-B-01" \
  --pilot "$OUTPUT_DIR/T20-C-01" \
  --output "$PROFILE_OUT" \
  --profile-id codex-gpt-5.6-sol-high-r1

python3 "$ROOT/scripts/generate-ai-native-formal-schedule.py" \
  --replications 3 \
  --profile-id codex-gpt-5.6-sol-high-r1 \
  --output "$SCHEDULE_OUT"

echo
echo "All three instrumentation pilots passed."
echo "Execution profile written to: $PROFILE_OUT"
echo "Pre-registered 216-run schedule written to: $SCHEDULE_OUT"
echo
echo "NEXT: review and commit those two generated files before starting formal runs."
