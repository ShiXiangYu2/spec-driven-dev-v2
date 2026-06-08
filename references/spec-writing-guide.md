# Spec 写作最佳实践

## 好 Spec 的六要素（来自阿里云 SDD 实践）

一份高质量 Spec 应包含以下六个要素：

### 1. Problem Statement（问题陈述）
用 2-3 句话说清楚"当前有什么问题"和"为什么要解决它"。

### 2. Success Metrics（成功指标）
**可测试的量化指标**，例如"搜索 API 响应时间 P95 < 200ms"而非"系统应该很快"。

### 3. User Stories（用户故事）
- 作为 [角色]，我希望 [功能]，以便 [收益]

### 4. Acceptance Criteria（验收标准）
可验证的 checkbox 列表，每条标准都能转化为测试用例。

### 5. Non-Goals（非目标）
明确排除的功能列表。**这是六要素中最容易被敷衍、但对 AI 最有效的约束。**

### 6. Constraints（约束）
技术、业务、合规方面的硬性限制。

> **好 Spec vs 坏 Spec 的本质差异：好 Spec 是可测试的，坏 Spec 是可解释的。**
> "系统应该很快"给了 AI 无限的解释空间；"P95 < 200ms" 则是硬约束。

---

## 粒度检验标准（Spec Granularity Test）

来自 Spec Kit 社区的经典检验方法：

> **"用不同技术栈实现这个 Spec，Spec 是否仍然有效？"**

- 如果你的 Spec 写了"使用 Redis 的 ZSET 结构存储排行榜"，那它只对 Redis 方案有效——换成 PostgreSQL 实现就失效了。**这说明你把 HOW 混进了 WHAT。**
- 如果你的 Spec 写了"排行榜需支持实时更新，延迟不超过 1 秒，支持 Top-100 查询"，那无论底层用 Redis、PostgreSQL 还是自研存储，这个 Spec 都成立。**这才是正确的粒度。**

**例外**：Constraints 部分可以出现技术约束——但那是"外部限制"（如"必须使用现有 PostgreSQL 实例"），不是"实现方案"。

---

## 好 Spec 的标准

一个好 spec 应该满足以下标准：

1. **具体可测试**：每个 What 都能写出测试用例
2. **边界清晰**：Constraints 和 Non-Goals 明确划定范围
3. **动机充分**：Why 让所有人理解为什么要做这个功能
4. **粒度适中**：任务拆解到 2-5 分钟粒度，不要太粗也不要太细

## 常见错误

### 错误 1：What 太模糊

❌ **错误示例**：
```markdown
## What
实现用户登录功能
```

✅ **正确示例**：
```markdown
## What
用户可以用邮箱+密码登录：
- 邮箱格式验证（符合 RFC 5322）
- 密码长度 8-64 字符
- 登录成功返回 JWT token（有效期 7 天）
- 连续 5 次失败锁定账户 15 分钟
```

### 错误 2：Non-Goals 缺失或敷衍

❌ **错误示例**：
```markdown
## Non-Goals
- 暂时不做高级功能
```

✅ **正确示例**：
```markdown
## Non-Goals（v1 不做）
- OAuth 第三方登录（Google/GitHub/微信）
- 手机号 + 验证码登录
- "记住我"功能
- 登录日志 / 审计功能
- 多设备登录管理
```

### 错误 3：Constraints 太抽象

❌ **错误示例**：
```markdown
## Constraints
- 代码要高质量
- 性能要好
```

✅ **正确示例**：
```markdown
## Constraints
- 密码必须 bcrypt 加密，cost factor = 12
- JWT token 有效期 7 天，refresh token 30 天
- API 响应时间 P99 < 200ms
- 单元测试覆盖率 ≥ 80%
```

### 错误 4：任务拆解太粗

❌ **错误示例**：
```markdown
## Tasks
- [ ] 实现登录功能
- [ ] 写测试
```

✅ **正确示例**：
```markdown
## Tasks
- [ ] 创建 User 模型（email, password_hash, failed_attempts）
- [ ] 实现 bcrypt 密码哈希工具函数
- [ ] 实现 POST /api/v1/auth/login 接口
- [ ] 实现邮箱格式验证中间件
- [ ] 实现登录失败计数和锁定逻辑
- [ ] 实现 JWT token 生成和验证
- [ ] 写单元测试：密码正确时返回 token
- [ ] 写单元测试：密码错误时返回 401
- [ ] 写单元测试：连续 5 次失败后锁定
- [ ] 写集成测试：完整登录流程
```

## Spec 模板选择指南

| 场景 | 模板 | 输出路径 |
|------|------|----------|
| 全新项目启动 | `assets/project-spec-template.md` | `AGENTS.md` 或 `docs/CONSTITUTION.md` |
| 已有项目加功能 | `assets/feature-spec-template.md` | `specs/功能名.md` |
| 代码重构 | `assets/change-spec-template.md` | `specs/变更名.md` |
| 快速启动 | `assets/agents-md-template.md` | `AGENTS.md` |

## Spec 维护

Spec 不是写一次就扔的文档：

1. **每次需求变更时更新 spec**
2. **每周回顾一次 AGENTS.md**，更新过时约束
3. **Spec 进 git**：把 spec 文件加入版本控制
4. **重大变更保留历史版本**：`spec-v1.md` → `spec-v2.md`

## AI 读取 Spec 的技巧

执行会话开始时，让 AI 读取 spec 文件：

```
请先阅读以下文件，了解本功能的规范：
1. AGENTS.md（项目级约束）
2. specs/user-login.md（功能级规范）

确认理解后，开始按规范实现代码。
```

这比在 prompt 里粘贴 spec 内容更高效，因为：
- AI 可以自己 Read 文件，不需要你手动粘贴
- 文件内容不受 prompt 长度限制
- 多个 AI 会话可以共享同一份 spec
