# Spec 漂移检测指南

## 定位

`detect-spec-drift.py` 是 spec-driven-dev 工作室的**第三层验证**。它在项目演进后运行，检测 spec 是否还反映代码的当前真相。

**核心理念**：spec 不是写一次就扔的文档。项目演进后，spec 会"漂移"——代码变了，但 spec 没更新。漂移的 spec 比没有 spec 更危险，因为它会给 AI 错误的约束。

## 什么时候运行

| 时机 | 目的 |
|------|------|
| **每周例行检查** | 发现 spec 是否已过时 |
| **发布前** | 确认 spec 与发布代码一致 |
| **新成员入职时** | 确认 AGENTS.md 还适用 |
| **AI 执行会话开始时** | 确认要读取的 spec 没有漂移 |
| **需求变更后** | 确认相关 spec 已更新 |

## 检测类型

### 类型 1：Non-Goals 漂移（范围蔓延）

**症状**：spec 的 Non-Goals 里列了"不做 OAuth"，但代码库里已经实现了 OAuth。

**危害**：AI 执行新功能时，看到 Non-Goals 里有 OAuth，可能会拒绝实现相关的功能——但实际上 OAuth 已经存在了。

**检测方法**：
- 扫描代码库中是否出现了 Non-Goals 中列出的功能关键词
- 扫描路由表、模型定义、依赖列表

**示例输出**：
```
⚠️ Non-Goals 漂移检测:
   Spec  says: "v1 不做 OAuth 第三方登录"
   Code  has:  src/routes/oauth.js (Google OAuth 实现)
   建议: 将 OAuth 从 Non-Goals 移除，或标记为"v2 已实现"
```

### 类型 2：接口签名漂移

**症状**：spec 定义 `POST /api/v1/auth/login` 返回 `{token, expires_in}`，但代码实际返回 `{accessToken, refreshToken, expiresAt}`。

**危害**：AI 按 spec 写前端对接代码，但实际接口不同，导致联调失败。

**检测方法**：
- 读取 spec 中的接口定义
- 扫描代码中的路由处理器
- 对比请求体/响应体/状态码

**示例输出**：
```
⚠️ 接口签名漂移:
   Spec  response: { token: string, expires_in: number }
   Code  response: { accessToken: string, refreshToken: string, expiresAt: number }
   差异: 字段名不同(token→accessToken)，新增 refreshToken 字段
   建议: 更新 spec 或统一代码返回格式
```

### 类型 3：技术约束漂移

**症状**：spec 要求"密码必须 bcrypt 加密"，但代码实际用了 argon2。

**危害**：AI 新写代码时按 spec 用 bcrypt，但现有代码用 argon2，导致加密方式不一致。

**检测方法**：
- 读取 spec 中的 Constraints
- 扫描代码中对应的技术实现
- 对比是否一致

**示例输出**：
```
⚠️ 技术约束漂移:
   Spec  requires: "密码必须 bcrypt 加密，cost factor = 12"
   Code  uses:     argon2 (src/utils/crypto.js:15)
   建议: 更新 spec 为 argon2，或统一代码为 bcrypt
```

### 类型 4：AGENTS.md 过时

**症状**：AGENTS.md 说"技术栈：React 17"，但代码库已经升级到 React 18。

**危害**：AI 按 AGENTS.md 写代码时，用了 React 17 的 API，在 React 18 中已废弃。

**检测方法**：
- 读取 AGENTS.md 中的技术栈约束
- 扫描 `package.json` / `pyproject.toml` 等配置文件
- 对比版本号

**示例输出**：
```
⚠️ AGENTS.md 过时:
   AGENTS.md says: "前端框架: React 17.x"
   package.json:   "react": "^18.2.0"
   建议: 更新 AGENTS.md 为 React 18.x
```

### 类型 5：依赖版本漂移

**症状**：spec 要求 `jsonwebtoken@9.x`，但 `package.json` 里已经是 `jsonwebtoken@9.5.x`，且 spec 没更新。

**危害**：通常无害，但可能隐藏版本兼容性问题。

**检测方法**：
- 读取 spec 中的依赖约束
- 扫描 `package.json` / `requirements.txt`
- 对比版本号

## 输出格式

```
📋 Spec 漂移检测报告
========================
生成时间: 2026-05-04
扫描范围: AGENTS.md + specs/*.md vs ./src

[🔴 严重] Non-Goals 漂移: 1 处
  - OAuth 已从 Non-Goals 移除但在代码中实现
    文件: src/routes/oauth.js
    建议: 更新 AGENTS.md，将 OAuth 标记为"已实现"

[🟡 警告] 接口签名漂移: 2 处
  - POST /api/v1/auth/login 响应字段名不同
    spec: token, expires_in
    code: accessToken, refreshToken, expiresAt
    建议: 统一字段名

[🟡 警告] 技术约束漂移: 1 处
  - 加密方式: spec(bcrypt) vs code(argon2)
    建议: 更新 spec 或统一代码

[🟢 正常] AGENTS.md 技术栈: 全部一致
[🟢 正常] 依赖版本: 全部一致

========================
严重: 1 / 警告: 3 / 正常: 2
建议操作: 先修复严重项，再处理警告项
```

## 修复流程

### Step 1：评估影响

对每个漂移项，判断：
- **是否影响当前开发？** → 如果是，立即修复
- **是否影响 AI 执行？** → 如果是，在下次执行前修复
- **是否只是记录不一致？** → 可以延后，但要在 1 周内修复

### Step 2：决定修复方向

**选项 A：更新 spec（推荐，如果代码已稳定）**
- spec 服从代码，更新文档反映现状
- 适用于：Non-Goals 已实现、AGENTS.md 技术栈过时

**选项 B：修复代码（如果 spec 是正确的）**
- 代码服从 spec，重构代码匹配规范
- 适用于：接口签名不一致（spec 是对的）、技术约束被违反

**选项 C：接受漂移（需记录原因）**
- 在 spec 中添加注释说明为什么不同
- 适用于：故意的设计变更，但文档还没跟上

### Step 3：更新并验证

修复后，重新运行 `detect-spec-drift.py` 确认无漂移。

## 与 check-code-consistency.py 的区别

| 维度 | check-code-consistency.py | detect-spec-drift.py |
|------|---------------------------|----------------------|
| **运行时机** | 执行前（预防） | 执行后/定期（发现） |
| **检查方向** | spec → 代码（spec 是否符合代码现状） | 代码 → spec（代码是否超出 spec 范围） |
| **核心问题** | "spec 是否合理？" | "spec 是否还反映真相？" |
| **输出** | 冲突/警告（阻止执行） | 漂移项（建议修复） |

## 最佳实践

1. **每周运行一次**：把漂移检测纳入例行工作流
2. **发布前必跑**：确保发布版本的 spec 是准确的
3. **CI 集成**：把 `detect-spec-drift.py` 加入 CI pipeline，漂移时告警
4. **spec 变更留痕**：每次更新 spec 时，在变更记录中写明原因
5. **AGENTS.md 月度回顾**：至少每月检查一次 AGENTS.md 是否还适用
