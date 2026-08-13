# Narness

Narness 是「研究 + 文档 + Claude Code 工具集」项目，阐述并落地一套工程化思想：

> 能用代码、hook、脚本约束 AI agent 行为的，优先用这些，而非提示词。因为 agent 很可能不按提示词办事；脚本、hook 能让 agent 发现实现有问题，并指导其正确行为，从而保证长程任务的正确性。

## 理念

提示词是软约束，agent 可能忽略；脚本、hook 是硬约束，agent 无法逃避。Narness 用「约束层级阶梯」（L0 提示词 → L5 编译期）组织方法论，并提供插件把约束落地为代码。

## 目录

- `docs/theory/` — 理论研究文档
- `docs/reference/` — 具体工具的 harness 工程化参考
- `plugins/narness-rust/` — Rust harness 工程化插件（skill + hook + 脚本）
- `.claude-plugin/marketplace.json` — marketplace 定义

## 快速开始

安装 marketplace 后安装 `narness-rust` 插件：

```bash
claude plugin marketplace add <本仓库地址>
claude plugin install narness-rust
```

## 理论文档

- [为什么不能只靠提示词](docs/theory/why-not-prompts.md)
- [约束层级阶梯](docs/theory/constraint-ladder.md)
- [决策准则](docs/theory/decision-guide.md)
- [长程任务的正确性](docs/theory/long-running-correctness.md)

## 参考文档

- [Rust 测试 Harness 工程化](docs/reference/rust-test-harness.md)（nextest + llvm-cov + LLM 反馈）
- [Git Hooks](docs/reference/git-hooks.md)（提交/推送时机的 harness 执行）
- [Claude Code Hooks](docs/reference/claude-code-hooks.md)（agent 工具调用时机的 harness 执行）
- [Codex Hooks](docs/reference/codex-hooks.md)（OpenAI Codex CLI 的 harness 执行）
