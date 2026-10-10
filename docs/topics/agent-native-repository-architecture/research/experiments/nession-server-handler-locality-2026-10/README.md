# Nession Server Handler Semantic Locality — pre-pilot (#1258)

**Status:** structural pre-pilot measured; AI coding-productivity experiment **not yet executed**.  
**Recorded:** 2026-10-10  
**Nession baseline:** `staging@6b7dcff69275b1e69ad6f8484240a41436db4cc5`  
**Treatment snapshot:** `feat/1258-server-handler-locality@3f91a570147905d49a5090fccd2e460729b3ff18` (unmerged [PR #1615](https://github.com/BestNathan/nession/pull/1615); Quality Gate [#38049143896](https://github.com/BestNathan/nession/actions/runs/38049143896) PASS).  
**Source requirement:** [Nession #1258](https://github.com/BestNathan/nession/issues/1258).

This is an append-only preparation note, not evidence that coding agents have become faster or more accurate. At this stage only repository file structure and a constrained deterministic navigation property have been measured. Acceptance depends on source verification and controlled trials.

## Verified source-shape measurements

| Metric | Baseline | Treatment snapshot |
|---|---:|---:|
| Server `handler.rs` | 8,182 lines, 328,385 bytes | removed |
| Versioned Server route entries | 30, one declaration | 30, same canonical declaration |
| Versioned leaf handler files | 0 | 29 (plus explicit relay.end runtime-owned exception) |
| Combined versioned leaf bytes | n/a | 114,313 |
| Median leaf implementation bytes | n/a | 2,787 |
| Largest versioned leaf | n/a | 14,202 bytes (`server_session_attach_v1.rs`) |
| Connection-state/shared `handler/mod.rs` | n/a | 45,345 bytes |
| Canonical `handler/routes.rs` | embedded in monolith | 8,770 bytes |
| Localized test files | none in monolith | 24, totalling 77,509 bytes |
| Tests moved from centralized module | n/a | 78 of 127 tests |
| Remaining shared/cross-unit test file | embedded in monolith | 61,016 bytes |

Measurements are repository file bytes from GitHub's file metadata and explicit source/test counts, not tokenizer accounting. The unversioned `control` and generic `relay` paths intentionally remain runtime mechanisms; `server.session.relay.end@v1` is advertised as an operation but its active transition is owned by the WebSocket relay reader, not a fake versioned leaf file.

For an implementation-only lookup, the baseline source address is a common 328,385-byte file. The treatment's direct address for `server.session.attach@v1` is a 14,202-byte file and its predictable sibling test file is 11,794 bytes. For `server.env.write@v1`, they are 6,028 and 6,936 bytes. This demonstrates **smaller directly addressable source segments**, not lower actual inference cost: a correct change may still require shared state, routing, contracts, tests and runtime evidence.

## Verified SC-12 concurrency pre-pilot

The exact treatment checkout passed `node scripts/server-handler-concurrency-selftest.mjs` inside the Quality Gate Rust job on 2026-10-10. The script copies the source of two distinct versioned handlers into an isolated git fixture, forks two Git worktrees from the same baseline commit and makes independently committed no-behavior-change edits.

| Recorded measure | Result |
|---|---|
| Agent rename worktree changed paths | `server_agent_rename_v1.rs` only |
| Env write worktree changed paths | `server_env_write_v1.rs` only |
| Changed-path intersection | 0 |
| `git merge --no-ff` | succeeded; verified two parents |
| Resulting merged handler files | both original files with their respective isolated edits |
| Evidence | [Quality Gate run 38049143896](https://github.com/BestNathan/nession/actions/runs/38049143896) and [Requirement #1258 evidence comment](https://github.com/BestNathan/nession/issues/1258#issuecomment-6097138643) |

This demonstrates source-location isolation and one clean merge, **not** a representative merge-conflict-rate estimate, agent productivity gain, or model-context saving. The baseline monolith did not undergo this exact runnable treatment (its two operations shared a physical file by construction). No model runs are reported here.

## Hypotheses to test, not assume

H1. Given the exact Unit/Version identity, first-location precision and time/tool calls to locate code + tests improve.  
H2. Editing two independent Units lowers touched-file overlap and merge interference; do not infer observed conflict rate from disjoint paths.  
H3. Reduced unrelated context does not reduce behavior correctness or increase repair loops.  
H4. The extra module boundary and routing indirection do not increase total cognitive/context cost for multi-unit or runtime-mechanism changes.

## Frozen candidate tasks

- T1: locate implementation and proofs for `server.session.attach@v1`, without modifying the repo.
- T2: apply an identical small behavior-preserving edit to `server.env.write@v1`, run required validation.
- T3: independently edit `server.agent.rename@v1` and `server.session.capture-preview@v1` in separate worktrees, observe diff overlap and actual merges.
- T4: diagnose a deliberately failing route/handler structural Gate mutation.
- T5: inspect `server.session.relay.end@v1` during active relay versus idle dispatch, to expose risks that naive file matching misses.

Run each against **frozen** baseline and treatment SHAs with the same task wording, harness, tools, model identifiers, budgets and verification contract; randomize task/treatment order where appropriate. Collect the model/provider version, agent/harness version, wall-clock time, all retrieval/edit/test tool calls, context bytes and actual token usage where supported, relevant/unrelated read bytes, first-location correctness, changed files, final proof outcome and repair-loop count.

## Pre-pilot limits and admission criteria

- Treatment PR has not yet satisfied all compilation/Gate/E2E/Acceptance criteria. **Do not use this snapshot as a validated successful treatment** until tests are green and source SHA is frozen.
- The baseline and treatment differ in source organization and potentially in unrelated branch history unless runs are deliberately normalized. Record exact trees and verify the baseline/treatment behavioral delta.
- Static byte ratios must not be reported as measured token savings or coding speedup.
- All mutations in T2–T4 must be isolated, disposable and reverted. The data-collection harness may use Nession's #1474 source-aligned Scenarios/Run Records when available, without making research observations a blocking repository Gate.
- Conclusions require real trials with reproducible records, failure review and quantified uncertainty; **the #1258 Narness Success Criterion remains Pending until then**.

## Next evidence needed

1. Pin the final accepted Nession treatment commit SHA after CI and protocol/relay behavior gates pass.
2. Freeze task fixtures and expected outcomes (including negative control for relay.end).
3. Execute same-harness baseline/treatment runs; store source and evaluation evidence separately.
4. Publish run logs, raw measures and a conclusion identifying which hypotheses were supported, refuted or not identifiable.
