# Execution Pre-Pilot Revision 9

Registered execution commit: `1633e9433b897903077f8c4813dc8d5a9821f9fb`.
Branch: `research/ai-native-execution-prepilot-r9`.
Benchmark: Revision 3 (`bb56a330c90755d9c149bff64aaeb3a841d8015c`).
Analysis: Revision 2.

R9 supersedes R8 after formal run 35731390660 exposed absolute-path scoring corruption. The runner records the isolated checkout root and the scorer maps only paths within that root to repository-relative paths. The root is persisted because scoring happens after checkout cleanup.

The controller's EXECUTION-PREPILOT-LOCK.json pins the preceding execution commit. The pinned runtime already contains Benchmark Revision 3 and the R2 generation scripts; registration is a separate commit to avoid a self-referential hash.

## Manual hosted sequence

Use GitHub-hosted Ubuntu 24.04 and environment `ds`, with its configured ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL and explicit CLAUDE_MODEL. Node 22.14.0, Python 3.13.2 and Claude Code 2.1.278 remain pinned.

1. Merge registration after hosted CI succeeds.
2. Dispatch AI Native Claude Code Pilots on main. It checks out the exact registered execution commit and runs fresh T05/A, T08/B and T20/C.
3. Dispatch AI Native Claude Pilot Promotion with the new artifact. It validates provenance and opens a draft PR adding execution-profile-r2.json, formal-schedule-r2.json, formal-plan-r2.lock.json and PILOT-FREEZE-r2.json.
4. Review and merge those files.
5. Dispatch formal collection separately at sequence 1 through 216, without a previous R1 artifact.

Pilot task success is not required; valid instrumentation and provenance are required. R1 metadata and partial run evidence remain historical records. Push and PR events never launch model collection.
