# Spec-Kit 完整指南

## 定位

Spec-Kit 是 GitHub 官方出品的开源工具包，专为 AI 辅助编程设计。核心思想是"宪法式约束"——先定义项目最高原则，后续所有 AI 行为都必须以此为约束，不可逾越。

**社区数据**：⭐ 43.7k Stars（截至 2026 年 5 月），是目前社区认可度最高的 SDD 工具。不绑定任何特定 Agent，支持 Claude、GPT、Gemini 等主流模型。

## 核心概念：三文件 + 一宪法

Spec-Kit 的核心设计围绕四个文件展开：

| 文件 | 职责 | 说明 |
|------|------|------|
| **constitution.md** | 项目宪法 | 不可违背的原则。所有 Spec 都必须遵守。修改需团队决策。 |
| **spec.md** | 需求规格 | "唯一真实来源"。定义做什么和为什么做，不涉及怎么做。 |
| **plan.md** | 技术方案 | AI 起草、人审核修改。包含架构设计、接口契约、风险评估。 |
| **tasks.md** | 任务清单 | 将 plan 拆解为原子任务，每个任务对应一个独立可验证的交付物。 |

> **"用不同技术栈实现这个 Spec，Spec 是否仍然有效？"**
> 如果答案是"否"，说明你在 Spec 里混入了 HOW——把不是 Spec 的内容写进了 Spec。

## 适用场景

- 全新项目启动
- 团队 ≥ 3 人，需要统一标准
- 对合规性有要求的企业场景
- 项目复杂度 ≥ 3-5 个模块

## 不适用场景

- 快速迭代的小需求
- 已有代码库的局部改动
- 不想搭 Python 环境（Spec-Kit 依赖 uv）

## 核心流程（五阶段，严格顺序）

```
Constitution（宪法）
    → Specify（功能规范）
    → Plan（技术方案）
    → Tasks（任务拆解）
    → Implement（代码实现）
```

### 阶段 1：Constitution（宪法）

定义项目的最高原则，AI 在整个开发过程中都要遵守。

**宪法示例：**
```markdown
# 项目宪法

## 技术标准
- 前端：React + TypeScript
- 后端：Node.js，禁止引入 ORM 以外的数据库抽象层

## 质量要求
- 单元测试覆盖率 ≥ 85%
- 所有 API 必须有错误处理

## 简化原则
- 初始实现特性数 ≤ 3，多一个要写说明理由
```

### 阶段 2：Specify（功能规范）

为每个功能写详细规范，包含 What/Why/Constraints/Non-Goals。

### 阶段 3：Plan（技术方案）

生成技术实现方案，包含架构设计、数据模型、接口定义。

### 阶段 4：Tasks（任务拆解）

将方案拆解为可执行的任务清单，每个任务 2-5 分钟粒度。

### 阶段 5：Implement（代码实现）

按任务清单逐条实现，AI 严格遵守宪法约束。

## 安装

```bash
pip install uv
git clone https://github.com/github/spec-kit.git
```

## Claude Code 中使用

```
/speckit.constitution          # 生成项目宪法
/speckit.specify "功能描述"     # 生成功能规范
/speckit.plan                  # 生成技术方案
/speckit.tasks                 # 拆解任务
/speckit.implement             # 开始实现
```

## 优点

- 强制执行规范，防止 AI 跑偏
- 适合复杂项目和团队协作
- 宪法文件是长期约束，不受对话截断影响

## 缺点

- 前期投入大，要写大量文档
- 学习曲线陡
- 对快速迭代场景不够灵活

## 典型工作流

1. 安装 Spec-Kit
2. 写 Constitution（项目宪法）
3. 用 `/speckit.specify` 写功能规范
4. 用 `/speckit.plan` 做技术方案
5. 用 `/speckit.tasks` 拆任务
6. 用 `/speckit.implement` 执行
7. 定期回顾 Constitution，更新过时约束
