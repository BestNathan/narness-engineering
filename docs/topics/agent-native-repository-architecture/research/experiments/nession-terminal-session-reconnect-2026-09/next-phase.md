# Next Phase — Freeze Benchmark and Treatments

> Status: Benchmark revision 2 and analysis revision 2 frozen; instrumentation plumbing and preflight green; three real Codex pilots pending.

Benchmark revision 2 and all three treatments are now frozen. Formal A/B/C data collection is still blocked on the three non-reportable instrumentation pilots.

## Exit criteria

Freeze criteria through the executable benchmark are complete. Formal runs may begin when the final pilot criterion is satisfied:

```text
T01–T24 task intents hardened                         DONE
T01–T24 starting-state/fixture semantics frozen            DONE
T01–T24 hidden acceptance oracles frozen                   DONE
Treatment A SHA frozen                                      DONE
Treatment B SHA frozen                                      DONE
Treatment C SHA frozen                                      DONE
C transformation cost recorded                              DONE
formal runner contract frozen                               DONE
benchmark integrity gate                                    PASS
pilot instrumentation validated on 3 non-reportable runs    PENDING
```

## Work order

### 1. Harden T07–T24

For each task, prove one of:

```text
bug      -> controlled defect exists after fixture
feature  -> requested capability is absent before run
refactor -> structural predicate is unsatisfied before run
evidence -> requested proof/test is absent before run
```

Each task receives a hidden acceptance oracle and a gold semantic scope.

### 2. Finish Treatment C

Refactor the selected reconnect slice around stable semantic capabilities while preserving behavior.

Record the one-time construction cost separately:

```text
files moved/created/deleted
lines changed
import-only churn
CI failures during construction
semantic-index maintenance
wall-clock / agent effort if available
```

### 3. Freeze treatment SHAs

Once C passes the research validation gate:

```text
A = frozen baseline
B = semantic-index treatment
C = agent-native structural treatment
```

No treatment may be changed after formal comparative runs begin. Any later treatment change creates experiment revision 2.

### 4. Implement executable run harness

The harness must:

```text
create clean worktree
apply task fixture
start/attach a fresh agent process supplied by the operator
capture tool/model trace where available
run hidden acceptance
run treatment-required verification
classify result
write machine-readable run record
reset/destroy worktree
```

The harness must not expose hidden acceptance or gold data to the coding agent.

### 5. Instrumentation pilot

Before collecting reportable data, run three representative tasks:

```text
one local bug
one cross-capability behavior change
one refactor/verification task
```

These runs validate measurement plumbing only and are not included in final results.

### 6. Formal collection

Minimum study:

```text
24 tasks × 3 treatments = 72 runs
```

Preferred study if compute budget allows:

```text
24 tasks × 3 treatments × 3 independent repetitions = 216 runs
```

## Why treatment freeze comes before formal runs

If B/C are modified after observing where A fails, the experiment stops measuring repository architecture and starts measuring benchmark-specific optimization.

The next phase therefore optimizes for experimental validity, not fast headline numbers.


## Current instrumentation gate

The active benchmark semantics are frozen at the revision-2 definition SHA. Post-freeze work has only hardened measurement mechanics.

Latest validated instrumentation state:

```text
structured Codex adapter replay                 PASS
search-result path normalization                PASS
runner/scorer selftest                          PASS
benchmark semantic-drift gate                   PASS
local pilot preflight (Codex skipped in CI)     PASS
AI Native Benchmark Integrity                    awaiting Revision-2 integrity record
general repository CI                           awaiting Revision-2 integrity record
```

The remaining transition is external execution, not benchmark design:

```text
authenticated local Codex CLI
        ↓
T05 / A pilot
T08 / B pilot
T20 / C pilot
        ↓
freeze execution-profile-r1.json
        ↓
generate + commit formal-schedule-r1.json
        ↓
formal collection may begin
```

The one-command entry point is:

```bash
./scripts/run-ai-native-codex-pilots.sh /path/to/nession
```

The command now preflights both repositories before spending model budget and,
after all three pilots pass, emits the frozen execution profile plus the
pre-registered 216-run schedule.

## Analysis and reporting readiness

Before seeing any formal outcome, the analysis plan has also been frozen.

```text
analysis definition SHA     357c38c9b10a3eb668b15aead703a5f5200b2858
analysis branch             research/ai-native-analysis-r2
paired task analysis        READY
task-cluster bootstrap      READY
failure taxonomy pipeline   READY
research report generator   READY
structured H1-H5 review     READY
```

`RUNBOOK.md` now defines the complete operational path from the three external Codex pilots through 216 formal runs, failure review, paired analysis, and final research report generation.
