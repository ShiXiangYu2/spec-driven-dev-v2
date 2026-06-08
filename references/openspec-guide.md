# OpenSpec 完整指南

## 定位

OpenSpec 来自 Fission-AI 团队，定位为"轻量敏捷的规范管理层"。核心设计是 Delta Specs（增量规范）——把"当前项目的事实"和"这次的变更提案"明确分开存放。

## 适用场景

- 已有代码库维护
- 需求频繁迭代的中小团队
- 个人开发者
- "已经有一堆代码但没有任何规范文档，想补上又不知道从哪里下手"的场景

## 不适用场景

- 从 0 开始的全新项目（Spec-Kit 更合适）
- 对规范约束要求极高的企业场景

## 核心设计：Delta Specs

```
openspec/
├── specs/          # 当前项目的真相（已建立的能力）
└── changes/        # 变更提案（准备改的东西）
    └── add-dark-mode/
        ├── proposal.md   # 为什么改、改什么
        ├── specs/        # 这次涉及的规范变更
        ├── design.md     # 技术方案
        └── tasks.md      # 任务清单
```

## 核心流程

```
init → new → ff → apply → verify → archive
```

### 1. init（初始化）

在项目根目录创建 `openspec/` 结构。

```bash
cd your-project
openspec init
```

### 2. new（创建变更）

为每个新需求创建一个独立的变更单。

```
/opsx:new add-dark-mode
```

### 3. ff（快进）

自动生成 proposal.md、design.md、tasks.md。

```
/opsx:ff
```

**重要**：生成后必须手动补上 Non-Goals！

```markdown
## 非目标（v1 不做）
- OAuth 第三方登录
- 手机号登录
- 记住我功能
```

### 4. apply（执行实现）

按 tasks.md 执行任务。

```
/opsx:apply
```

### 5. verify（验证）

检查代码是否符合规范。

```
/opsx:verify
```

### 6. archive（归档）

变更合并回主规范库，历史可查。

```
/opsx:archive
```

## 安装

```bash
npm install -g openspec-cn  # 推荐中文版
```

## Claude Code / Cursor 中使用

```
/opsx:new 变更名          # 创建新变更
/opsx:ff                  # 快进，自动生成文档
/opsx:apply               # 执行实现
/opsx:verify              # 检查规范
/opsx:archive             # 归档，更新主规范库
```

## 优点

- 低侵入性，不破坏现有工作流
- 增量式建立规范，渐进式改进
- 支持 25+ 种 AI 工具，零 API 密钥
- 规范始终跟着代码走（通过 archive 机制）

## 缺点

- 不强制 TDD
- 不强制代码审查
- 需要自觉执行 archive 步骤

## 典型工作流

1. 安装 `openspec-cn`
2. 在项目根目录执行 `openspec init`
3. 新需求来时：`/opsx:new 需求名`
4. `/opsx:ff` 自动生成文档
5. **手动补上 Non-Goals**（关键步骤！）
6. `/opsx:apply` 执行开发
7. `/opsx:verify` 检查规范
8. `/opsx:archive` 归档
