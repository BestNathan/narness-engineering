# Fixture Validation — T05 / Treatment A

```yaml
task_id: T05
treatment: A-baseline
fixture_branch: research/ai-native-a-fixture-t05
fixture_sha: 039906a1fce6f5f87825f54c5c5ca4a45d95abbc
validation_pr: BestNathan/nession#883
workflow_run: 35524866623
result: valid
expected_ci_result: failure
actual_ci_result: failure
```

## Controlled mutation

The fixture intentionally routes a live explicit handshake refusal through normal socket-loss reconnect handling instead of definitive connection failure.

## Expected defect

A refused handshake incorrectly:

```text
enters reconnecting
increments/spends reconnect recovery
schedules another physical connection attempt
```

instead of settling in `disconnected`.

## Validation result

The full Web suite failed in exactly the refusal semantics:

```text
WebSocketService
  rejects the connection when the handshake is refused;
  in-flight work fails and no reconnect is scheduled

  -> timed out because the fixture scheduled recovery

useAppConnection
  manual connect with a failing handshake toasts and drops to disconnected

  expected: disconnected
  received: reconnecting
```

Suite summary:

```text
2 test files failed
190 test files passed

2 tests failed
1655 tests passed
```

This is a narrow and useful fixture: the intended reconnect/refusal contract fails while almost the entire suite remains green.

## Decision

```text
T05 A-fixture: ACCEPTED
```

Treatment B can use the equivalent mutation.

Treatment C must reproduce the semantic defect "explicit refusal is misclassified as recoverable transport loss" at its reconnect boundary.
