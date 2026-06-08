# Spec-to-Code 桥梁：从规范到代码的完整路径

## 核心理念

**规范不是终点，执行计划的起点。**

旧的 spec-driven-dev 停在"生成 spec 文档"就结束。工作室升级后，spec 确认后还要建立到代码的可执行路径——让开发者拿到 spec 后知道：改哪些文件、按什么顺序改、改完怎么验证。

## 桥梁三层结构

```
Spec 文档（What/Why/Constraints/Non-Goals）
    ↓ 提取
执行计划（文件清单 + 任务拆解 + 依赖关系）
    ↓ 执行
代码变更（新增/修改/删除文件）
    ↓ 验证
一致性检查（spec vs 代码）
    ↓ 维护
漂移检测（spec 是否还反映代码真相）
```

## 第一层：从 Spec 提取执行计划

### 自动提取

使用 `scripts/generate-execution-plan.py`：

```bash
# 基本用法（使用占位符路径）
python3 scripts/generate-execution-plan.py \
  --spec ./specs/user-login.md \
  --output ./execution-plan.md

# 扫描代码目录，推断真实文件路径
python3 scripts/generate-execution-plan.py \
  --spec ./specs/user-login.md \
  --output ./execution-plan.md \
  --code-dir ./src \
  --feature auth
```

脚本会读取 spec 中的以下章节，自动生成执行计划：
- **接口设计** → 推断需要新增/修改的路由文件
- **数据模型** → 推断需要新增/修改的模型文件和迁移脚本
- **任务拆解** → 按依赖排序，生成执行顺序
- **Constraints** → 推断需要新增的依赖包和配置

**目录扫描**：当提供 `--code-dir` 时，脚本会扫描现有目录结构（`routes/`、`models/`、`services/`、`tests/` 等），根据实际项目结构推断文件路径，而不是输出 `[feature].js` 占位符。

### 手动补全

自动提取后，需要人工检查并补全以下内容：

1. **文件级变更清单**：自动提取的可能遗漏现有文件的修改
2. **依赖安装命令**：`npm install bcrypt jsonwebtoken` 等
3. **数据库迁移命令**：`npx prisma migrate dev` 等
4. **环境变量变更**：新增哪些 `.env` 配置
5. **CI/CD 变更**：是否需要更新测试流水线

### 执行计划模板

```markdown
# 执行计划：[功能名]

> 生成自：specs/功能名.md
> 生成日期：YYYY-MM-DD

## 1. 环境准备

```bash
# 安装新依赖
npm install bcrypt jsonwebtoken

# 数据库迁移（如需要）
npx prisma migrate dev --name add_user_auth
```

## 2. 文件变更清单

| # | 文件 | 操作 | 说明 | 依赖 |
|---|------|------|------|------|
| 1 | src/models/User.js | 新增 | User 模型 | 无 |
| 2 | src/utils/crypto.js | 新增 | bcrypt 封装 | 无 |
| 3 | src/middleware/validator.js | 新增 | 输入验证 | 无 |
| 4 | src/routes/auth.js | 新增 | 登录路由 | #1, #2, #3 |
| 5 | tests/auth.test.js | 新增 | 测试 | #4 |

## 3. 任务执行顺序

按依赖关系拓扑排序执行：

**Phase 1：基础设施（可并行）**
- [ ] Task 1：创建 User 模型
- [ ] Task 2：实现 bcrypt 工具
- [ ] Task 3：实现验证中间件

**Phase 2：核心功能（依赖 Phase 1）**
- [ ] Task 4：实现登录接口
- [ ] Task 5：实现锁定逻辑

**Phase 3：验证（依赖 Phase 2）**
- [ ] Task 6：写单元测试
- [ ] Task 7：写集成测试
- [ ] Task 8：手动验证 checklist

## 4. 验证点

**每 Phase 完成后验证**：
- Phase 1 验证：数据库迁移成功，模型可正常实例化
- Phase 2 验证：API 返回正确状态码
- Phase 3 验证：测试覆盖率 ≥ 80%，所有测试通过

## 5. 会话切换指南

**执行会话开始时，让 AI 读取以下文件**：
1. `AGENTS.md`（项目级约束）
2. `specs/功能名.md`（功能级规范）
3. 本执行计划文件

**执行会话的标准 prompt**：
```
请按以下顺序执行：
1. 读取 AGENTS.md + specs/功能名.md + 执行计划
2. 从 Phase 1 开始执行
3. 每完成一个 Phase，汇报进度并等待确认
4. 严格执行 Non-Goals，不实现范围外的功能
5. 所有代码必须通过测试
```
```

## 第二层：执行会话的规范

### 执行会话的输入

执行会话开始时，AI 必须读取的文件：
1. **AGENTS.md** — 项目级最高约束
2. **功能 spec** — 当前功能的 What/Why/Constraints/Non-Goals
3. **执行计划** — 文件清单 + 任务顺序 + 验证点

### 执行会话的行为规范

1. **严格按执行计划顺序**：先 Phase 1，再 Phase 2，不跳步
2. **每 Phase 完成后汇报**：告诉用户完成了什么、下一步做什么
3. **遇到 spec 冲突时暂停**：如果实现过程中发现 spec 不合理，停下来讨论，不擅自修改
4. **Non-Goals 是红线**：任何试图实现 Non-Goals 中功能的请求，都要拒绝并引用 spec
5. **测试先行（如适用）**：如果是 Superpowers 用户，严格执行 TDD

