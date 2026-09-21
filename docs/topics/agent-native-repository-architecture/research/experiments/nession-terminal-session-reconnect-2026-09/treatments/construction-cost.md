# Treatment Construction Cost — Pre-Registered Context

> Status: recorded before reportable formal collection.

The study must not treat Treatment C as free. This record separates raw Git churn
from semantic migration cost before any A/B/C outcome is visible.

## Frozen inputs

```text
A  0dc28d5e768f3a0421cb17ebc2a88f0e6a84d664
B  8fb6e8707f2dc967a900e227bb899b0c75336d2e
C  3e544761d5b89dc09a631533659dca4862f9e559
```

## A → B

The semantic-index treatment adds only:

```text
.ai-native/README.md          +40
.ai-native/capabilities.json +225
.ai-native/resolve.mjs        +83
```

Total:

```text
commits       3
changed files 3
additions     348
deletions     0
net lines     +348
```

This is the up-front repository cost of the deterministic semantic index/resolver
before maintenance cost is considered.

## A → C

Raw GitHub comparison:

```text
commits       35
changed files 25
additions     2453
deletions     2050
raw churn     4503
net lines     +403
```

Raw churn substantially overstates new implementation because C is primarily a
canonical-owner relocation.

The line-level decomposition is unusually clean:

```text
implementation relocation
  old owners deleted        2042
  localized owners added    2042

primary test rename/import churn
  deleted                      8
  added                        8

semantic index
  added                      366

unit documentation
  added                       15

legacy compatibility glue
  added                       22
```

Therefore:

```text
2453 additions
= 2042 relocated implementation
+    8 renamed-test edits
+  366 semantic index
+   15 unit docs
+   22 compatibility projections

2050 deletions
= 2042 relocated implementation
+    8 renamed-test edits
```

The exact net increase is:

```text
+403 lines
= +366 semantic index
+  15 unit documentation
+  22 compatibility projection glue
```

So C's **4503 lines of raw churn are real migration activity**, but almost all
production/test body churn is relocation rather than new behavior.

## Structural surface excluding the semantic index

If the three `.ai-native/` files are excluded:

```text
changed files 22
additions     2087
deletions     2050
raw churn     4137
net lines     +37
```

The +37 net lines are exactly the unit README (+15) and thin compatibility
projections (+22).

## Interpretation rule

The final research report must show both:

1. raw migration churn, because moving code has engineering cost;
2. classified churn, because relocated implementation must not be misrepresented
   as 4092 lines of newly authored behavior.

Commit count is not treated as engineering time. No wall-clock construction time
was measured reliably enough to infer labor cost.

The machine-readable source for this section is
`treatments/construction-cost-r1.json`.
