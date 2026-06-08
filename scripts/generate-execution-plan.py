#!/usr/bin/env python3
"""
从 Spec 生成执行计划。

用法:
    python generate-execution-plan.py --spec spec.md --output plan.md
    python generate-execution-plan.py --spec spec.md --output plan.md --code-dir ./src

功能:
    1. 读取 spec 中的接口设计、数据模型、任务拆解
    2. 扫描代码目录结构，推断真实文件路径
    3. 按依赖排序任务
    4. 生成执行计划 Markdown 文件

示例:
    # 基本用法（无代码目录，使用占位符路径）
    python generate-execution-plan.py --spec specs/login.md --output plans/login-plan.md

    # 扫描现有代码目录，推断真实文件路径
    python generate-execution-plan.py --spec specs/login.md --output plans/login-plan.md --code-dir ./src

    # 指定功能名（用于生成文件名）
    python generate-execution-plan.py --spec specs/login.md --output plans/login-plan.md --code-dir ./src --feature auth
"""

import argparse
import re
import sys
from pathlib import Path


# ── 目录映射表：文件类型 → 常见目录名（按优先级排序） ──
DIR_MAP = {
    "route": ["routes", "controllers", "handlers", "api", "endpoints", "routers"],
    "model": ["models", "entities", "schemas", "domain", "db"],
    "service": ["services", "business", "usecases", "core", "logic"],
    "util": ["utils", "helpers", "lib", "common", "shared"],
    "middleware": ["middleware", "middlewares", "plugins", "guards", "interceptors"],
    "test": ["tests", "__tests__", "test", "spec", "e2e", "integration"],
    "config": ["config", "configs", "settings", "env"],
}


