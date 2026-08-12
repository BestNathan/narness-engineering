# Rust 测试 Harness 工程化

## 1. 定位

测试是约束 AI agent 正确性的最强 ground truth（约束阶梯 L4）。本文档说明如何用 **cargo-nextest** + **cargo-llvm-cov** 构建一个 Rust 测试 harness——它不只是「跑测试」，而是能**把测试失败以结构化、可操作的方式反馈给 LLM**，让 agent 自己发现问题并修复。

核心命题：测试约束不应停留在提示词（「记得写测试」），而应下沉为可执行的 harness（脚本 + hook + 阈值门禁）。

## 2. 测试运行器：nextest

### 2.1 为什么选 nextest 而非 cargo test

| 维度 | cargo test | cargo-nextest |
|---|---|---|
| 执行模型 | 测试二进制内多线程 | 每个测试独立进程，并行 |
| 速度 | 基线 | 2–3× 更快（多二进制并行消除长尾） |
| 隔离 | 共享进程（一个 panic 影响全局状态） | 进程隔离（一个崩溃不影响其余） |
| flaky 处理 | 无 | `--retries` 自动重试 |
| 超时 | 无（挂起卡死 CI） | 单测超时强杀 |
| 输出 | 墙文本 | 结构化结果表 + 进度 + 单测耗时 |
| 失败定位 | 需自行解析 | 每个失败单测的精确位置与输出 |

**Narness 视角**：nextest 的价值不只是「快」。它对 harness 的关键意义在于**结构化输出**——每个测试的 pass/fail、位置、耗时都机器可读，这让脚本能把失败信息精确、简洁地回传给 LLM，而不是抛给它一堵文本墙。

### 2.2 安装与基本用法

```bash
cargo install cargo-nextest

# 运行测试
cargo nextest run

# 只跑失败的测试（重跑 flaky）
cargo nextest run --retries 2

# 指定 profile
cargo nextest run --profile ci
```

注意：nextest 不运行 doctest，需单独执行 `cargo test --doc`。

### 2.3 nextest.toml 配置

配置文件：`.config/nextest.toml`。

```toml
[profile.default]
retries = 0
fail-fast = false
failure-output = "immediate"   # 失败即时输出（而非全跑完才打印）

[profile.ci]
retries = 2
fail-fast = true
failure-output = "immediate-final"
slow-timeout = { period = "60s", terminate-after = 2 }

# 输出 JUnit XML 供 CI 消费
[profile.ci.junit]
path = "target/nextest/ci/junit.xml"
```

关键点：`failure-output = "immediate"` 让失败即时打印，这是 harness 反馈 LLM 的前提——失败信息越早出现，agent 越早看到。

### 2.4 与 harness 集成

把 nextest 封装为单一职责脚本，失败时输出到 stderr 并 exit 1：

```bash
#!/usr/bin/env bash
# 只做一件事：用 nextest 跑测试
set -euo pipefail
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"
cargo nextest run
```

## 3. 覆盖率：llvm-cov

### 3.1 为什么需要覆盖率

测试的「存在」不等于「覆盖」。agent 可能写了测试，但测试没覆盖关键分支。覆盖率是**测试质量的 ground truth**，把「写了测试」这个软约束变成「覆盖率 ≥ 阈值」这个硬约束。

### 3.2 安装与用法

```bash
cargo install cargo-llvm-cov

# 跑测试并生成覆盖率
cargo llvm-cov

# 生成 HTML 报告（逐行高亮未覆盖代码）
cargo llvm-cov --html
# 报告在 target/llvm-cov/html/index.html

# 输出 lcov（供 Codecov / VS Code Coverage Gutters）
cargo llvm-cov --lcov --output-path lcov.info
```

### 3.3 覆盖率阈值作为门禁

```bash
# 行/区域/函数覆盖率同时强制，低于阈值则 exit 非零
cargo llvm-cov --fail-under-lines 80 --fail-under-regions 80 --fail-under-functions 75
```

