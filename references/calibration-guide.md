# 漂移检测校准指南

> **为什么需要校准？**
> drift detection 的权重机制是一个**启发式系统**——它的阈值和权重是基于通用项目经验设定的。你的项目可能有特殊的目录结构、命名习惯或代码风格，导致误报或漏报。校准的目的是让检测更贴合你的代码库真相。

---

## 1. DRIFT_THRESHOLD 总阈值

当前默认值：`2.0`

### 阈值含义

权重 = 文件类型权重 × 代码特征权重

| 权重范围 | 含义 |
|----------|------|
| < 2.0 | 视为**偶然提及**，不报警 |
| ≥ 2.0 | 视为**实质性证据**，报告漂移 |

### 何时调整

| 场景 | 建议阈值 | 原因 |
|------|----------|------|
| 小型项目（< 10 个路由文件） | `1.5` | 文件少，每个文件的权重影响大，降低阈值避免漏报 |
| 大型项目（> 100 个文件，Monorepo） | `2.5` | 文件多，偶然提及的概率高，提高阈值减少误报 |
| 高敏感项目（金融/医疗） | `1.5` | 范围蔓延成本高，宁可误报也不漏报 |
| 快速迭代项目（MVP 阶段） | `2.5` | 允许一定灵活性，减少噪声 |

### 调整方法

```bash
# 临时调整（单次运行）
python detect-spec-drift.py --spec AGENTS.md --code-dir ./src --threshold 1.5

# 持久化：在项目根目录创建 .sddrc
```json
{
  "drift_threshold": 1.5,
  "file_type_weights": {
    "route": 3.0,
    "model": 2.5
  }
}
```
```

---

## 2. FILE_TYPE_WEIGHTS 文件类型权重

当前默认值：

```python
FILE_TYPE_WEIGHTS = {
    "route": 3.0,      # routes/, controllers/, handlers/, api/
    "model": 2.5,      # models/, entities/, schemas/
    "service": 2.0,    # services/, business/, usecases/
    "config": 1.5,     # config/, settings/
    "middleware": 2.0, # middleware/, guards/
    "util": 0.5,       # utils/, helpers/, lib/
    "test": 0.3,       # tests/, __tests__/, test/
    "doc": 0.1,        # README, docs, 注释
}
```

### 何时调整

**场景 A：你的项目没有标准的 MVC 结构**

比如你的项目把所有逻辑放在 `src/handlers/` 里（既是路由又是服务）：

```python
# 建议：把 handlers 的权重从 route 调整为介于两者之间
FILE_TYPE_WEIGHTS["route"] = 2.5      # 原 3.0
FILE_TYPE_WEIGHTS["handler"] = 2.0    # 新增分类
```

**场景 B：你的项目大量使用工具函数实现业务逻辑**

比如你在 `src/utils/` 里放了大量核心算法：

```python
# 建议：提高 util 的权重
FILE_TYPE_WEIGHTS["util"] = 1.5       # 原 0.5
```

**场景 C：Monorepo，有 packages/ 目录**

```python
# 建议：增加 package 分类
FILE_TYPE_WEIGHTS["package"] = 2.0    # packages/ 下的子项目
```

### 目录映射扩展

如果项目有特殊目录名，编辑 `classify_file()` 函数：

```python
# 当前支持的目录关键词
def classify_file(filepath):
    path_lower = str(filepath).lower()
    for ftype, keywords in [
        ("route", ["route", "controller", "handler", "endpoint", "api"]),
        ("model", ["model", "entity", "schema", "domain"]),
        # ...
    ]:
        if any(kw in path_lower for kw in keywords):
            return ftype
    return "other"
```

**示例：添加你的自定义目录**

```python
("adapter", ["adapter", "port", "driven"]),      # 六边形架构
("command", ["command", "cqrs"]),                # CQRS
("repository", ["repository", "dao"]),           # 仓储模式
```

---

## 3. CODE_FEATURE_WEIGHTS 代码特征权重

当前默认值：

