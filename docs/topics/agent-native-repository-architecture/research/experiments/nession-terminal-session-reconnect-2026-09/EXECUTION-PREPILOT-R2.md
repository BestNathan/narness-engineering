# Execution Pre-Pilot Revision 2

> Status: frozen before any real Codex instrumentation pilot.

The first execution pre-pilot handoff was frozen at:

```text
research/ai-native-execution-prepilot-r1
b6a71b25efac50bb11c8363cc908c1b7f42ab236
```

It was superseded before any real pilot or reportable formal run.

## Why Revision 2 exists

After Revision 1 was frozen, the execution path was hardened in ways that do not
change benchmark or analysis semantics but do change the trusted execution
mechanics:

```text
Codex preflight now requires:
  codex login status == success

pilot execution now rejects exported:
  OPENAI_API_KEY
  CODEX_ACCESS_TOKEN

GitHub self-hosted pilot workflow:
  requires trusted self-hosted runner
  requires ai-native-research label
  uses persist-credentials: false
  captures non-reportable pilot handoff artifacts

RUNBOOK / next-phase:
  document local and trusted self-hosted execution paths
```

Because the execution profile is derived from the pilot runs, these changes must
be present before the three pilots are executed. Reusing Revision 1 would freeze
an execution profile from obsolete preflight/security mechanics.

## Revision 2 identity

```text
branch:
research/ai-native-execution-prepilot-r2

commit:
6072a096e2ea8899930056d876c4b4679421c9b3

AI Native Benchmark Integrity:
35628400123 PASS

general CI:
35628400116 PASS
```

## Frozen semantic inputs are unchanged

```text
Benchmark Revision 2
194bf5dc1a28f4e4c10491d7326891ba157d325b

Analysis Revision 2
357c38c9b10a3eb668b15aead703a5f5200b2858

Treatment A
0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664

Treatment B
8fb6e8707f2dc967a900e227bb899b0c75336d2e

Treatment C
3e544761d5b89dc09a631533659dca4862f9e559

Hidden oracle
70d8074e7c50f3865771fabd714e811ae440e09d
```

No task, fixture, oracle, gold scope, scorer semantic, analysis threshold, or
treatment changed between execution pre-pilot revisions.

## Pilot rule

The three non-reportable pilots must run from this exact revision:

```text
T05 / A
T08 / B
T20 / C
```

After they pass, freeze and commit:

```text
runner/execution-profile-r1.json
runner/formal-schedule-r1.json
runner/formal-plan-r1.lock.json
```

No later Narness execution change may be mixed into the same formal plan without
rerunning the pilot freeze.