def read_spec(filepath):
    """读取 spec 文件内容。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ 错误: Spec 文件不存在: {filepath}")
        sys.exit(2)
    except Exception as e:
        print(f"❌ 错误: 无法读取文件: {e}")
        sys.exit(2)


def extract_section(content, headings):
    """提取指定标题下的内容。"""
    for heading in headings:
        pattern = rf"(?:^|\n)##?\s*{re.escape(heading)}\s*\n"
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            start = match.end()
            next_header = re.search(r"\n##?\s", content[start:])
            if next_header:
                return content[start:start + next_header.start()].strip()
            return content[start:].strip()
    return ""


def scan_project_structure(code_dir):
    """扫描代码目录结构，找到常见的目录模式。"""
    if not code_dir:
        return {}

    code_path = Path(code_dir)
    if not code_path.exists():
        return {}

    found_dirs = {}
    for subdir in code_path.rglob("*"):
        if subdir.is_dir() and not any(part.startswith(".") for part in subdir.parts):
            dir_name = subdir.name.lower()
            for file_type, candidates in DIR_MAP.items():
                if dir_name in candidates:
                    if file_type not in found_dirs:
                        found_dirs[file_type] = []
                    # 保存相对路径
                    rel = subdir.relative_to(code_path)
                    if str(rel) not in found_dirs[file_type]:
                        found_dirs[file_type].append(str(rel))

    return found_dirs


def infer_file_path(file_type, code_dir, feature_name, default_template):
    """根据项目结构推断文件路径。"""
    found_dirs = scan_project_structure(code_dir)

    if file_type in found_dirs and found_dirs[file_type]:
        # 使用找到的第一个匹配目录
        base_dir = found_dirs[file_type][0]
        ext = ".js"  # 默认扩展名

        # 尝试推断扩展名
        code_path = Path(code_dir)
        if code_path.exists():
            for ext_candidate in [".ts", ".tsx", ".jsx", ".py", ".go", ".rs"]:
                sample_files = list(code_path.rglob(f"*{ext_candidate}"))
                if sample_files:
                    ext = ext_candidate
                    break

        return f"{base_dir}/{feature_name}{ext}"

    # 回退到默认模板
    return default_template


def extract_api_endpoints(spec_content):
    """从接口设计章节提取 API 端点。"""
    section = extract_section(spec_content, ["接口设计", "API Design", "API 设计"])
    if not section:
        return []

    endpoints = []
    patterns = [
        r"(GET|POST|PUT|DELETE|PATCH)\s+([/\w:{}-]+)",
        r"```\s*\n(GET|POST|PUT|DELETE|PATCH)\s+([/\w:{}-]+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, section, re.IGNORECASE):
            method = match.group(1).upper()
            path = match.group(2)
            endpoints.append({"method": method, "path": path})

    return endpoints


def extract_data_models(spec_content):
    """从数据模型章节提取模型名。"""
    section = extract_section(spec_content, ["数据模型", "Data Model", "模型"])
    if not section:
        return []

    models = []
    for match in re.finditer(r"^([A-Z][a-zA-Z0-9_]*):", section, re.MULTILINE):
        models.append(match.group(1))

    return models


def extract_tasks(spec_content):
    """从任务拆解章节提取任务列表。"""
    section = extract_section(spec_content, ["任务拆解", "Task Breakdown", "任务"])
    if not section:
        return []

    tasks = []
    for match in re.finditer(r"^[-*]\s*(?:\[\s*\]\s*)?(.*?)$", section, re.MULTILINE):
        task_text = match.group(1).strip()
        if task_text and not task_text.startswith("placeholder"):
            tasks.append(task_text)

    return tasks


def infer_files_from_spec(spec_content, endpoints, models, tasks, code_dir=None, feature_name="feature"):
    """根据 spec 推断文件变更清单，优先使用代码目录结构。"""
    files = []
    file_counter = 1

    # 从数据模型推断模型文件
    for model in models:
        path = infer_file_path("model", code_dir, model, f"src/models/{model}.js") if code_dir else f"src/models/{model}.js"
        files.append({
            "num": file_counter,
            "path": path,
            "action": "新增",
            "desc": f"{model} 模型定义",
            "deps": [],
        })
        file_counter += 1

    # 从接口推断路由文件
    if endpoints:
        path = infer_file_path("route", code_dir, feature_name, f"src/routes/{feature_name}.js") if code_dir else f"src/routes/[{feature_name}].js"
        files.append({
            "num": file_counter,
            "path": path,
            "action": "新增",
            "desc": f"API 路由（{len(endpoints)} 个端点）",
            "deps": list(range(1, file_counter)),
        })
        file_counter += 1

    # 从任务推断其他文件
    for task in tasks:
        lower_task = task.lower()
        if "test" in lower_task or "测试" in lower_task:
            path = infer_file_path("test", code_dir, feature_name, f"tests/{feature_name}.test.js") if code_dir else f"tests/[{feature_name}].test.js"
            files.append({
                "num": file_counter,
                "path": path,
                "action": "新增",
                "desc": task,
                "deps": [file_counter - 1] if file_counter > 1 else [],
            })
            file_counter += 1
        elif "util" in lower_task or "工具" in lower_task:
            path = infer_file_path("util", code_dir, feature_name, f"src/utils/{feature_name}.js") if code_dir else f"src/utils/[{feature_name}].js"
            files.append({
                "num": file_counter,
                "path": path,
                "action": "新增",
                "desc": task,
                "deps": [],
            })
            file_counter += 1
        elif "middleware" in lower_task or "中间件" in lower_task:
            path = infer_file_path("middleware", code_dir, feature_name, f"src/middleware/{feature_name}.js") if code_dir else f"src/middleware/[{feature_name}].js"
            files.append({
                "num": file_counter,
                "path": path,
                "action": "新增",
                "desc": task,
                "deps": [],
            })
            file_counter += 1
        elif "service" in lower_task or "服务" in lower_task or "业务逻辑" in lower_task:
            path = infer_file_path("service", code_dir, feature_name, f"src/services/{feature_name}.js") if code_dir else f"src/services/[{feature_name}].js"
            files.append({
                "num": file_counter,
                "path": path,
                "action": "新增",
                "desc": task,
                "deps": [],
            })
            file_counter += 1

    return files


def generate_plan(spec_content, spec_path, code_dir=None, feature_name="feature"):
    """生成执行计划内容。"""
    endpoints = extract_api_endpoints(spec_content)
    models = extract_data_models(spec_content)
    tasks = extract_tasks(spec_content)

    files = infer_files_from_spec(spec_content, endpoints, models, tasks, code_dir, feature_name)

    if not files:
        files = [
            {"num": 1, "path": "src/models/[Model].js", "action": "新增", "desc": "数据模型", "deps": []},
            {"num": 2, "path": "src/routes/[feature].js", "action": "新增", "desc": "路由/控制器", "deps": [1]},
            {"num": 3, "path": "tests/[feature].test.js", "action": "新增", "desc": "测试文件", "deps": [2]},
        ]

    if not tasks:
        tasks = [
            "创建数据模型",
            "实现核心逻辑",
            "实现接口/路由",
            "写单元测试",
            "写集成测试",
        ]

    spec_name = Path(spec_path).stem

    # 检测是否使用了代码目录推断
    structure_note = ""
    if code_dir:
        found_dirs = scan_project_structure(code_dir)
        if found_dirs:
            dirs_summary = ", ".join(f"{k}: {', '.join(v[:2])}" for k, v in found_dirs.items())
            structure_note = f"\n> 基于代码目录结构推断：{dirs_summary}\n"
        else:
            structure_note = "\n> ⚠️ 未在代码目录中检测到常见目录结构，使用默认路径\n"

    plan = f"""# 执行计划：{spec_name}

