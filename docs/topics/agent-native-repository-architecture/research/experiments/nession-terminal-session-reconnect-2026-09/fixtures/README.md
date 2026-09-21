# Fixture Validation Index

The first six bug-oriented benchmark instances are now validated against Treatment A.

| Task | Defect | Oracle | Result |
|---|---|---|---|
| T01 | disposed visibility wake reconnects | hidden acceptance | ACCEPTED |
| T02 | superseded attach success mutates current state | existing tests | ACCEPTED |
| T03 | cancelled attach failure drives recovery | hidden acceptance | ACCEPTED |
| T04 | one loss cycle emits duplicate recovery transition | hidden acceptance | ACCEPTED |
| T05 | handshake refusal consumes reconnect recovery | existing tests | ACCEPTED |
| T06 | stale socket callback mutates live state | existing tests | ACCEPTED |

Validation detail:

- [T01](validation-T01-A.md)
- [T02](validation-T02-A.md)
- [T03](validation-T03-A.md)
- [T04](validation-T04-A.md)
- [T05](validation-T05-A.md)
- [T06](validation-T06-A.md)

## Observation

Three of the six defects were not guaranteed to be observable through the existing visible verification surface.

This is already an empirical property of the selected codebase:

```text
implementation invariant
!= always represented in existing visible tests
```

The research runner therefore keeps hidden task-specific acceptance separate from the agent's normal feedback environment.

That distinction matters for the final analysis:

- **visible feedback quality** is part of the treatment environment and can affect repair loops;
- **hidden acceptance** is only the experiment oracle and determines whether the final behavior is correct.


## Feature-absence validation

| Task range | Treatment A result | Detail |
|---|---|---|
| T07–T12 | ACCEPTED | [Feature absence validation](validation-T07-T12-A.md) |
