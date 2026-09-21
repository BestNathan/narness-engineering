# Execution Pre-Pilot Revision 4

> Status: active and frozen before any real Codex instrumentation pilot.

## Identity

```text
branch:
research/ai-native-execution-prepilot-r4

commit:
d01117beb44e57c24cb6b73ae8c4c9f89100e825

AI Native Benchmark Integrity:
35630413932 PASS

general CI:
35630413911 PASS
```

## Why Revision 4 exists

Revision 3 restricted Codex filesystem reads to the active workspace, but the
runner still created that workspace with `git worktree add`.

A linked worktree shares:

```text
source repository refs
source repository object database
research-only descendant/sibling commits
```

with the coding-agent checkout.

That is an experimental contamination channel even when hidden Narness files are
filesystem-inaccessible. An agent could use Git introspection to discover
research branches, alternate treatments, or the hidden-oracle commit if those
objects are present in the shared repository.

Revision 4 replaces linked worktrees with a standalone repository per run:

```text
temporary empty git repository
        ↓
fetch exact frozen treatment SHA
        ↓
retain only that commit + reachable ancestry
        ↓
detach HEAD
        ↓
delete FETCH_HEAD
        ↓
no configured remote
no object alternates
no source path in .git/config
```

This preserves ordinary historical context reachable **before** the treatment
commit while excluding research-only descendants and sibling branches.

## Real-subject proof

CI validates the strategy against the actual frozen Nession repository, not only
a synthetic fixture.

For Treatment A/B/C, it proves:

```text
isolated history == exact source ancestry of treatment SHA

hidden oracle object:
  absent

non-ancestor treatment objects:
  absent

refs:
  none

remote:
  none

object alternates:
  none

source checkout path in config:
  absent

FETCH_HEAD:
  removed
```

The same invariant is separately tested with a synthetic repository containing a
known hidden descendant.

## Codex isolation inherited from Revision 3

Revision 4 keeps the Revision-3 agent sandbox contract:

```text
permission profile:
  narness-research

filesystem:
  :root      deny
  :minimal   read
  :tmpdir    deny
  :slash_tmp deny

network:
  false

shell-command environment:
  explicit allowlist only

exported OPENAI_API_KEY / CODEX_ACCESS_TOKEN:
  rejected by preflight
```

The two isolation layers are complementary:

```text
OS/tool permission boundary
        +
Git object/ref boundary
```

The first prevents arbitrary filesystem discovery. The second ensures the
workspace itself does not contain hidden research history.

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

No task, fixture, oracle, gold scope, scorer semantic, treatment, hypothesis,
threshold, or analysis implementation changed.

## Required pilot profile

The three non-reportable pilots:

```text
T05 / A
T08 / B
T20 / C
```

must all freeze:

```text
harness repository SHA:
d01117beb44e57c24cb6b73ae8c4c9f89100e825

checkout isolation:
single-ref-standalone-git-no-remote

permission profile:
narness-research

filesystem scope:
workspace-only-plus-minimal-runtime; temp roots denied

network:
false
```

Only then may the generated execution profile, 216-run schedule, and formal-plan
lock be promoted and committed.
