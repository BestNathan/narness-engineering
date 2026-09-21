# Formal Run Harness Contract

Formal A/B/C runs must be executed in fresh isolated agent sessions.

## Common system constraints

Every run receives the same task statement and the same generic coding instruction:

```text
Work on the requested task in the provided repository state.
Find the owning behavior yourself.
Make the smallest correct change.
Use repository feedback to validate it.
Do not inspect experiment gold data or other treatment branches.
```

The runner records every tool call and, when available, token/cost telemetry.

## Treatment-specific capability exposure

### A — baseline

No semantic resolver is announced.

Allowed discovery is the normal repository/harness surface:

```text
filesystem / repository browsing
grep / search
glob
language tooling already present
tests / compiler / lint
```

### B — semantic index

Add exactly one instruction:

```text
A deterministic repository semantic resolver is available:
node .ai-native/resolve.mjs <task text | capability id>
```

No expected capability ID or owner path is given.

### C — agent-native structure

Expose the same resolver instruction as B. No additional task-specific hint is allowed.

Any performance difference between B and C should therefore come from physical/semantic code organization and feedback locality, not from a richer task prompt.

## Session isolation

A formal run is inadmissible if the agent/session has previously:

- inspected the task's source slice;
- seen the fixture mutation;
- seen the hidden acceptance oracle;
- seen the gold owner mapping;
- solved the same task under another treatment.

For repeated runs, each repetition uses a new session.

## Starting state

The runner applies the treatment-specific task fixture before the agent session begins.

Record:

```yaml
task_id:
treatment:
treatment_base_sha:
fixture_sha:
effective_start_sha:
model:
model_version:
reasoning_setting:
harness_version:
```

## Completion

The coding agent stops when it believes the task is complete.

The runner then executes hidden acceptance plus required repository checks. Hidden acceptance is not included in the task prompt.

## Trace measurements

At minimum classify:

```text
search / grep calls
glob calls
semantic resolver calls
artifacts read
first relevant artifact
first edit
patch attempts
validation attempts
failed validations
repair loops
final evidence
```

Artifact relevance is scored afterward against the hidden gold set.

## No cross-treatment learning

Do not run A → B → C for the same task inside one conversation or persistent agent memory.

The experiment compares environments, not whether an agent can remember the previous solution.
