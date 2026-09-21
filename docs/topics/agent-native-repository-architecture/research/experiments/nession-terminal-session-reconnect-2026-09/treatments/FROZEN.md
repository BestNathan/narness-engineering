# Frozen Treatment SHAs — Experiment Revision 1

> Formal comparative runs must use these exact treatment commits.

```text
A baseline
0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664

B semantic index
8fb6e8707f2dc967a900e227bb899b0c75336d2e

C agent-native structure
3e544761d5b89dc09a631533659dca4862f9e559
```

## Isolation

The research CI/oracle branch is not a treatment:

```text
research/ai-native-ci-base
```

It supplies hidden experiment acceptance and validation only.

## Freeze rule

From this point forward, formal A/B/C results are comparable only when the corresponding treatment starts from the SHA above.

If A, B, or C is changed for any reason after reportable runs begin, the new state belongs to **experiment revision 2** and must not be mixed into revision-1 aggregates.

## Treatment meaning

```text
A: original repository organization

B: A + deterministic semantic capability index/resolver
   production source topology materially unchanged

C: same semantic capability layer as B
   + behavior-oriented canonical ownership
   + localized primary evidence
   + legacy paths reduced to compatibility projections
```

This freeze prevents later benchmark-specific tuning of B or C after observing formal A failures.
