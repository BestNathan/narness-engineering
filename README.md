# Narness

Narness is a "research + documentation + Claude Code tooling" project that articulates and puts into practice an engineering philosophy:

> When code, hooks, or scripts can constrain an AI agent's behavior, prefer them over prompts. An agent will very likely not follow prompts; scripts and hooks let the agent discover that its implementation is wrong and guide it toward correct behavior, thereby guaranteeing correctness on long-running tasks.

## Philosophy

Prompts are soft constraints that an agent may ignore; scripts and hooks are hard constraints an agent cannot escape. Narness organizes its methodology around the **constraint ladder** (L0 prompts → L5 compile-time) and ships plugins that put constraints into code.

## Layout

- `docs/theory/` — theory and research docs
- `docs/reference/` — harness-engineering references for specific tools
- `plugins/narness-rust/` — the Rust harness-engineering plugin (skill + hook + scripts)
- `cli/` — the narness environment checker (npm package)
- `.claude-plugin/marketplace.json` — marketplace definition

## Quick start

Install the `narness-rust` plugin after adding the marketplace:

```bash
claude plugin marketplace add <this repo's URL>
claude plugin install narness-rust
```

## Theory docs

- [Why not just prompts](docs/theory/why-not-prompts.md)
- [The constraint ladder](docs/theory/constraint-ladder.md)
- [Decision guide](docs/theory/decision-guide.md)
- [Correctness of long-running tasks](docs/theory/long-running-correctness.md)
- [Command interception](docs/theory/command-interception.md) (replacing and normalizing agent commands via config + the narness CLI)

## Reference docs

- [Rust test harness engineering](docs/reference/rust-test-harness.md) (nextest + llvm-cov + LLM feedback)
- [Git hooks](docs/reference/git-hooks.md) (harness execution at commit/push time)
- [Claude Code hooks](docs/reference/claude-code-hooks.md) (harness execution at agent tool-call time)
- [Codex hooks](docs/reference/codex-hooks.md) (harness execution in the OpenAI Codex CLI)

## Environment check

`cli/` is an npm package. Put a `.narness.toml` in the project root declaring the agent's runtime requirements, then check them with `npx narness`:

```toml
[[checks]]
type = "version"
name = "node"
min = "22"

[[checks]]
type = "exists"
name = "rg"
```

```bash
npx narness           # human report (failures include fix suggestions)
npx narness --json    # structured output (for hooks/CI)
```
