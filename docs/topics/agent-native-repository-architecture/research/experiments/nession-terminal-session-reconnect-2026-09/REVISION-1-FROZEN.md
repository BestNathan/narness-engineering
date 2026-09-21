# Benchmark Revision 1 — Superseded Before Formal Collection

The original benchmark definition was frozen, then superseded before any reportable formal run.

```text
experiment:       nession-terminal-session-reconnect-2026-09
revision:         1
definition SHA:   5ba7fe074fc230fa2ff2e20a69c61d7442dc21de
definition branch: research/ai-native-benchmark-r1

Treatment A: 0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664
Treatment B: 8fb6e8707f2dc967a900e227bb899b0c75336d2e
Treatment C: 3e544761d5b89dc09a631533659dca4862f9e559

Hidden oracle: 70d8074e7c50f3865771fabd714e811ae440e09d
Integrity run: 35556728129 — PASS
Tasks: T01–T24
```

The integrity gate verified all 24 task manifests, treatment commit identities,
hidden-oracle sources, fixture applicability, treatment-specific mutation
applicability, and the Python runner/scorer/validator syntax.

## Freeze boundary

The following are benchmark semantics and may not change during revision 1 formal collection:

- task prompts;
- treatment SHAs;
- controlled task fixtures;
- hidden acceptance semantics;
- T23/T24 semantic mutations;
- hidden navigation gold;
- relevance classes;
- success/admissibility rules;
- metric definitions.

Changing any of the above creates **benchmark revision 2**.

## What may still change before formal collection

Only instrumentation mechanics may be repaired during the three non-reportable
pilot runs, provided the repair does not change benchmark semantics. The exact
runner/harness adapter commit must be recorded for every run.

Formal collection begins only after three representative instrumentation pilots
produce complete, scoreable traces.

## Current state

```text
benchmark semantics       FROZEN
treatments                FROZEN
hidden oracle             FROZEN
integrity                 PASS
instrumentation pilots    PENDING
formal A/B/C collection   NOT STARTED
```

## Supersession

Revision 1 remains as an audit artifact.

After the freeze, the scorer gained implementations for metrics that had already been declared by the research protocol/analysis design, including pre-edit acquisition and missed-artifact counts. The task prompts, treatments, fixtures, hidden oracle, and gold semantic scope did not change.

Because Revision 1 explicitly treated scoring semantics as part of the freeze boundary, the study creates Benchmark Revision 2 rather than silently accepting that drift.

No reportable formal run was observed under Benchmark Revision 1.
