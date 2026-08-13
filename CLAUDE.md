# Narness

Narness 是「研究 + 文档 + Claude Code 工具集」项目，阐述并落地「harness 工程化」理念。

## 核心理念

能用代码、hook、脚本约束 AI agent 行为的，优先用这些，而非提示词。因为 agent 很可能不按提示词办事；脚本、hook 能让 agent 发现实现有问题，并指导其正确行为，从而保证长程任务的正确性。

约束层级阶梯：L0 提示词 → L1 项目约定 → L2 Skill → L3 Hook → L4 脚本校验 → L5 编译期；目标是让约束从 L0-L2 下沉到 L3-L5。

## 项目约定（必须遵守）

1. **脚本单一职责**：校验脚本必须一个脚本只做一件事。禁止「完整门禁」这类把 fmt/lint/test 全包的上帝脚本。每个校验拆成独立的 `verify-*.sh`（如 `verify-fmt.sh` / `verify-check.sh` / `verify-clippy.sh` / `verify-test.sh`）。
2. **hook 入口薄**：hook 脚本（`post-edit-gate.sh`）只做「判断触发条件 + 委派给单一职责脚本」，不内联校验逻辑。
3. **失败信息回传 LLM**：脚本失败时必须把诊断写到 stderr（PostToolUse hook 退出码 2 会把 stderr 注入 LLM 上下文），确保 agent 能看到自己的错误并修复。

## 结构

- `plugins/narness-rust/` — Rust harness 工程化插件（skill + PostToolUse hook + 6 个 `verify-*.sh` 脚本）
- `docs/theory/` — 理论文档（约束阶梯、决策准则等）
- `docs/reference/` — 工具实践参考（如 Rust 测试 harness）
- `.claude-plugin/marketplace.json` — 外层 marketplace

## 首期范围

只做 Rust，纯理论无示例项目。后续扩展：其他语言插件（narness-python 等）、示例项目。
