# 黄金搭档：OpenSpec + Superpowers

## 为什么叫"黄金搭档"

这是目前社区最推荐的组合：

- **OpenSpec** 负责"做什么"——规划对齐，需求不跑偏
- **Superpowers** 负责"怎么做好"——TDD 强制，代码质量有保证

两者互补，覆盖了 SDD 的两个核心维度：规划 + 执行。

## 完整实战：开发一个登录功能

### 第一步：安装

```bash
# 安装 OpenSpec
npm install -g openspec-cn

# 安装 Superpowers（在 Claude Code 中）
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace

# 重启 Claude Code
```

### 第二步：用 OpenSpec 锁定需求

```bash
cd your-project
openspec init
```

在 Claude Code 中：

```
/opsx:new add-user-login
/opsx:ff
```

`/opsx:ff` 是"快进"命令，会自动生成：
- `proposal.md`（为什么改、改什么）
- `design.md`（技术方案）
- `tasks.md`（任务清单）

**关键步骤**：打开 `proposal.md`，**手动补上"非目标"**那一栏：

```markdown
## 非目标（v1 不做）
- OAuth 第三方登录
- 手机号登录
- 记住我功能
```

**这步很多人会跳过，跳过之后 AI 就会开始"好心办坏事"。**

### 第三步：用 Superpowers 执行开发

```
/superpowers:brainstorm
```

AI 会先问你几个关键问题（密码策略、token 过期时间等）。回答完后：

```
/superpowers:write-plan
```

它会读取 OpenSpec 的 `tasks.md`，生成极细粒度的执行计划——每个任务精确到文件名和函数名，2-5 分钟粒度。

```
/superpowers:execute-plan
```

接下来就是 AI 自动干活：
1. 创建 Git 分支（git worktrees）
2. 写失败测试（TDD）
3. 写实现代码让测试通过
4. 双阶段代码审查
5. 验收，处理分支

### 第四步：归档闭环

```
/opsx:verify    # 检查代码是否符合规范
/opsx:archive   # 合并回主规范库
```

跑完这一套之后：
- 你的代码是 TDD 覆盖的
- 你的代码经过双阶段审查
- 你的项目里有一份完整的、可追溯的开发记录
- 下次新成员接手，打开 `openspec/specs/` 就能知道这套登录是怎么设计的、为什么这么设计

## 组合优势

| 维度 | OpenSpec | Superpowers | 组合效果 |
|------|----------|-------------|---------|
| 规划 | ✅ 增量规范 | ❌ 不管理 | ✅ 需求清晰 |
| 执行 | ❌ 不强制 | ✅ TDD + 审查 | ✅ 质量保证 |
| 可追溯 | ✅ archive 机制 | ❌ 无 | ✅ 历史可查 |
| 自动化 | ⚠️ 半自动 | ✅ 全自动 | ✅ 流程顺畅 |

## 注意事项

1. **必须先补 Non-Goals**：`/opsx:ff` 生成的文档默认没有 Non-Goals，必须手动补
2. **规划会话和执行会话分开**：先用 OpenSpec 规划，再用 Superpowers 执行
3. **archive 不要忘**：很多人做完功能就停了，忘了 archive，导致规范库和代码不同步
4. **Token 成本**：Superpowers 比直接写代码多 10-20% Token，但返工减少 60-70%

## 什么时候不用这个组合

- 单文件 patch（<50 行）→ 直接写代码
- 快速原型验证 → 太重了
- 非 Claude Code 用户 → Superpowers 不支持
- 团队已经有成熟的 CI/CD + Code Review → Superpowers 可能重复
