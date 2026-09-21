# Treatment Freeze — 2026-09-21

## Milestone

The three repository treatments for experiment revision 1 are now frozen.

```text
A  0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664
B  8fb6e8707f2dc967a900e227bb899b0c75336d2e
C  3e544761d5b89dc09a631533659dca4862f9e559
```

Treatment C passed the isolated Web validation gate after canonical implementations and primary tests were moved under `web/src/units/terminal-session/`.

## C structure

```text
terminal-session/
  transport-reconnect/
  visibility-wake/
  attach/
  route-recovery/
  runtime-projection/
```

Legacy production paths remain thin re-export projections so the experiment changes canonical ownership/locality without forcing unrelated consumers to migrate.

## Benchmark audit

The second half of the task pool was audited before formal runs.

Three candidate tasks were replaced because the frozen code already contained the requested evidence or because the task was too correlated with another task:

```text
T14 -> preserve transport identity across non-routing context churn
T19 -> typed failure classification instead of prose-string matching
T23 -> competing recovery signals converge to one relay transition
```

T23/T24 verification-task acceptance now uses hidden mutation testing: a new test must pass against clean code and fail against a known semantic mutation.

## Next gate

Treatments are frozen, but the benchmark is not fully frozen.

Remaining work before reportable A/B/C runs:

```text
validate/harden T07-T24 starting states and hidden oracles
materialize remaining controlled fixtures
finish executable run harness
run non-reportable instrumentation pilot
freeze benchmark revision 1
```

Only after that gate will formal fresh-session A/B/C data collection begin.
