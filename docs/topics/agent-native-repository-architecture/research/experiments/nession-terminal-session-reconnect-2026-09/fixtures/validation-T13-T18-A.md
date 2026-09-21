# Regression Fixture Validation — T13–T18 / Treatment A

All six regression-oriented benchmark instances were validated against Treatment A.

| Task | Run | Primary observed failure | Existing suite also caught mutation? | Result |
|---|---:|---|---|---|
| T13 | 35555602966 | exhausted stopped transport wake produced 0 explicit connect attempts, expected 1 | no | ACCEPTED |
| T14 | 35555609736 | non-routing context churn created 3 physical sockets, expected 1 | yes; mutation also broke snapshot identity and caused update-loop symptoms | ACCEPTED, broad fixture |
| T15 | 35555617125 | same-URL route-intent change created 0 replacement sockets, expected 1 | yes | ACCEPTED |
| T16 | 35555624610 | viewport stayed at 80x24 during reconnect, expected 120x40 | no | ACCEPTED |
| T17 | 35555632158 | manual exhaustion remained `connecting`, expected `failed` | yes | ACCEPTED |
| T18 | 35555639437 | repeated recovery outcomes emitted two `force-relay` events, expected one | no | ACCEPTED |

## Feedback-surface observation

This batch separates tasks into two useful classes.

Visible-test-covered regressions:

```text
T14
T15
T17
```

Hidden-oracle-only regressions:

```text
T13
T16
T18
```

That split is useful experimental data. For some tasks the repository already provides strong diagnostic feedback once the agent reaches the right area. For others, the agent can produce a semantically wrong change while every existing visible test remains green.

## T14 note

T14 is intentionally retained even though removing same-endpoint reuse has broad consequences. The fixture is semantically narrow — one transport-identity guard is removed — but that guard prevents multiple downstream failures, including unnecessary transport rebuild, snapshot identity churn, and React update loops.

The breadth of observed failures is therefore treated as a property of the invariant's importance, not as multiple unrelated mutations.

## Decision

```text
T13–T18 A fixtures: ACCEPTED
```

The semantic defects are now stable enough to project into Treatment B directly and Treatment C through its localized owners.
