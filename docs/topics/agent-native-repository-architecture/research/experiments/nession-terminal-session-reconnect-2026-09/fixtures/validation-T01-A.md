# Fixture Validation — T01 / Treatment A

```yaml
task_id: T01
treatment: A-baseline
fixture_branch: research/ai-native-a-fixture-t01
fixture_sha: d2adf9a74fe3d68b1376bbd7fe370307c7fc5fbd
validation_pr: BestNathan/nession#891
workflow_run: 35548739103
result: valid
expected_ci_result: failure
actual_ci_result: failure
```

## Starting condition

T01 requires no source mutation: the frozen baseline already attempts `connect()` when a previously authenticated, disconnected service is disposed and the document becomes visible.

The validation branch only adds a non-code marker so the research CI can select the hidden oracle.

## Hidden acceptance result

```text
research acceptance T01
  visibility wake never reconnects a disposed transport

expected connect() calls: 0
received: 1
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
T01 A-fixture: ACCEPTED
```

T01 is therefore a valid formal bug benchmark instance on the frozen A baseline.
