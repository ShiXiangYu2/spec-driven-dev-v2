# 代码一致性检查指南

## 定位

`check-code-consistency.py` 是 spec-driven-dev 工作室的**第二层验证**。它在 spec 写完后、代码执行前运行，检查 spec 中的技术选型、接口设计、数据模型是否与现有代码库冲突。

## 什么时候运行

| 时机 | 命令 | 目的 |
|------|------|------|
| **写 spec 时**（已有代码库） | `check-code-consistency.py --scan-only` | 提取代码库约束，辅助写 spec |
| **执行前** | `check-code-consistency.py --spec spec.md --code-dir ./src` | 检查 spec 与代码是否一致 |
| **代码 review 时** | `check-code-consistency.py --spec spec.md --code-dir ./src --strict` | 严格检查所有约束 |

## 检查维度

### 维度 1：技术栈一致性

**检查内容**：spec 中的框架/库/工具是否与代码库现有选型一致。

**示例**：
- spec 说用 Express.js，但 `package.json` 里是 Fastify → **冲突**
- spec 说用 Prisma，但代码里已有 TypeORM → **冲突**
- spec 说用 bcrypt，但代码里已有 argon2 → **建议统一**

**扫描来源**：
- `package.json` / `Cargo.toml` / `pyproject.toml` / `go.mod`
- `requirements.txt` / `Pipfile`
- `Dockerfile` / `docker-compose.yml`

### 维度 2：接口路径一致性

**检查内容**：spec 中的 API 路径是否与已有路由冲突。

**示例**：
- spec 定义 `POST /api/v1/auth/login`，但已有 `POST /api/v1/users/login` → **建议统一**
- spec 定义 `GET /users/:id`，但已有 `GET /users/:id` → **冲突（重复）**

**扫描来源**：
- 路由文件（`src/routes/`、`app/urls.py`、`handlers/`）
- OpenAPI/Swagger 文档
- API 测试文件

### 维度 3：数据模型一致性

**检查内容**：spec 中的数据模型是否与已有模型冲突。

**示例**：
- spec 定义 `User` 模型有 `email` 字段，但已有 `User` 模型没有 → **需要迁移**
- spec 定义 `User` 模型的 `id` 是 UUID，但已有模型是自增 int → **冲突**

**扫描来源**：
- ORM 模型文件
- 数据库迁移文件
- Prisma schema / SQLAlchemy models / TypeORM entities

### 维度 4：代码风格一致性

**检查内容**：spec 中的代码风格要求是否与代码库现有风格一致。

**示例**：
- spec 要求使用分号，但代码库不用 → **建议跟随代码库**
- spec 要求函数名用 camelCase，但代码库用 snake_case → **冲突**

**扫描来源**：
- `.eslintrc` / `.prettierrc` / `pyproject.toml [tool.black]`
- 现有代码样本（随机抽样 3-5 个文件）

### 维度 5：依赖版本约束

**检查内容**：spec 要求新增的依赖是否与现有依赖版本兼容。

**示例**：
- spec 要求 `jsonwebtoken@9.x`，但代码库已有 `jsonwebtoken@8.x` → **建议升级现有**
- spec 要求 Node.js ≥ 18，但 `package.json` 的 `engines` 是 ≥ 16 → **建议更新 engines**

## 输出格式

```
📋 代码一致性检查报告
========================

技术栈一致性:
  ✅ 后端框架: spec(Express.js) vs 代码库(Express.js) — 一致
  ⚠️  ORM: spec(Prisma) vs 代码库(TypeORM) — 冲突
     建议: 统一使用 TypeORM，或说明为什么需要引入 Prisma

接口路径一致性:
  ✅ 未发现冲突路由

数据模型一致性:
  ⚠️  User 模型: spec要求email字段(唯一索引) vs 代码库无email字段 — 需要迁移
     建议: 添加数据库迁移脚本

代码风格一致性:
  ✅ 分号使用: spec(要求) vs 代码库(使用) — 一致
  ✅ 命名规范: spec(camelCase) vs 代码库(camelCase) — 一致

依赖版本约束:
  ⚠️  jsonwebtoken: spec(9.x) vs 代码库(8.x) — 版本不匹配
     建议: 升级现有依赖或调整 spec

========================
通过: 3 / 警告: 3 / 冲突: 0
```

## 处理冲突

当 `check-code-consistency.py` 报告冲突时：

**选项 A：改 spec（推荐）**
- 如果代码库已经稳定运行，优先让 spec 服从代码库
- 更新 spec 中的技术选型，与代码库保持一致

**选项 B：改代码库**
- 如果 spec 中的选型明显更优，且变更成本可控
- 需要额外写迁移计划，作为变更 spec 的一部分

**选项 C：接受差异（需用户确认）**
- 有些差异是故意的（如引入新技术栈）
- 在 spec 的 Constraints 中明确说明原因

## 与 validate-spec.py 的区别

| 维度 | validate-spec.py | check-code-consistency.py |
|------|------------------|---------------------------|
| **检查对象** | spec 文档本身 | spec vs 代码库 |
| **检查内容** | 四要素完整性、Non-Goals 数量 | 技术栈/接口/模型/风格一致性 |
| **运行时机** | 写 spec 后 | 执行前 |
| **是否需要代码库** | 否 | 是 |
| **输出** | 通过/失败 | 一致/警告/冲突 |
