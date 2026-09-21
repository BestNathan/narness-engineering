# Failure Review Protocol

> Status: pre-registered before reportable formal collection.

Failure taxonomy is diagnostic evidence. It must not become a post-hoc story written
after seeing which treatment won an aggregate comparison.

## Review order

For every failed admissible run:

```text
sealed run
   ↓
inspect per-run prompt / trace / diff / acceptance / verification
   ↓
assign one primary R1–R12 cause
   ↓
record rationale + evidence references
   ↓
write review.json anchored to seal.json
```

Complete failed-run reviews before using aggregate treatment results to explain
failure-mode differences.

Full treatment blinding is not possible because Treatment C paths and semantic
resolver use may be visible in the trace. The protocol therefore reduces bias by
constraining **what evidence is reviewed first**, rather than claiming perfect
blinding.

## Evidence order

Review in this order:

1. task prompt and final task outcome;
2. navigation trace before first edit;
3. final diff;
4. failed acceptance / verification / mutation evidence;
5. repair-loop trace;
6. treatment-specific metadata only when required to distinguish R11/R12.

Do not start from A/B/C aggregate success rates.

## Primary taxonomy

```text
R1  target not found
R2  wrong semantic owner selected
R3  important dependency/consumer missed
R4  contract misunderstood
R5  invariant missed
R6  implementation error
R7  verification gap
R8  feedback insufficient or misleading
R9  tool/runtime failure
R10 task ambiguity
R11 treatment metadata stale/incorrect
R12 architecture treatment introduced accidental complexity
```

Choose the earliest causal failure that best explains why evidence closure failed.

Examples:

```text
wrong file selected → broken implementation
primary: R2
secondary: R6

correct implementation, required consumer never discovered
primary: R3

metadata points to stale owner and agent follows it
primary: R11
secondary: R2

localized Treatment C structure introduces a new ambiguous compatibility layer
primary: R12
```

## Required review record

A failed run review must contain:

```text
primary failure code
optional secondary codes
non-empty causal rationale
at least one evidence reference
SHA-256 of the reviewed seal.json
review timestamp
review policy version
```

Example:

```bash
python3 scripts/review-ai-native-run.py \
  --run-dir /path/to/formal-runs/T07-B-02 \
  --primary R3 \
  --secondary R6 \
  --notes 'The agent changed the reconnect owner but never inspected the route-recovery consumer; hidden acceptance failed on stale route state.' \
  --evidence 'trace.jsonl: navigation before first edit' \
  --evidence 'acceptance: route-switch reconnect case'
```

The review is content-bound to the run seal. If the run artifacts change, failure
aggregation rejects the stale review.

## Aggregate interpretation

Failure counts are diagnostic, not a substitute for the pre-registered H1–H5
primary metrics.

A shift such as:

```text
R1/R2 ↓
R6 unchanged
```

may support the interpretation that retrieval improved while implementation
remained the bottleneck, but it does not independently promote a hypothesis to
Supported.

Negative treatment-specific findings such as R11 or R12 must be reported rather
than collapsed into generic implementation failure.
