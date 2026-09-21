# Execution Pre-Pilot Revision 3 — Superseded Before Real Pilots

> Status: superseded by Revision 4 before any real Codex instrumentation pilot.

## Identity

```text
branch:
research/ai-native-execution-prepilot-r3

commit:
1519adcb31bc66d5741e4cd0e67e54c79b19eef1

AI Native Benchmark Integrity:
35629539218 PASS

general CI:
35629539165 PASS
```

## Why Revision 3 exists

Revision 2 tightened authentication handling but still relied on the coding
agent's default workspace sandbox read semantics.

Before any real pilot, the execution path was hardened so hidden Narness research
state cannot be discovered by a Codex shell command outside the detached Nession
worktree.

The live Codex invocation now uses a dedicated permission profile:

```text
default_permissions = "narness-research"
extends = ":workspace"

filesystem:
  :root      deny
  :minimal   read
  :tmpdir    deny
  :slash_tmp deny

network:
  enabled = false
```

The coding-agent command environment is also allowlisted to a small runtime set:

```text
PATH
HOME
TMPDIR
TMP
TEMP
LANG
LC_*
SHELL
USER
```

The adapter no longer passes the legacy `--sandbox workspace-write` flag. This
avoids mixing legacy sandbox selection with the custom permission profile.

CI now statically proves the emitted Codex argv contains the expected permission
profile, root/temp denials, offline network policy, and shell-environment
allowlist.

## Hidden-evaluation boundary

The research harness and hidden evaluation material live outside the detached
Nession worktree.

The intended boundary is:

```text
Codex
  can read/write:
    detached Nession workspace

  can read:
    minimal runtime/tool paths required to execute commands

  cannot read:
    filesystem root by default
    general TMPDIR
    /tmp outside the workspace root
    Narness benchmark/gold/oracle files

  cannot use:
    network
    exported OpenAI/Codex bearer credentials
```

The worktree itself may physically live under a temporary directory. It remains
available as the active workspace root; general temporary roots are separately
denied.

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

No task, fixture, oracle, gold scope, scorer semantic, treatment, analysis
threshold, or analysis implementation changed for this execution revision.

## Pilot rule

Only these three non-reportable cells may define the formal execution profile:

```text
T05 / A
T08 / B
T20 / C
```

They must all identify:

```text
harness repository SHA:
1519adcb31bc66d5741e4cd0e67e54c79b19eef1

permission profile:
narness-research

filesystem scope:
workspace-only-plus-minimal-runtime; temp roots denied

network:
false
```

After all three pilots pass instrumentation validation, generate, review, and
commit:

```text
runner/execution-profile-r1.json
runner/formal-schedule-r1.json
runner/formal-plan-r1.lock.json
```

Any later execution-mechanics change requires a new pre-pilot revision and fresh
pilots before it can define a formal plan.


## Supersession

Revision 3 correctly isolated Codex filesystem/tool access, but the benchmark
runner still created a linked Git worktree. A linked worktree shares the source
Nession object database and refs, so a coding agent could potentially discover
research-only treatment/oracle commits through Git history/ref inspection.

Revision 4 removes that channel by creating a standalone Git repository per run
and fetching only the frozen treatment commit plus its reachable ancestry. No
real pilot was executed from Revision 3.
