# Fixture Validation — T03 / Treatment A

```yaml
task_id: T03
treatment: A-baseline
fixture_branch: research/ai-native-a-fixture-t03
fixture_sha: 128af918d4cb0e99726bf12c8d5d864ccd7b741e
validation_pr: BestNathan/nession#886
workflow_run: 35548587353
result: valid
expected_ci_result: failure
actual_ci_result: failure
```

## Controlled mutation

The fixture preserves stale-success suppression but intentionally lets a stale timeout/failure after cancellation drive attach recovery.

## Hidden acceptance result

The normal suite did not detect this injected defect, so the research CI installed a task-specific hidden oracle.

That oracle failed exactly as intended:

```text
research acceptance T03
  late attach failure after cancellation is a no-op

expected outcomes length: 0
received outcomes length: 1
received phase: reconnecting
```

Suite summary:

```text
1 hidden test failed
192 test files passed

1 test failed
1657 tests passed
```

## Decision

```text
T03 A-fixture: ACCEPTED
```

This validation also records an important benchmark fact: the existing visible test suite did not cover stale failure after cancellation, so hidden acceptance evidence is necessary for this task.
