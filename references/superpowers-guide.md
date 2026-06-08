# Superpowers 完整指南

## 定位

Superpowers 是 Jesse Vincent（obra）在 2025 年 10 月开源的项目。核心理念是 **Process over Prompt（流程大于提示词）**——与其给 AI 写更精准的 prompt，不如给 AI 套上一套工程纪律，让它像有经验的工程师一样工作。

**注意**：Superpowers 不管规范文档，只管执行时的行为约束。最好跟 OpenSpec 或 Spec-Kit 配合使用。

## 适用场景

- Claude Code 重度用户
- 对代码质量有硬性要求的正式项目
- 想让 AI 产出"能上线"而不只是"能运行"的代码

## 不适用场景

- 快速原型验证（流程太重）
- 非 Claude Code 用户（这是 Claude Code 插件）
- 已经有成熟代码审查流程的团队（可能重复）

## 核心流程

```
brainstorming（需求澄清）
    → git worktrees（创建隔离分支）
    → writing-plans（拆成 2-5 分钟粒度的任务）
    → TDD（先写测试，再写实现）
    → subagent execution（子代理并行执行）
    → code review（双阶段审查）
    → finish branch（验收，处理分支）
```

## 关键特性

### 1. TDD 强制

AI 必须先写出"会失败的测试"，再写实现代码让测试通过，最后重构。

**任何试图跳过 TDD 的 prompt，Superpowers 都会拒绝执行**，并解释为什么。

### 2. 子代理并行

复杂任务自动拆分为子代理并行执行，提升效率。

### 3. 双阶段代码审查

- 第一阶段：自动化检查（lint、类型、测试）
- 第二阶段：逻辑审查（边界情况、异常处理）

### 4. Git Worktrees

每个任务在独立分支上执行，互不干扰。

## 安装

在 Claude Code 中：

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

重启 Claude Code。

## 使用

```
/superpowers:brainstorm      # 从需求澄清开始
/superpowers:write-plan      # 生成执行计划
/superpowers:execute-plan    # 开始执行
```

## Token 成本

完整跑下来比直接写代码多消耗 **10-20%** 的 Token，但返工减少了 **60-70%**。

**算总账是划算的。**

## 中文增强版

```bash
npm install -g superpowers-zh
```

支持更多国内工具。

## 优点

- TDD 强制，代码质量有保证
- 子代理并行，效率提升
- 双阶段审查，减少低级错误
- 流程自动化，减少人工干预

## 缺点

- Token 消耗增加 10-20%
- 只支持 Claude Code
- 流程较重，不适合快速原型
- 不管规范文档（需要配合 OpenSpec/Spec-Kit）

## 典型工作流（配合 OpenSpec）

1. 用 OpenSpec 锁定需求（`/opsx:new` → `/opsx:ff`）
2. 用 Superpowers 执行开发（`/superpowers:brainstorm` → `/superpowers:write-plan` → `/superpowers:execute-plan`）
3. Superpowers 自动读取 OpenSpec 的 tasks.md，生成极细粒度的执行计划
4. AI 自动：创建 Git 分支 → 写失败测试 → 写实现代码 → 让测试通过 → 双阶段代码审查
5. 用 OpenSpec 归档（`/opsx:verify` → `/opsx:archive`）