或写入 `.llvm-cov.toml`：

```toml
fail-under-lines = 80
fail-under-functions = 75
fail-under-regions = 80
```

**Narness 视角**：覆盖率阈值的价值在于把「测试是否充分」从 agent 的自觉判断变成**确定性的 pass/fail**。低于阈值 → exit 非零 → hook/脚本把「覆盖率 78% < 80%，以下函数未覆盖：…」回传给 LLM，agent 被迫补测试。

## 4. 何时触发测试（分层触发）

测试 harness 不应只有一个触发时机。按约束阶梯 L3–L5 分层：

| 时机 | 触发方式 | 跑什么 | 目的 |
|---|---|---|---|
| 编辑后（L3 hook） | PostToolUse hook | 快速编译检查（`cargo check`，非全量测试） | 编译错误即时反馈 |
| 提交前（L4 脚本） | agent 主动调用 verify-*.sh | 全量 nextest + llvm-cov 阈值 | 完整门禁，阻止累积错误 |
| CI（L4/L5） | CI pipeline | 全量测试 + 覆盖率 + JUnit | 回归保护，物理约束 |

**为什么 hook 阶段只跑 check 而非全量测试**：全量测试耗时，每次编辑都跑会拖慢编辑循环、打断 agent 心流。hook 只做最快的编译检查，全量测试交给提交前的脚本和 CI——这是「快速 hook + 可组合脚本」的分层。

## 5. 如何保证 harness 能给 LLM 反馈

这是 Narness 的核心：harness 的价值不在于「检测失败」，而在于**让 LLM 看到失败并据此修复**。四个要点：

### 5.1 输出可定位

失败信息必须含精确位置（文件:行号 + 失败原因），让 agent 不用猜。nextest 的结构化输出天然满足这点；覆盖率报告能指出「哪些行未覆盖」。

### 5.2 exit code 语义明确

- `0`：通过
- `1`：校验失败（脚本层面）
- `2`：hook 失败，stderr 回传 LLM

脚本用明确的 exit code 区分「通过/失败」，hook 用 exit 2 触发回传。

### 5.3 hook 的 stderr 回传机制

PostToolUse hook 退出码 2 时，其 **stderr 会被作为系统消息注入 LLM 上下文**。所以校验失败时，脚本必须把诊断写到 stderr（而非 stdout），否则 LLM 看不到。

```bash
# 错误示范：诊断信息进了 stdout，hook 回传的是 stderr，LLM 看不到
cargo nextest run 2>&1 | tail

# 正确：把诊断信息写到 stderr
if ! out="$(cargo nextest run 2>&1)"; then
  printf '%s\n' "$out" >&2   # 写 stderr，hook 回传给 LLM
  exit 2
fi
```

### 5.4 失败信息可操作

失败信息要回答三个问题，而不只是「失败了」：
1. **哪里失败**：文件名 + 行号 + 测试名
2. **为什么失败**：断言期望 vs 实际、编译错误、覆盖率差距
3. **怎么修**：下一步建议（如「覆盖率 78% < 80%，请为 `foo::bar` 补测试」）

## 6. 与 narness-rust 脚本的对应

本文档的工具映射到 narness-rust 插件的单一职责脚本：

| 脚本 | 工具 | 对应本文档 |
|---|---|---|
| `verify-check.sh` | cargo check | §4 编辑后 hook |
| `verify-test.sh` | cargo test（可替换为 nextest） | §2 |
| `verify-clippy.sh` | cargo clippy -D warnings | 编译期约束 |
| `verify-invariants.sh` | 不变量扫描 | 代码规范 |
| `verify-test-discipline.sh` | 测试纪律 | §4 提交前 |

（首期脚本为保持零依赖使用 `cargo test`；`nextest` / `llvm-cov` 作为推荐工具在本文档说明，后续可作为脚本的可选后端。）
