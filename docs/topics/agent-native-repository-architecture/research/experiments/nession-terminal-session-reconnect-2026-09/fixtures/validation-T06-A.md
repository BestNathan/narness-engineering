# Fixture Validation — T06 / Treatment A

```yaml
task_id: T06
treatment: A-baseline
fixture_branch: research/ai-native-a-fixture-t06
fixture_sha: 4303ecf1a5d080841eb2735a60338419d450490b
validation_pr: BestNathan/nession#888
workflow_run: 35548550112
result: valid
expected_ci_result: failure
actual_ci_result: failure
```

## Controlled mutation

The fixture removes the stale-socket guards from the asynchronous handshake-success continuation. A superseded or disposed physical socket can therefore promote the shared transport state after it is no longer current.

## Validation result

The existing WebSocket unit suite caught the defect without a new hidden oracle:

```text
WebSocketService
  ignores a late handshake completion from a superseded socket
  expected: connecting
  received: connected

WebSocketService
  dispose() rejects an in-flight connect() whose handshake is still pending
  expected: disconnected
  received: connected
```

Suite summary:

```text
1 test file failed
191 test files passed

2 tests failed
1655 tests passed
```

## Decision

```text
T06 A-fixture: ACCEPTED
```

The same semantic defect for Treatment C is: stale completion from an obsolete transport identity is allowed to mutate the current transport state.
