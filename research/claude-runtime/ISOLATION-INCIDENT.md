# R9 filesystem isolation incident

Formal collection 35810458835 stopped at sequence 47 (T09/A/01). The seal
reported access to runner/gold.json. The trace also contains paths to a previous
task's Claude memory and other run records. Forty-six runs passed the existing
seal, but that does not establish absence of cross-run contamination. Preserve
artifact 10734986125 as diagnostic evidence; do not resume it into a new cohort.

## Filesystem repair

The Claude adapter now launches the entire client and its tools in bubblewrap.
The view contains only the current standalone treatment checkout at /workspace,
read-only system runtime files and the exact setup-node runtime directory.
Host home, controller checkout, hidden oracle, other run outputs and host temp
directories are not mounted. HOME, Claude configuration/cache and /tmp are
empty private tmpfs directories for every invocation. PID isolation prevents
using host processes' /proc roots to recover host paths. Nested user namespaces
are disabled, capabilities are dropped and inherited file descriptors are closed.
Missing or unusable bubblewrap fails closed; there is no direct-host fallback.
Provider credentials remain in the parent gateway, never in the agent environment or command arguments. The agent receives a placeholder credential.

The hosted isolation workflow uses the same launcher to test forbidden reads,
symlink traversal, runtime writes, task writes, environment filtering, repeated
invocation state isolation, and the pinned Claude binary. It makes no model calls.
Ubuntu 24.04 requires an AppArmor user-namespace exception for /usr/bin/bwrap.
The hosted workflow loads the reviewed bwrap.apparmor profile for that executable
only. It does not disable AppArmor or global user-namespace restrictions. Nested
user namespaces remain disabled inside the sandbox. Future pilot/collection
setup must install bubblewrap/socat and load this same profile.

## Registration remains suspended

Existing R9/R2 files are retained unchanged for audit. Pilot, promotion and formal
workflows stop before model calls or promotion until a reviewed successor is
registered. The new adapter hash and runtime identity cannot match the old freeze.
Do not relabel these results or silently edit frozen hashes.

The network namespace has no external route. A per-invocation Unix socket exposes
only POST /v1/messages and /v1/messages/count_tokens (including beta=true) to a
parent-side gateway. A loopback bridge lets the Claude client use its normal HTTP
API. The gateway fixes the configured HTTPS provider origin, base path and model,
replaces authentication headers, rejects other routes and never follows redirects.
No host TCP listener or provider credential is exposed to the coding agent.
Streaming is relayed without buffering the full response. This permits inference,
not arbitrary web access or package downloads; install dependencies before launch.

Before registering a new execution profile, require hosted isolation tests and
fresh T05/A, T08/B and T20/C pilots to pass. Freeze a new execution profile and
formal plan, then collect a fresh cohort. The old benchmark/analysis and R9/R2
registration bytes remain unchanged in this repair PR; the successor registration
must bind the reviewed repair commit. Automatic synthetic checks alone do not
constitute real pilot evidence or authorize formal collection.

## Hosted verification

Isolation run 35833804315 passed on Ubuntu 24.04, including Claude Code 2.1.278
startup and the fixed-provider gateway tests. No provider requests or real
credentials were used. Benchmark Integrity and repository CI also passed.
