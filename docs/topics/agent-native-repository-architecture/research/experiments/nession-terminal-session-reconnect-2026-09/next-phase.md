# Next Phase: Fresh R9 Pilots and R2 Formal Freeze

Benchmark Revision 3 fixes absolute checkout path scoring. Analysis Revision 2 and all 24 tasks, A/B/C treatment commits, fixtures, oracle and gold remain unchanged.

The R1 formal attempt [35731390660](https://github.com/BestNathan/narness-engineering/actions/runs/35731390660) stopped at T15/B because a primary read was scored as irrelevant. Preserve its original artifact and R1 metadata as audit evidence; do not reuse its runs in the new collection.

1. Merge the scorer and R9 registration PR after GitHub-hosted integrity CI passes.
2. Manually dispatch **AI Native Claude Code Pilots** on main: fresh T05/A, T08/B and T20/C.
3. Manually dispatch **AI Native Claude Pilot Promotion** with the new pilot run ID and artifact name.
4. Review and merge the generated `execution-profile-r2.json`, `formal-schedule-r2.json`, `formal-plan-r2.lock.json` and `PILOT-FREEZE-r2.json`.
5. Manually dispatch formal collection from sequence 1 through 216 with no previous artifact.

No model collection is triggered by a push, PR, or promotion. The current minimum remaining gate is fresh pilot evidence and the committed R2 freeze files. These files cannot be synthesized from the old R1 profile.

See [Runbook](RUNBOOK.md) and [R9 registration](EXECUTION-PREPILOT-R9.md).