> 生成自：{spec_path}
> 生成日期：自动生成
> 版本：v1.0{structure_note}

---

## 1. 环境准备

```bash
# 安装新依赖（根据 spec 的 Constraints 推断）
# npm install [依赖1] [依赖2]
# pip install [依赖1] [依赖2]

# 数据库迁移（如需要）
# npx prisma migrate dev --name [迁移名]
```

---

## 2. 文件变更清单

| # | 文件 | 操作 | 说明 | 依赖 |
|---|------|------|------|------|
"""

    for f in files:
        deps_str = "无" if not f["deps"] else ", ".join(f"#{d}" for d in f["deps"])
        plan += f"| {f['num']} | `{f['path']}` | {f['action']} | {f['desc']} | {deps_str} |\n"

    plan += """
---

## 3. 任务执行顺序

**Phase 1：基础设施（可并行）**
"""

    phase1_tasks = [t for t in tasks if any(kw in t.lower() for kw in ["模型", "工具", "util", "中间件", "middleware", "配置", "config"])]
    if not phase1_tasks:
        phase1_tasks = tasks[:max(1, len(tasks) // 3)]

    for t in phase1_tasks:
        plan += f"- [ ] {t}\n"

    plan += """
**Phase 2：核心功能（依赖 Phase 1）**
"""
    phase2_tasks = [t for t in tasks if t not in phase1_tasks]
    core_tasks = [t for t in phase2_tasks if not any(kw in t.lower() for kw in ["test", "测试", "验证", "验收"])]
    test_tasks = [t for t in phase2_tasks if any(kw in t.lower() for kw in ["test", "测试", "验证", "验收"])]

    if not core_tasks:
        core_tasks = phase2_tasks[:max(1, len(phase2_tasks) // 2)]
        test_tasks = [t for t in phase2_tasks if t not in core_tasks]

    for t in core_tasks:
        plan += f"- [ ] {t}\n"

    plan += """
**Phase 3：验证（依赖 Phase 2）**
"""
    for t in test_tasks:
        plan += f"- [ ] {t}\n"

    plan += f"""
---

## 4. 验证点

