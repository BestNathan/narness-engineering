# R9 filesystem isolation incident

Formal collection 35810458835 stopped at sequence 47 (T09/A/01). The seal
reported access to runner/gold.json. The trace also contains paths to a previous
task's Claude memory and other run records. Forty-six runs passed the existing
seal, but that does not establish absence of cross-run contamination. Preserve
artifact 10734986125 as diagnostic evidence; do not resume it into a new cohort.

## Filesystem repair

The Claude client now runs in an outer bubblewrap mount/PID/network namespace.
The view contains only the current standalone treatment checkout at /workspace,
read-only system runtime files and the exact setup-node runtime directory.
Host home, controller checkout, hidden oracle, other run outputs and host temp
directories are not mounted. HOME, Claude configuration/cache and /tmp are
empty private tmpfs directories for every invocation. PID isolation prevents
using host processes' /proc roots to recover host paths. Capabilities are dropped,
inherited file descriptors are closed, the standalone checkout's .git directory
is read-only, and setup-produced node_modules trees are over-mounted read-only.
Missing or unusable isolation dependencies fail closed; there is no direct-host
fallback.

Claude Code's Bash tool is additionally forced through Anthropic Sandbox Runtime
with failIfUnavailable enabled, unsandboxed commands disabled, strict network
allowlisting with an empty allowlist, no Unix sockets, and provider environment
variables denied. Nested user namespaces remain available only inside the already
isolated outer namespace so this second Bash sandbox can be created; they cannot
recover host mounts, host PIDs, or host networking that the outer namespace never
exposed.

Provider credentials remain in the parent gateway, never in the agent environment
or command arguments. The Claude client receives only a placeholder credential.
The gateway fixes provider origin, model and admitted local tool names and rejects
typed/server-side tools. Bash and its children cannot reach either the loopback
provider bridge or the mounted provider Unix socket.

Post-agent execution is now a separate trust boundary. The runner freezes the
agent patch before running project code, recreates a fresh standalone checkout
for every acceptance/verification command, applies only that patch, and executes
the command in another no-network, clean-environment bubblewrap sandbox. Hidden
oracle bytes are materialized only into disposable validation checkouts through
no-follow path traversal; they are never written into the agent checkout.
Mutation checks likewise run in disposable validation checkouts. Therefore
agent-controlled source, package scripts and test hooks are never executed by
the host controller with host credentials or host filesystem authority.

The hosted isolation workflow tests forbidden host and symlink reads, read-only
Git/dependency mounts, environment filtering, private HOME/tmp state, fresh
checkout state isolation, the nested Bash provider denial, no-follow oracle
installation, post-agent validation isolation, provider route/model/tool policy,
streaming and the pinned Claude binary. It makes no real model calls.
Ubuntu 24.04 requires an AppArmor user-namespace exception for /usr/bin/bwrap.
The hosted workflow loads the reviewed bwrap.apparmor profile for that executable
only. It does not disable AppArmor globally. Future pilot/collection setup must
install bubblewrap, socat, libseccomp-dev, the pinned Claude Code client and the
pinned Anthropic Sandbox Runtime, then load this same AppArmor profile.

## Registration remains suspended

Existing R9/R2 files are retained unchanged for audit. Pilot, promotion and formal
workflows stop before model calls or promotion until a reviewed successor is
registered. The new adapter hash and runtime identity cannot match the old freeze.
Do not relabel these results or silently edit frozen hashes.

The outer network namespace has no external route. A per-invocation Unix socket
exposes only POST /v1/messages and /v1/messages/count_tokens (including beta=true)
to a parent-side gateway. A loopback bridge lets only the Claude client use its
normal HTTP API. The gateway fixes the configured HTTPS provider origin, base
path and model, replaces authentication headers, rejects other routes, rejects
unregistered local tools and typed/server tools, and never follows redirects.
No host TCP listener or provider credential is exposed to the coding agent.
Claude's Bash sandbox cannot use the bridge or Unix socket. Streaming is relayed
without buffering the full response. This permits the registered Claude client to
perform inference without granting arbitrary provider authority to agent tools.

Before registering a new execution profile, require hosted isolation tests and
fresh T05/A, T08/B and T20/C pilots to pass. Freeze a new execution profile and
formal plan, then collect a fresh cohort. The old benchmark/analysis and R9/R2
registration bytes remain unchanged in this repair PR; the successor registration
must bind the reviewed repair commit. Automatic synthetic checks alone do not
constitute real pilot evidence or authorize formal collection.

## Hosted verification

The original PR #18 isolation run passed on Ubuntu 24.04, including Claude Code
2.1.278 startup and the first fixed-provider gateway tests. The successor repair
must pass the expanded hosted execution-isolation workflow before any new pilot
registration. No synthetic isolation check by itself authorizes formal collection.