### 执行会话的输出

每个 Phase 完成后输出：
- 修改了哪些文件
- 新增/删除/修改了多少行代码
- 测试是否通过
- 覆盖率是否达标
- 是否遇到 spec 中未预料到的问题

## 第三层：Spec 变更回流机制

> **这是之前版本缺失的关键环节。**

执行过程中，spec 和执行计划**不是只读文档**。当发现 spec 不合理时，必须按规范流程更新，而不是擅自偏离。

### 什么时候需要回流

| 场景 | 处理方式 |
|------|---------|
| **spec 遗漏**（漏了一个边界条件） | 更新 spec → 重新生成执行计划 → 继续 |
| **spec 错误**（接口定义与实际不符） | 更新 spec → 重新生成执行计划 → 回滚已做工作 → 重做 |
| **技术约束不可行**（要求的库不存在） | 更新 spec Constraints → 重新生成 → 继续 |
| **新需求**（用户说"再加个功能"） | **不直接加**。先判断：是遗漏（补到 spec）还是新需求（进 backlog） |

### 回流流程（5 步）

```
发现问题
    ↓
Step 1: 暂停执行（在当前 Phase 完成后暂停，不要中途停止）
    ↓
Step 2: 标记问题（在执行计划中记录："发现 spec 遗漏：..."）
    ↓
Step 3: 更新 spec（修改 spec 文件，补充遗漏或修正错误）
    ↓
Step 4: 重新生成执行计划（运行 generate-execution-plan.py）
    ↓
Step 5: 继续执行（从下一个 Phase 继续）
```

### 回流时的铁律

1. **不要让新需求偷偷溜进当前范围**。如果是新需求，先更新 Non-Goals，再决定是否纳入当前迭代。
2. **执行计划必须重新生成**。不要凭记忆修改，重新跑脚本确保一致性。
3. **已完成的 Phase 一般不重做**。除非 spec 错误导致已完成的代码完全不可用。
4. **每次回流都要记录原因**。在执行计划中写明"为什么回流"，便于后续复盘。

### 回流示例

**场景**：执行 Phase 2（登录接口）时，发现 spec 漏了"密码强度验证"。

```markdown
## 执行计划变更记录

### 2026-05-04 回流 #1
- **触发**：Phase 2 实现中发现 spec 遗漏密码强度验证
- **spec 更新**：在 Constraints 中补充"密码必须包含字母+数字，长度 8-64"
- **影响**：Phase 1（User 模型）需补充 password_strength 字段 → Phase 2 需添加验证中间件
- **重新生成**：执行计划已更新（v1.1）
- **继续**：从 Phase 2 子任务"实现验证中间件"继续
```

## 第四层：执行后的验证

### 一致性检查

执行完成后，运行：

```bash
python3 scripts/check-code-consistency.py \
  --spec ./specs/功能名.md \
  --code-dir ./src
```

检查项：
- [ ] spec 中的接口是否在代码中实现
- [ ] spec 中的数据模型是否与代码一致
- [ ] spec 中的 Constraints 是否被遵守（如 bcrypt、JWT 有效期）
- [ ] Non-Goals 中的功能是否真的没有实现

### 漂移检测

项目演进一段时间后，运行：

```bash
python3 scripts/detect-spec-drift.py \
  --spec ./AGENTS.md \
  --code-dir ./src
```

检查项：
- [ ] AGENTS.md 中的技术栈约束是否还适用
- [ ] AGENTS.md 中的 Non-Goals 是否被意外实现
- [ ] 功能 spec 中的接口签名是否已与代码不同步

## 常见错误

### 错误 1：Spec 和执行计划脱节

**❌ 错误**：spec 写完后，执行计划只是简单复制任务列表，没有文件级清单。

**✅ 修复**：执行计划必须包含具体的文件路径和操作类型。

### 错误 2：执行会话不读取 spec

**❌ 错误**：执行会话开始时，AI 没有读取 spec 文件，凭记忆执行。

**✅ 修复**：执行会话的 prompt 必须明确要求 AI 先读取 spec 文件。

### 错误 3：Phase 之间缺少验证

**❌ 错误**：一口气把所有代码写完，最后才发现 Phase 1 的基础设施有问题。

**✅ 修复**：每个 Phase 完成后必须验证，通过后再进入下一个 Phase。

### 错误 4：发现 spec 问题时不回流

**❌ 错误**：执行中发现 spec 漏了一个字段，直接按自己的理解加上去，不更新 spec。

**✅ 修复**：按"Spec 变更回流机制"处理——暂停→更新 spec→重新生成→继续。

### 错误 5：执行计划不更新

**❌ 错误**：执行过程中发现需要新增文件，但执行计划没有更新。

**✅ 修复**：执行过程中如果需要偏离执行计划，先更新执行计划文件，再执行。

## 最佳实践

1. **执行计划也是文档**：进 git，与 spec 和代码一起版本管理
2. **Phase 粒度控制在 30 分钟内**：每个 Phase 应该能在 30 分钟内完成和验证
3. **预留缓冲时间**：执行计划中预留 20% 的缓冲时间给意外情况
4. **失败回滚**：每个 Phase 完成后 commit，失败时可以回滚到上一个稳定点
5. **回流必须记录**：每次 spec 变更都要在执行计划中写明原因
