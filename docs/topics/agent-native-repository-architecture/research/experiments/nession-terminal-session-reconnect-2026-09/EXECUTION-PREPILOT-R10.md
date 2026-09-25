# Execution Pre-Pilot Revision 10

Registered execution commit: `1b436827649b360fae231c9362d51b7f9051ac11`.
Branch: `research/ai-native-execution-prepilot-r10`.
Benchmark: Revision 3 (`bb56a330c90755d9c149bff64aaeb3a841d8015c`).
Analysis: Revision 2 (`357c38c9b10a3eb668b15aead703a5f5200b2858`).

R10 supersedes R9 after run 35810458835 exposed insufficient host filesystem
isolation and cross-task memory access. R9 and R2 freeze metadata remain historical
audit records. The R10 runtime uses bubblewrap mount/PID/user/network namespaces,
private HOME/Claude config/tmp, and a per-run Unix model gateway that permits only
the configured HTTPS provider and model. Real provider credentials never enter
the agent sandbox. The AppArmor exception is scoped to /usr/bin/bwrap.

The execution commit contains the R3 generation scripts. This separate
registration commit pins it without a self-referential hash. Pilot tools,
runtime policy and subsequent formal tooling must match this frozen execution.

## Manual hosted sequence

Use GitHub-hosted Ubuntu 24.04 and environment `ds`. Existing
ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL and CLAUDE_MODEL configuration applies.
Node 22.14.0, Python 3.13.2 and Claude Code 2.1.278 remain pinned.
Both pilot and formal jobs install bubblewrap/socat, load the scoped AppArmor
policy and run the no-model isolation smoke test before any provider request.

1. Merge registration after hosted checks pass.
2. Dispatch **AI Native Claude Code Pilots** on main. It checks out the exact
   registered SHA and runs fresh T05/A, T08/B and T20/C.
3. Dispatch **AI Native Claude Pilot Promotion** with that run ID and artifact
   `ai-native-claude-r10-<run-id>-<attempt>`. Review and merge the four generated
   R3 freeze files: execution-profile-r3.json, formal-schedule-r3.json,
   formal-plan-r3.lock.json and PILOT-FREEZE-r3.json.
4. Dispatch **AI Native Claude Formal Collection** with sequences 1–24 and empty
   previous-artifact inputs. The frozen schedule still contains 216 runs; the
   smaller default batch avoids the six-hour hosted job limit.
5. Continue contiguous registered ranges, restoring the immediately previous R3
   artifact so evidence accumulates. Use recovery only for an incomplete run
   directory. Never restore R1/R2 artifacts. Finalization requires all 216 seals.

Task success is not a prerequisite for pilot promotion; instrumentation,
isolation and provenance are. Synthetic isolation tests do not count as pilots.
No push or PR event starts model collection. The new profile and formal plan do
not exist until real pilots produce them; do not create placeholder freeze files.
