# Treatment C Construction Record

> Status: Frozen construction complete; final isolated validation passed.
>
> Nession branch: `research/ai-native-repo-c-agent-native`
>
> Checkpoint SHA: `3e544761d5b89dc09a631533659dca4862f9e559`

## Transformation

Treatment C preserves the same semantic capabilities as B but changes canonical physical ownership.

Canonical slice:

```text
web/src/units/terminal-session/
  transport-reconnect/
    service.ts
    types.ts
    __tests__/service.test.ts

  visibility-wake/
    useVisibilityReconnect.ts

  attach/
    state.ts
    controller.ts
    __tests__/state.test.ts
    __tests__/controller.test.ts

  route-recovery/
    runtime.ts
    __tests__/runtime.test.ts

  runtime-projection/
    useTerminalAttach.ts
    useTerminalOrchestration.ts
    __tests__/useTerminalAttach.test.ts
```

Legacy production paths remain as thin compatibility projections where existing imports depend on them. They are explicitly not semantic owners.

## Semantic continuity

The six capability IDs are unchanged from Treatment B. `.ai-native/capabilities.json` now resolves each capability to the localized owner/evidence path.

## Construction diff at C2

GitHub comparison against the frozen source reports:

```text
commits:       35
changed files: 25
additions:     2453
deletions:     2050
```

These raw line counts substantially overstate semantic change because the main implementation bodies are relocated rather than rewritten.

GitHub recognizes the five primary test files as renames with only import-path edits.

The large deletion/addition pairs for production files represent:

```text
old canonical implementation
    ↓
thin compatibility projection

same implementation body
    ↓
behavior-oriented canonical unit
```

## New non-relocation surface

Treatment C also contains the B semantic layer plus C documentation:

```text
.ai-native/README.md
.ai-native/capabilities.json
.ai-native/resolve.mjs
web/src/units/terminal-session/README.md
```

## Behavioral intent

No production behavior is intentionally changed by the C structural conversion.

The first C validation checkpoint before evidence relocation passed the full isolated Web gate. The final C2 checkpoint passed before the treatment SHA was frozen; see `C-validation.md`.

## Cost accounting note

The final study should report both:

1. raw repository churn, because migration cost is real;
2. semantic-change classification, because rename/move churn is not equivalent to new behavior.

This prevents Treatment C from appearing either artificially cheap or artificially expensive. The completed quantitative decomposition is recorded in `construction-cost.md` and `construction-cost-r1.json`.
