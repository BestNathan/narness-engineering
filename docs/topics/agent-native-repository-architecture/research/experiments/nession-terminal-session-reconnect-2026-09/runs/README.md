# Experiment Runs

No coding-task runs have been recorded yet.

Each run gets a file:

```text
<task-id>-<treatment>-<attempt>.md
```

Example:

```text
T02-A-01.md
T02-B-01.md
T02-C-01.md
```

## Required run template

```yaml
run_id:
task_id:
treatment:
nession_start_sha:
treatment_start_sha:
model:
model_version:
reasoning_setting:
harness_version:
started_at:
ended_at:

metrics:
  time_to_first_relevant_artifact_ms:
  first_hit_correct:
  search_calls:
  glob_calls:
  resolver_calls:
  files_read:
  unique_files_read:
  primary_or_relevant_files_read:
  irrelevant_files_read:
  important_artifacts_missed:
  input_tokens:
  output_tokens:
  reasoning_tokens:
  time_to_first_edit_ms:
  patch_count:
  reverted_patch_count:
  out_of_scope_edits:
  compiler_failures:
  test_failures:
  repair_loops:
  task_success:
  evidence_complete:
  wall_time_ms:
  model_cost:
```

Then append:

```text
## Trace summary
## Retrieval classification
## Change summary
## Validation evidence
## Failure classification
## Notes
```

Raw traces should be retained separately when the execution harness can provide them.
