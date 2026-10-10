# #1258 — paired source-locality experiment (measured)

**Classification:** completed deterministic Git-source retrieval experiment; **not** an LLM/AI coding-agent productivity experiment.  
**Execution:** 2026-10-10, [Narness workflow #38051474658](https://github.com/BestNathan/narness-engineering/actions/runs/38051474658), measure job **Success**.  
**Raw measurements:** [download workflow artifact](https://github.com/BestNathan/narness-engineering/actions/runs/38051474658), `nession-1258-source-locality-observations` (artifact ID `11670050229`).  
**Raw `observations.json` SHA-256:** `5cc36bb2ced14062c17df985ad996bc0c8a9014f30680c831ceb76021e1195ed`.  
**Reproduction:** `python scripts/measure-nession-handler-locality.py --source-repo /path/to/nession --output-dir /tmp/nession-1258-observations`. The script verifies both immutable commits, reads real Git blobs with `git show`, checks canonical handler/route identities, and emits per-blob source paths and SHA-256 fingerprints.

## Frozen treatments

- **A, original monolith:** Nession `6b7dcff69275b1e69ad6f8484240a41436db4cc5`.
- **C, split handlers:** Nession staging `696892d0cb003a507dde5f9b7087014db8f92e18`, after [PR #1615](https://github.com/BestNathan/nession/pull/1615) and the staging [SC-03 Protocol Case #38051081406](https://github.com/BestNathan/nession/actions/runs/38051081406).

There were five frozen lookup tasks: four versioned operations with fixed canonical identities and method-name oracles, and `server.session.relay.end` as a runtime-owner negative control. Both treatments received the same task identity/oracle, and both resolved all five code owners. No attempt was made to measure natural-language autonomous search.

## Observations

Values are actual `git show` byte counts. The conservative closure includes the versioned implementation, canonical route declaration, located test module and connection-state module; duplicate paths are counted once per task.

| Probe | A: implementation bytes | C: implementation bytes | A: closure bytes | C: closure bytes | C tests local? |
|---|---:|---:|---:|---:|---|
| T01 `server.session.attach` | 328,385 | 14,384 | 328,385 | 80,350 | Yes |
| T02 `server.env.write` | 328,385 | 6,200 | 328,385 | 67,308 | Yes |
| T03 `server.agent.rename` | 328,385 | 3,616 | 328,385 | 118,728 | No; tests shared |
| T04 `server.session.capture-preview` | 328,385 | 5,216 | 328,385 | 120,328 | No; tests shared |
| T05 `server.session.relay.end` | 433,428 | 113,870 | 433,428 | 113,870 | N/A — active relay owned by WebSocket runtime |

Across T01–T04 (four independent task observations, **not** four independent repo files in baseline):

- Implementation retrieval bytes: **1,313,540 → 29,416**, or approximately **97.76% fewer selected bytes**.
- Conservative source+route+test+connection closure: **1,313,540 → 386,714**, or approximately **70.56% fewer selected bytes**.
- Versioned Unit owner lookup correctness with known identity/method: **4/4 → 4/4**.
- Localized treatment tests for these tasks: **2/4**.
- T05 negative control: the live relay-end operation still requires understanding `websocket.rs`; a leaf-only path resolver would be incorrect, so this must remain a separate runtime mechanism in any proposed semantic index.

## Interpretation and limitations

**Supported, bounded observation:** splitting the Server handler makes *these four known operations* separately addressable as smaller Git source artifacts, and a conservative file-closure proxy is smaller. A real two-worktree independent merge for two Units was separately established in Nession [Quality Gate #38049143896](https://github.com/BestNathan/nession/actions/runs/38049143896) and [SC-12 evidence](https://github.com/BestNathan/nession/issues/1258#issuecomment-6097138643).

**Not established:** better natural-language retrieval, AI first-hit correctness, token savings, wall-clock speed, fewer model/tool calls, fewer repair loops, reduced merge-conflict probability, improved behavior correctness, or productivity. **No LLM inference or coding-agent task was run in this experiment.** All method oracles were provided in advance. Source-byte counting is a retrieval-surface proxy, not an inference-cost metric. The conservative closure is not guaranteed to contain every true runtime dependency, and the changes in the treatment tree are not a perfect counterfactual independent of unrelated branch history.

## Research conclusion

H1 / locality: **supported only for directly addressable, known Unit identities measured in this file-retrieval setting**.  
H2 / concurrent edits: **a single independent Git merge demonstrated**, but no generalized conflict-rate or team throughput evidence.  
H3 / model efficiency and H4 / change correctness: **not tested**.  
H5 / runtime-owned edge cases: **important counterexample; splitting versioned handlers does not eliminate shared relay logic**.

Keep the architecture experiment **conditional**. To claim AI-native productivity gains, run matched AI-agent tasks at frozen baselines under one model/harness/environment with token and tool-call telemetry, repair loops and independent acceptance. See the surrounding [research methodology](../../ai-native-codebase-and-productivity-experiment.md) and the pre-pilot [README](README.md).

This measured study fulfills the *recording of before/after source-locality observations* but **does not prove AI engineering productivity improvements**.
