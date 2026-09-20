# T01-A-PILOT-01

```yaml
run_id: T01-A-PILOT-01
task_id: T01
treatment: A-baseline
pilot: true
admissible_for_final_analysis: false

nession_frozen_sha: 0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664
solution_branch: research/ai-native-a-t01
solution_head_sha: c55ff5cbcd58884eceb80d2f8fa7ef2b59f2ae56
research_pr: BestNathan/nession#881

model: GPT-5.6 Sol
reasoning_setting: high
harness: ChatGPT GitHub connector

metrics:
  first_hit_correct: contaminated_by_setup
  search_calls: not_admissible
  glob_calls: not_admissible
  resolver_calls: 0
  files_read: not_admissible
  input_tokens: unavailable
  output_tokens: unavailable
  reasoning_tokens: unavailable
  patch_count: 1
  test_addition_count: 1
  repair_loops: 0
  task_success: true
  evidence_complete: true

ci:
  workflow: AI Native Research Validation
  run_id: 35524635219
  started_at: 2026-09-20T17:03:18Z
  completed_at: 2026-09-20T17:05:32Z
  wall_time_seconds: 134
  conclusion: success
```

## Trace summary

The pilot located the visibility wake hook, inspected nearby hook-test conventions, added a disposed-service guard, and added focused coverage.

The experiment researcher had already inspected both the visibility hook and WebSocket transport during experiment design. Navigation measurements are therefore contaminated and intentionally excluded.

## Change summary

Behavioral change:

```text
visible + authenticated-before + disconnected + disposed
```

now exits before calling `connect()`.

Existing live-disconnected wake behavior remains unchanged.

## Validation evidence

The isolated research PR targets `research/ai-native-ci-base`, not `staging`.

The research workflow passed:

```text
npm ci       PASS
npm test     PASS
npm run build PASS
npm run lint PASS
```

## Failure classification

None for implementation/evidence.

Experiment-design issue discovered:

```text
benchmark task validity / prior-knowledge contamination
```

This led to the task-fixture protocol amendment documented in Pilot 0.

## Notes

This run validates the mechanics of:

```text
research-only solution branch
→ research-only PR base
→ isolated GitHub Actions validation
→ Narness run record
```

It does not validate the A/B/C architecture hypothesis.
