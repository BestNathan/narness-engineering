# Correctness of long-running tasks

## 1. What is a long-running task

A task that can't be completed in a single conversation and needs multiple round-trips or spans sessions: implementing a module from scratch, refactoring a whole subsystem, fixing a cross-file bug. Traits: context keeps growing, early constraints get diluted, errors accumulate.

## 2. Why long-running tasks drift most easily

- Early prompts get drowned by later context
- Small deviations at each step accumulate into a large directional error
- Without an external checkpoint, the agent struggles to notice "it's already wrong"

## 3. The harness's role at each stage

| Stage | Corresponding harness | Role |
|---|---|---|
| Task start | L1/L2 (CLAUDE.md + skill) | establish ground truth and acceptance criteria |
| During coding | L3 (hook) | validate every change immediately; deviations don't survive overnight |
| Staged commit | L4 (script) | full gate; keep accumulated errors from entering the next step |
| Integration / regression | L5 (compile-time) + CI | physical constraints + regression protection |

## 4. Core insight

Long-running correctness doesn't come from the agent "remembering the rules all along", but from this: every change passes through hard-constraint validation; an error is caught and fed back by a script/hook the moment it is produced; the agent is forced to fix it while it is still small. This is the mechanism of "letting the agent discover its own mistakes".
