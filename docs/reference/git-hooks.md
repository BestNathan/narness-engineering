# Git Hooks：提交/推送时机的 harness 执行

## 1. 机制原理

git 在特定动作前后，执行 `.git/hooks/` 目录下的同名脚本。这些脚本是**版本控制层**的约束机制——在代码进入 git 历史前拦截。

hooks 分两类：

- **客户端 hooks**：在本地仓库触发（commit、push 等），用于提交前校验
- **服务端 hooks**：在远程仓库触发（pre-receive、update、post-receive），用于强制策略

harness 脚本主要挂在**客户端 hooks**上，因为目标是「在 agent 提交前拦截坏代码」。

## 2. 常用客户端 hooks

| 钩子 | 时机 | 用途 | 退出非零效果 |
|---|---|---|---|
| `pre-commit` | `git commit` 前，提交信息编辑器弹出前 | 格式、lint、快速测试 | 阻止提交 |
| `commit-msg` | 提交信息编辑后、提交前 | 校验提交信息格式 | 阻止提交 |
| `pre-push` | `git push` 前 | 全量测试、较重门禁 | 阻止推送 |
| `post-commit` | 提交完成后 | 通知、日志 | 不阻止 |
| `pre-rebase` | `git rebase` 前 | 阻止危险 rebase | 阻止 |
| `post-merge` / `post-checkout` | 合并/切换分支后 | 触发依赖更新 | 不阻止 |

对 harness 最有用的是 `pre-commit`（快检查）和 `pre-push`（重检查）。

## 3. 配置方式

### 3.1 直接写 `.git/hooks/`

```bash
# .git/hooks/pre-commit
#!/usr/bin/env bash
set -euo pipefail
bash plugins/narness-rust/scripts/verify-fmt.sh
bash plugins/narness-rust/scripts/verify-clippy.sh
```

```bash
chmod +x .git/hooks/pre-commit
```

**缺点**：`.git/` 不入库，无法与团队共享；换机器/克隆后丢失。

### 3.2 `core.hooksPath` 指向仓库内目录

把 hooks 放进仓库（如 `.githooks/`），再指向它：

```bash
git config core.hooksPath .githooks
```

**优点**：hooks 脚本入库、可共享、可 code review。

### 3.3 pre-commit 框架

用 `.pre-commit-config.yaml` 声明式管理，跨语言、自动安装：

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: verify-fmt
        name: cargo fmt --check
        entry: bash plugins/narness-rust/scripts/verify-fmt.sh
        language: system
        files: '\.rs$'
      - id: verify-clippy
        name: cargo clippy -D warnings
        entry: bash plugins/narness-rust/scripts/verify-clippy.sh
        language: system
        files: '\.rs$'
```

**优点**：自动管理 hook 安装、支持 `files` 过滤（只在 `.rs` 改动时触发）、生态成熟。

## 4. hook 脚本规范

1. **退出码**：`0` = 通过；**非零 = 阻止提交/推送**。这是 git hook 的强制机制。
2. **stdout/stderr**：hook 的输出会显示给用户（提交者），但**不会**反馈给任何 LLM——git hook 只做「阻止」，不做「反馈」。
3. **性能**：pre-commit 必须快（每次提交都跑），重的检查留给 pre-push 或 CI。

## 5. 具体示例：分层挂载

**pre-commit（快）**——只跑格式和 lint，几秒内完成：

```bash
#!/usr/bin/env bash
# .githooks/pre-commit
set -euo pipefail
bash plugins/narness-rust/scripts/verify-fmt.sh
bash plugins/narness-rust/scripts/verify-clippy.sh
```

**pre-push（重）**——跑全量测试和覆盖率：

```bash
#!/usr/bin/env bash
# .githooks/pre-push
set -euo pipefail
bash plugins/narness-rust/scripts/verify-test.sh
cargo llvm-cov --fail-under-lines 80
```

## 6. 注意事项

- **绕过**：`git commit --no-verify` 会跳过 pre-commit。git hook 是「约束」，不是「物理不可违反」——真正强制的只有服务端 hook 或 CI。
- **服务端 hook**：`pre-receive` 在远程强制校验，agent 无法绕过。这是 git 层面最强的约束（对应约束阶梯 L5 的「物理不可能违反」）。
- **Windows**：hook 脚本默认用 sh 执行，shebang 需要兼容；或用 pre-commit 框架规避平台差异。

## 7. 在分层 harness 中的位置

git hook 是「提交级」约束，比 agent 的编辑级 hook（Claude Code / Codex）更粗、但更「硬」——它由 git 执行，不依赖 agent 自觉。分层：

```
编辑后（CC/Codex hook）→ 提交前（git pre-commit）→ 推送前（git pre-push）→ CI
  细粒度即时反馈        阻止坏代码入库            全量测试门禁          回归保护
```

git hook 的价值在于：即使 agent 忽略了编辑级的即时反馈，坏代码也**进不了 git 历史**。