```python
CODE_FEATURE_WEIGHTS = {
    "route_definition": 2.0,    # .get('/path'), router.post()
    "model_definition": 1.5,    # class User:, new Schema()
    "function_export": 1.0,     # export function, def login()
    "import_statement": 0.5,    # import oauth, require('passport')
    "text_mention": 0.2,        # 纯文本提及
    "comment_only": 0.0,        # 仅在注释中出现
}
```

### 何时调整

**场景 A：项目中大量使用装饰器模式**

比如 Python 的 `@app.route()` 或 NestJS 的 `@Controller()`：

```python
# 当前 route_definition 的正则可能匹配不到装饰器
# 建议扩展匹配逻辑或提高相关特征的权重
```

**场景 B：你的项目使用函数式编程，没有 class/struct**

```python
# model_definition 的权重可能失效
# 建议：为函数式项目增加 "type_definition" 特征
CODE_FEATURE_WEIGHTS["type_definition"] = 1.5   # TypeScript type/interface
```

**场景 C：项目大量使用配置文件（YAML/JSON）定义行为**

```python
# 当前特征权重对配置文件不敏感
# 建议：增加 "config_definition" 特征
CODE_FEATURE_WEIGHTS["config_definition"] = 1.0  # openapi.yml, routes.json
```

---

## 4. 校准流程（推荐）

### 第一步：基线测量

```bash
# 1. 在默认阈值下运行，记录结果
python detect-spec-drift.py --spec AGENTS.md --code-dir ./src --json > drift-baseline.json

# 2. 人工审查结果，标记哪些是误报、哪些是漏报
# 误报 = spec 没漂移但报告了
# 漏报 = spec 漂移了但没报告
```

### 第二步：分类问题

| 问题类型 | 根因 | 调整方向 |
|----------|------|----------|
| 大量误报 | 阈值太低 | 提高 DRIFT_THRESHOLD |
| 某个目录频繁误报 | 目录权重不对 | 调整 FILE_TYPE_WEIGHTS |
| 某种代码模式被忽略 | 特征权重不对 | 调整 CODE_FEATURE_WEIGHTS |
| 合法引用被当作漂移 | 注释/导入权重太高 | 降低 import_statement/text_mention |

### 第三步：小步调整

一次只调一个参数，重新运行，对比结果。

```bash
# 调整前备份
cp detect-spec-drift.py detect-spec-drift.py.bak

# 编辑阈值 → 运行 → 记录 → 重复
```

### 第四步：固化配置

校准完成后，将参数写入项目级配置文件：

```bash
# 创建项目级配置
cat > .sddrc << 'EOF'
{
  "project": "my-project",
  "calibrated_at": "2026-05-04",
  "drift_threshold": 2.5,
  "notes": "Monorepo结构，降低util权重避免误报"
}
EOF
```

---

## 5. 常见项目类型的推荐配置

### 小型 Express.js 项目（< 20 个文件）

```python
DRIFT_THRESHOLD = 1.5
FILE_TYPE_WEIGHTS["route"] = 2.5    # 文件少，route证据更珍贵
```

### 大型 NestJS Monorepo（> 200 个文件）

```python
DRIFT_THRESHOLD = 2.5
FILE_TYPE_WEIGHTS["util"] = 0.3     # 工具函数多，降低避免噪声
FILE_TYPE_WEIGHTS["test"] = 0.2     # 测试文件多
```

### Python FastAPI + SQLAlchemy 项目

```python
# FastAPI 使用装饰器定义路由
# 确保 route_definition 正则能匹配 @app.get("/path")
# 当前已支持 @app.route 模式，无需调整
```

### Go 微服务项目

```python
# Go 项目通常没有 models/ 目录，模型和 handler 在一起
# 建议：降低 model 权重，提高 handler（route）权重
FILE_TYPE_WEIGHTS["model"] = 1.5
FILE_TYPE_WEIGHTS["route"] = 3.5
```

---

## 6. 验证校准效果

校准后，用以下 checklist 验证：

- [ ] 已知已漂移的代码能被检测出来（召回率）
- [ ] 未漂移的代码不产生误报（精确率）
- [ ] 同一份代码运行 3 次，结果一致（稳定性）
- [ ] 新增一个 Non-Goal 后，检测能发现对应的漂移（灵敏度）

**目标**：精确率 > 80%，召回率 > 90%。如果达不到，继续微调。
