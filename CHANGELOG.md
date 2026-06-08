# Changelog

## 1.1.0

- **新增 constitution.md 模板**：项目宪法——不可违背的原则层，API 设计/安全/代码质量/基础设施约束归入独立文件
- **新增 tasks.md 模板**：三文件体系补齐——spec.md（需求）+ plan.md（方案）+ tasks.md（任务）
- **新增核心哲学第 7 条**："三文件 + 一宪法"模式，明确 constitution 优先于所有 spec
- **更新 spec-writing-guide.md**：增加好 Spec 六要素框架（Problem Statement / Success Metrics / User Stories / Acceptance Criteria / Non-Goals / Constraints）+ 粒度检验标准
- **更新 spec-kit-guide.md**：增补社区数据（43.7k Stars）+ 三文件一宪法概念详解
- **新增 SKILL.md SDD 成熟度三级光谱**：L1 Spec-First → L2 Spec-Anchored → L3 Spec-as-Source
- **更新 References 路由表 / Assets 模板速查 / 核心规则速查**：纳入 constitution 和三文件体系
- **更新 Step 3 路径A**：推荐"三文件 + 一宪法"输出结构

## 1.0.0

- 初始版本发布
- 建立从"需求澄清→规范定义→执行计划→代码实现→一致性验证→漂移检测"的完整闭环
- 支持 Spec-Kit、OpenSpec、Superpowers、spec-first 四种工具选型与适配
- 提供 8 个自动化脚本：validate-spec、peer-review-spec、check-code-consistency、detect-spec-drift、generate-execution-plan、check-env、run-evals
- 包含 6 个 spec 模板和 12 篇参考指南
- 四层验证体系：Spec 文本验证 → 同行评审 → 代码一致性验证 → Spec 漂移检测
