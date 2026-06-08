# 环境检测与智能降级指南

## 定位

`check-env.py` 是 spec-driven-dev 工作室的**环境探测工具**。它在项目诊断阶段运行，检测用户的开发环境，推荐可用的 SDD 工具，并在工具不可用时自动降级。

## 为什么需要环境检测

旧的 spec-driven-dev 假设用户可以直接安装任何工具（`npm install -g openspec-cn`、`pip install uv`），但实际上：
- 用户可能没有 Node.js 环境
- 用户可能没有 Python/uv
- 用户可能在使用不支持插件的 AI 工具
- 用户可能在离线环境

**硬装工具的代价**：浪费时间、挫败感、最终放弃使用 SDD。

**智能降级的价值**：根据用户实际环境，推荐最适合且可立即使用的方案。

## 检测维度

### 维度 1：编程语言环境

```bash
python3 --version    # Python 是否可用
node --version       # Node.js 是否可用
npm --version        # npm 是否可用
uv --version         # uv 是否可用（Spec-Kit 需要）
```

### 维度 2：版本管理工具

```bash
git --version        # Git 是否可用（所有方案都需要）
```

### 维度 3：AI 工具能力

```bash
# Claude Code 插件市场是否可用
# Cursor 插件是否可用
# 其他 AI 工具的插件能力
```

## 推荐矩阵

根据检测结果，推荐方案：

| 检测条件 | 推荐方案 | 理由 |
|---------|---------|------|
| 有 Node + npm | OpenSpec | 可立即安装 `openspec-cn` |
| 有 Python + uv | Spec-Kit | 可立即安装 Spec-Kit |
| 有 Claude Code 插件市场 | Superpowers | 可安装 Superpowers 插件 |
| 有 Node，无 uv | OpenSpec + spec-first 备选 | OpenSpec 依赖 Node |
| 有 Python，无 uv | spec-first 备选 | Spec-Kit 需要 uv |
| 只有 Git | spec-first（AGENTS.md） | 零额外依赖 |
| 什么都没有 | spec-first（纯文本） | 只需要文本编辑器 |

## 降级路径

当首选工具不可用时，自动降级：

```
首选: Spec-Kit
    ↓ 无 Python/uv
降级: OpenSpec
    ↓ 无 Node/npm
降级: Superpowers（如果有 Claude Code）
    ↓ 无插件市场
降级: spec-first（AGENTS.md + 手动执行计划）
    ↓ 无 Git
降级: spec-first 纯文本（不版本管理）
```

## 输出示例

```
🔍 环境检测报告
========================

编程语言环境:
  ✅ Python 3.11.4
  ❌ Node.js (未安装)
  ❌ npm (未安装)
  ❌ uv (未安装)

版本管理:
  ✅ Git 2.42.0

AI 工具:
  ✅ Claude Code (检测到)
  ❌ Superpowers 插件 (未安装)

========================
推荐方案: spec-first（AGENTS.md）
理由: 你的环境有 Python 但没有 Node/uv。spec-first 零依赖，立即可用。

如果你以后安装了 Node.js，可以升级：
  npm install -g openspec-cn

安装命令:
  # 无需安装，直接使用 AGENTS.md 模板

下一步:
  1. 我会为你生成 AGENTS.md
  2. 后续功能 spec 也用 Markdown 模板
  3. 执行计划手动管理
```

## 使用方式

### 自动检测（推荐）

在 Step 0 自动运行：

```bash
python3 scripts/check-env.py
```

根据输出推荐方案。

### 手动检测

用户想确认某个工具是否可用：

```bash
python3 scripts/check-env.py --check openspec
python3 scripts/check-env.py --check spec-kit
python3 scripts/check-env.py --check superpowers
```

### 静默模式

在脚本中调用：

```bash
python3 scripts/check-env.py --json
```

输出 JSON 格式，便于脚本解析。

## 与工具选型矩阵的关系

`check-env.py` 的输出作为 Step 1 "项目诊断" 的输入。Step 1 的 3 个问题（项目阶段/团队规模/AI 工具）决定**方向**，`check-env.py` 决定**可行性**。

**综合决策**：
- Step 1 推荐 OpenSpec + `check-env.py` 有 Node → 确认 OpenSpec
- Step 1 推荐 OpenSpec + `check-env.py` 无 Node → 降级到 spec-first
- Step 1 推荐 Spec-Kit + `check-env.py` 有 uv → 确认 Spec-Kit
- Step 1 推荐 Spec-Kit + `check-env.py` 无 uv → 降级到 OpenSpec 或 spec-first
