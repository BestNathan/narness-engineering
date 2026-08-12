---
name: narness-rust
description: "指导在 Rust 项目中实施 harness 工程化——用 cargo/clippy/hook/脚本约束 AI agent，而非提示词。当需要为 Rust 项目建立约束、或将靠提示词反复失效的约束下沉为代码时调用。"
---

# Narness Rust — Rust Harness 工程化

把对 AI agent 的约束从「提示词」下沉为「代码、hook、脚本」，保证长程任务的正确性。

## 核心思想

能用代码、hook、脚本约束 agent 的，优先用它们，而非提示词。提示词是软约束，agent 可能忽略；脚本是硬约束，agent 无法逃避。

## 约束层级阶梯（Rust 映射）

| 层级 | 手段 | 约束力 |
|---|---|---|
| L0 提示词 | 口头/文档要求 | 最弱 |
| L1 项目约定 | CLAUDE.md | 弱 |
| L2 Skill | 本 skill | 中弱 |
| L3 Hook | PostToolUse 校验 | 中强 |
| L4 脚本 | verify-*.sh / verify-invariants.sh | 强 |
| L5 编译期 | clippy -D warnings、#![forbid] | 最强 |

## 何时调用本 skill

- 需要为 Rust 项目建立 harness 约束时
- 发现 agent 反复违反同一类约束（如总写 unwrap、总忘测试）时
- 需要把某个「靠提示词约束失效」的规则下沉为代码时

## 把约束下沉的步骤

1. 识别：哪条规则 agent 反复违反？
2. 定位层级：这条规则最适合落到 L3–L5 哪层？
3. 落地：
   - L3 → 配置 PostToolUse hook 跑校验脚本
   - L4 → 调用 scripts/ 下的校验脚本
   - L5 → 加 clippy lint / `#![forbid(...)]` / trait bound

## 可用脚本

| 脚本 | 用途 |
|---|---|
| `scripts/verify-fmt.sh [DIR]` | 格式检查：cargo fmt --check |
| `scripts/verify-check.sh [DIR]` | 编译检查：cargo check |
| `scripts/verify-clippy.sh [DIR]` | lint 检查：cargo clippy -D warnings |
| `scripts/verify-test.sh [DIR]` | 测试：cargo test |
| `scripts/verify-invariants.sh [DIR]` | 不变量：禁 unwrap/expect/panic!/unsafe 无注释 |
| `scripts/verify-test-discipline.sh [DIR]` | 测试纪律：改 .rs 必有测试 |

## 测试纪律

- 先写测试，再写实现
- 改动 src/ 下的 .rs 必须有对应测试文件
- 提交前按需跑 verify-fmt.sh / verify-clippy.sh / verify-test.sh

## 常见反模式与对应硬约束

| 反模式 | 硬约束 |
|---|---|
| 到处 unwrap() | clippy::unwrap_used + verify-invariants.sh |
| 裸 panic! | clippy::panic + thiserror/anyhow |
| 忘写测试 | verify-test-discipline.sh + hook |
| 格式漂移 | cargo fmt --check 门禁 |
