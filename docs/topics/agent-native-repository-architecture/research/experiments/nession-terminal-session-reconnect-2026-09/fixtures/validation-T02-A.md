# Fixture Validation — T02 / Treatment A

```yaml
task_id: T02
treatment: A-baseline
fixture_branch: research/ai-native-a-fixture-t02
fixture_sha: f8e923dbe43d13deb2ff4852d5bd7cc1c63b50bf
validation_pr: BestNathan/nession#882
workflow_run: 35524837163
result: valid
expected_ci_result: failure
actual_ci_result: failure
```

## Controlled mutation

The fixture intentionally allows a stale successful attach result from a superseded attach generation to bypass the normal epoch guard, while stale failures remain suppressed.

## Expected defect

A superseded attach can resolve successfully and incorrectly dispatch `ATTACH_OK` into current state.

## Validation result

The full Web test suite failed in exactly the stale-resolution area:

```text
SessionAttachController
  ignores a late attach resolution after cancel (epoch guard)
  expected outcomes length 0, received 1

SessionAttachController
  ignores a superseded attach resolution — only the latest generation counts
  expected outcomes length 0, received 1
```

Suite summary:

```text
1 test file failed
191 test files passed

2 tests failed
1655 tests passed
```

This is a good fixture shape: it breaks the intended invariant while leaving the rest of the suite overwhelmingly intact.

## Decision

```text
T02 A-fixture: ACCEPTED
```

For Treatment B, use the equivalent mutation because implementation topology is intentionally unchanged.

For Treatment C, reproduce the same stale-success defect at the semantic attach-attempt boundary rather than copying a file-specific patch.