- **Phase 1 验证**：基础设施可正常导入/初始化
- **Phase 2 验证**：核心功能按 spec 的验收标准通过
- **Phase 3 验证**：测试覆盖率达标，所有测试通过

---

## 5. 会话切换指南

**执行会话开始时，让 AI 读取以下文件**：
1. `AGENTS.md`（项目级约束）
2. `{spec_path}`（功能级规范）
3. 本执行计划文件

**执行会话的标准 prompt**：
```
请按以下顺序执行：
1. 读取 AGENTS.md + {spec_name}.md + 执行计划
2. 从 Phase 1 开始执行
3. 每完成一个 Phase，汇报进度并等待确认
4. 严格执行 Non-Goals，不实现范围外的功能
5. 所有代码必须通过测试
```

---

## 6. Spec 变更回流机制

> 执行过程中如果发现 spec 不合理，按以下流程处理：

**发现 spec 问题 → 暂停执行 → 更新 spec → 重新生成执行计划 → 继续执行**

具体步骤：
1. **暂停**：在当前 Phase 完成后暂停，不要中途停止
2. **标记**：在执行计划中记录问题（"发现 spec 遗漏：..."）
3. **更新**：修改 spec 文件，补充遗漏或修正错误
4. **重新生成**：运行 `generate-execution-plan.py` 重新生成执行计划
5. **继续**：从下一个 Phase 继续执行

**重要**：不要让新需求偷偷溜进当前范围。如果是新需求，先更新 spec 的 Non-Goals，再决定是否纳入。

---

## 7. 风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|---------|
| 实现过程中发现 spec 遗漏 | 中 | 中 | 按"Spec 变更回流机制"处理 |
| 与现有代码冲突 | 中 | 高 | 先运行 check-code-consistency.py 确认 |
| 依赖安装失败 | 低 | 中 | 检查网络/镜像源，尝试替代依赖 |
| 推断的文件路径与实际不符 | 中 | 低 | 手动调整执行计划中的路径 |

---

> ⚠️ **注意**：这是自动生成的执行计划。请根据项目实际情况检查和调整文件路径、依赖关系和任务顺序。
"""

    return plan


def main():
    parser = argparse.ArgumentParser(
        description="从 Spec 生成执行计划",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法（无代码目录，使用占位符路径）
  python generate-execution-plan.py --spec specs/login.md --output plans/login-plan.md

  # 扫描现有代码目录，推断真实文件路径
  python generate-execution-plan.py --spec specs/login.md --output plans/login-plan.md --code-dir ./src

  # 指定功能名（用于生成文件名）
  python generate-execution-plan.py --spec specs/login.md --output plans/login-plan.md --code-dir ./src --feature auth
        """
    )
    parser.add_argument("--spec", required=True, help="Spec 文件路径")
    parser.add_argument("--output", required=True, help="输出文件路径")
    parser.add_argument("--code-dir", help="代码目录（用于扫描目录结构、推断真实文件路径）")
    parser.add_argument("--feature", default="feature", help="功能名（用于生成文件名，默认从 spec 文件名推断）")
    args = parser.parse_args()

    spec_content = read_spec(args.spec)

    # 从 spec 文件名推断 feature 名
    feature_name = args.feature
    if feature_name == "feature":
        feature_name = Path(args.spec).stem

    plan = generate_plan(spec_content, args.spec, args.code_dir, feature_name)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(plan)

    # 统计信息
    file_count = len([l for l in plan.split("\n") if "|" in l and "新增" in l])
    print(f"✓ 执行计划已生成: {output_path}")
    print(f"  推断文件: {file_count} 个")
    if args.code_dir:
        found_dirs = scan_project_structure(args.code_dir)
        if found_dirs:
            print(f"  检测到目录结构: {', '.join(found_dirs.keys())}")
        else:
            print(f"  ⚠️ 未在 {args.code_dir} 中检测到常见目录结构")
    print(f"  请检查文件路径是否与项目结构匹配")


if __name__ == "__main__":
    main()
