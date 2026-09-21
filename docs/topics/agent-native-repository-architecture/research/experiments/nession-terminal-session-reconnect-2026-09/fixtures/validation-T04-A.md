# Fixture Validation — T04 / Treatment A

```yaml
task_id: T04
treatment: A-baseline
fixture_branch: research/ai-native-a-fixture-t04
fixture_sha: 4fe7deb9852eeb71aeb5ad8fc660bf2e74317625
validation_pr: BestNathan/nession#887
workflow_run: 35548588870
result: valid
expected_ci_result: failure
actual_ci_result: failure
```

## Controlled mutation

The fixture removes the attached-phase eligibility guard from recoverable connection-state notifications, allowing one physical transport-loss cycle to redispatch recovery when the reconnect timer transitions back through `connecting`.

## Hidden acceptance result

The normal visible suite did not detect this injected defect. The research CI installed a task-specific hidden oracle.

The oracle observed:

```text
research acceptance T04
  one transport loss cycle emits one recovery transition

expected route-intent-changed events: 1
received: 2
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
T04 A-fixture: ACCEPTED
```

This task specifically measures whether an agent notices the phase/idempotence boundary rather than merely reacting to repeated connection-state callbacks.
