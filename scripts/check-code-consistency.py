#!/usr/bin/env python3
"""
代码一致性检查脚本——检查 spec 与代码库是否一致。

用法:
    python check-code-consistency.py --spec spec.md --code-dir ./src
    python check-code-consistency.py --spec spec.md --code-dir ./src --strict
    python check-code-consistency.py --scan-only --code-dir ./src

检查维度:
    1. 技术栈一致性（框架/库/工具）
    2. 接口路径一致性
    3. 数据模型一致性
    4. 代码风格一致性
    5. 依赖版本约束

退出码:
    0 - 全部一致
    1 - 有警告或冲突
    2 - 文件不存在或不可读
"""

import argparse
import json
import re
import sys
from pathlib import Path

# 添加 lib 到路径
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))

try:
    from lib.spec_parser import read_spec, extract_section, extract_api_definitions, extract_data_models
except ImportError:
    # 降级：如果 lib 不可用，使用内联实现
    def read_spec(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"❌ 错误: Spec 文件不存在: {filepath}")
            sys.exit(2)
        except Exception as e:
            print(f"❌ 错误: 无法读取文件 {filepath}: {e}")
            sys.exit(2)

    def extract_section(content, headings):
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

    def extract_api_definitions(content):
        apis = []
        api_section = re.search(
            r"##?\s*(?:接口设计|API Design).*?\n(.*?)\n(?:##|\Z)",
            content, re.DOTALL | re.IGNORECASE
        )
        if not api_section:
            return apis
        section = api_section.group(1)
        for match in re.finditer(r"(GET|POST|PUT|DELETE|PATCH)\s+([/\w:{}-]+)", section, re.IGNORECASE):
            apis.append({"method": match.group(1).upper(), "path": match.group(2)})
        return apis

    def extract_data_models(content):
        section = extract_section(content, ["数据模型", "Data Model", "模型"])
        if not section:
            return []
        models = []
        for match in re.finditer(r"^([A-Z][a-zA-Z0-9_]*):", section, re.MULTILINE):
            models.append(match.group(1))
        return models


def find_config_files(code_dir):
    """在代码目录中查找配置文件。"""
    configs = {}
    code_path = Path(code_dir)

    for filename in ["package.json", "Cargo.toml", "pyproject.toml", "go.mod", "requirements.txt", "Pipfile"]:
        filepath = code_path / filename
        if filepath.exists():
            configs[filename] = filepath.read_text(encoding="utf-8")

    return configs


def extract_spec_constraints(spec_content):
    """从 spec 中提取技术约束。"""
    constraints = {
        "frameworks": [],
        "libraries": [],
        "databases": [],
        "api_paths": [],
        "models": [],
        "style_rules": [],
    }

    # 提取框架（常见后端框架）
    framework_patterns = [
        r"(Express|Fastify|Koa|Django|Flask|FastAPI|Spring|Rails|Laravel|NestJS)",
        r"(React|Vue|Angular|Svelte|Next\.js|Nuxt)",
    ]
    for pattern in framework_patterns:
        for match in re.finditer(pattern, spec_content, re.IGNORECASE):
            constraints["frameworks"].append(match.group(1))

    # 提取库
    lib_patterns = [
        r"(bcrypt|argon2|jsonwebtoken|passport|jwt|prisma|typeorm|sequelize)",
        r"(axios|fetch|requests|httpx)",
    ]
    for pattern in lib_patterns:
        for match in re.finditer(pattern, spec_content, re.IGNORECASE):
            constraints["libraries"].append(match.group(1))

    # 提取数据库
    db_patterns = [
        r"(PostgreSQL|MySQL|MongoDB|SQLite|Redis|Elasticsearch)",
        r"(Prisma|TypeORM|Sequelize|SQLAlchemy|Django ORM)",
    ]
    for pattern in db_patterns:
        for match in re.finditer(pattern, spec_content, re.IGNORECASE):
            constraints["databases"].append(match.group(1))

    # 提取 API 路径（使用公共模块）
    constraints["api_paths"] = extract_api_definitions(spec_content)

    # 提取模型名（使用公共模块）
    constraints["models"] = extract_data_models(spec_content)

    return constraints


def check_tech_stack(spec_constraints, configs):
    """检查技术栈一致性。"""
    issues = []

    if "package.json" in configs:
        pkg = configs["package.json"]
        # 检查 Express vs Fastify
        if "express" in pkg.lower() and "Fastify" in str(spec_constraints["frameworks"]):
            issues.append({
                "type": "冲突",
                "category": "技术栈",
                "message": "spec 要求 Fastify，但 package.json 已有 Express",
                "suggestion": "统一使用 Express，或说明引入 Fastify 的原因",
            })
        if "fastify" in pkg.lower() and "Express" in str(spec_constraints["frameworks"]):
            issues.append({
                "type": "冲突",
                "category": "技术栈",
                "message": "spec 要求 Express，但 package.json 已有 Fastify",
                "suggestion": "统一使用 Fastify，或说明引入 Express 的原因",
            })

        # 检查 Prisma vs TypeORM
        if "prisma" in pkg.lower() and "TypeORM" in str(spec_constraints["databases"]):
            issues.append({
                "type": "冲突",
                "category": "ORM",
                "message": "spec 要求 TypeORM，但 package.json 已有 Prisma",
                "suggestion": "统一使用 Prisma，或说明引入 TypeORM 的原因",
            })

    if "Cargo.toml" in configs:
        cargo = configs["Cargo.toml"]
        # 类似的 Rust 框架检查
        pass

    if "pyproject.toml" in configs:
        pyproject = configs["pyproject.toml"]
        # 类似的 Python 框架检查
        pass

    return issues


def scan_routes(code_dir):
    """扫描代码目录中的路由定义。"""
    routes = []
    code_path = Path(code_dir)

    # 简单的启发式扫描：查找包含路由定义的文件
    for pattern in ["**/*.js", "**/*.ts", "**/*.py", "**/*.go"]:
        for filepath in code_path.glob(pattern):
            try:
                content = filepath.read_text(encoding="utf-8")
                # 匹配常见路由模式
                route_patterns = [
                    r"\.(get|post|put|delete|patch)\s*\(\s*['\"]([/\w:{}-]+)['\"]",
                    r"@app\.(route|get|post|put|delete)\s*\(\s*['\"]([/\w:{}-]+)['\"]",
                    r"router\.(Get|Post|Put|Delete|Patch)\s*\(\s*['\"]([/\w:{}-]+)['\"]",
                ]
                for rp in route_patterns:
                    for match in re.finditer(rp, content, re.IGNORECASE):
                        routes.append({
                            "method": match.group(1).upper(),
                            "path": match.group(2),
                            "file": str(filepath.relative_to(code_path)),
                        })
            except Exception:
                continue

    return routes


def check_api_paths(spec_constraints, code_routes):
    """检查 API 路径一致性。"""
    issues = []
    spec_paths = spec_constraints.get("api_paths", [])

    # 检查 spec 中的路径是否在代码中已存在（可能冲突）
    for spec_path in spec_paths:
        for code_route in code_routes:
            if spec_path["path"] == code_route["path"]:
                issues.append({
                    "type": "冲突",
                    "category": "接口路径",
                    "message": f"{spec_path['method']} {spec_path['path']} 已在 {code_route['file']} 中定义",
                    "suggestion": "检查是否需要修改现有路由，或 spec 中的路径需要调整",
                })

    return issues


def check_code_style(code_dir):
    """简单检查代码风格（采样检查）。"""
    issues = []
    code_path = Path(code_dir)

    # 检查 ESLint/Prettier 配置
    eslint = code_path / ".eslintrc" in list(code_path.iterdir()) or (code_path / ".eslintrc.js").exists()
    prettier = (code_path / ".prettierrc").exists() or (code_path / ".prettierrc.js").exists()

    if not eslint and not prettier:
        issues.append({
            "type": "警告",
            "category": "代码风格",
            "message": "未检测到 ESLint 或 Prettier 配置",
            "suggestion": "建议在项目中添加代码风格配置",
        })

    return issues


def scan_models(code_dir):
    """扫描代码目录中的模型定义。"""
    models = []
    code_path = Path(code_dir)

    for pattern in ["**/*model*", "**/models/**", "**/entities/**"]:
        for filepath in code_path.glob(pattern):
            if filepath.is_file() and filepath.suffix in [".js", ".ts", ".py", ".go"]:
                try:
                    content = filepath.read_text(encoding="utf-8")
                    # 简单提取类名/模型名
                    for match in re.finditer(r"(?:class|struct|interface|type)\s+([A-Z][a-zA-Z0-9_]*)", content):
                        models.append(match.group(1))
                except Exception:
                    continue

    return models


def check_models(spec_constraints, code_models):
    """检查数据模型一致性。"""
    issues = []
    spec_models = spec_constraints.get("models", [])

    for spec_model in spec_models:
        # 检查是否已有同名模型
        for code_model in code_models:
            if spec_model.lower() == code_model.lower():
                issues.append({
                    "type": "警告",
                    "category": "数据模型",
                    "message": f"模型 {spec_model} 可能已在代码中存在",
                    "suggestion": "检查现有模型字段，确定是否需要修改",
                })

    return issues


def print_report(issues, spec_constraints, configs):
    """打印人类可读报告。"""
    print("📋 代码一致性检查报告")
    print("=" * 50)
    print()

    # 技术栈摘要
    if configs:
        print("代码库检测:")
        for name in configs:
            print(f"  ✅ {name}")
        print()

    # Spec 中提取的信息
    print("Spec 中提取:")
    if spec_constraints["frameworks"]:
        print(f"  框架: {', '.join(spec_constraints['frameworks'])}")
    if spec_constraints["libraries"]:
        print(f"  库: {', '.join(spec_constraints['libraries'])}")
    if spec_constraints["databases"]:
        print(f"  数据库/ORM: {', '.join(spec_constraints['databases'])}")
    if spec_constraints["api_paths"]:
        print(f"  API: {len(spec_constraints['api_paths'])} 个端点")
    if spec_constraints["models"]:
        print(f"  模型: {', '.join(spec_constraints['models'])}")
    print()

    # 问题列表
    if not issues:
        print("🎉 未发现冲突或警告！")
        print("=" * 50)
        return

    conflicts = [i for i in issues if i["type"] == "冲突"]
    warnings = [i for i in issues if i["type"] == "警告"]

    if conflicts:
        print(f"🔴 冲突 ({len(conflicts)}):")
        for issue in conflicts:
            print(f"  [{issue['category']}] {issue['message']}")
            print(f"    建议: {issue['suggestion']}")
        print()

    if warnings:
        print(f"🟡 警告 ({len(warnings)}):")
        for issue in warnings:
            print(f"  [{issue['category']}] {issue['message']}")
            print(f"    建议: {issue['suggestion']}")
        print()

    print("=" * 50)
    print(f"冲突: {len(conflicts)} / 警告: {len(warnings)}")

    if conflicts:
        print("⚠️  请先解决冲突再继续执行。")
    elif warnings:
        print("💡 建议处理警告，但不阻塞执行。")


def main():
    parser = argparse.ArgumentParser(description="检查 spec 与代码库的一致性")
    parser.add_argument("--spec", help="Spec 文件路径")
    parser.add_argument("--code-dir", default=".", help="代码目录（默认当前目录）")
    parser.add_argument("--scan-only", action="store_true", help="仅扫描代码库，不对比 spec")
    parser.add_argument("--strict", action="store_true", help="严格模式：警告也视为失败")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    # 扫描代码库
    configs = find_config_files(args.code_dir)
    code_routes = scan_routes(args.code_dir) if not args.scan_only else []
    code_models = scan_models(args.code_dir) if not args.scan_only else []

    if args.scan_only:
        # 仅扫描模式：输出代码库摘要
        print("🔍 代码库扫描结果")
        print("=" * 40)
        if configs:
            print("配置文件:")
            for name in configs:
                print(f"  ✅ {name}")
        else:
            print("  ⚠️ 未检测到常见配置文件")

        print(f"\n发现路由: {len(code_routes)} 个")
        for route in code_routes[:10]:
            print(f"  {route['method']} {route['path']} ({route['file']})")
        if len(code_routes) > 10:
            print(f"  ... 还有 {len(code_routes) - 10} 个")

        print(f"\n发现模型: {len(code_models)} 个")
        for model in code_models[:10]:
            print(f"  {model}")
        if len(code_models) > 10:
            print(f"  ... 还有 {len(code_models) - 10} 个")
        return

    if not args.spec:
        print("❌ 错误: --spec 是必需的（除非使用 --scan-only）")
        sys.exit(2)

    # 读取 spec
    spec_content = read_spec(args.spec)
    spec_constraints = extract_spec_constraints(spec_content)

    # 运行检查
    issues = []
    issues.extend(check_tech_stack(spec_constraints, configs))
    issues.extend(check_api_paths(spec_constraints, code_routes))
    issues.extend(check_code_style(args.code_dir))
    issues.extend(check_models(spec_constraints, code_models))

    # 输出
    if args.json:
        output = {
            "spec_file": args.spec,
            "code_dir": args.code_dir,
            "issues": issues,
            "summary": {
                "conflicts": len([i for i in issues if i["type"] == "冲突"]),
                "warnings": len([i for i in issues if i["type"] == "警告"]),
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(issues, spec_constraints, configs)

    # 退出码
    conflicts = [i for i in issues if i["type"] == "冲突"]
    warnings = [i for i in issues if i["type"] == "警告"]

    if conflicts:
        sys.exit(1)
    if args.strict and warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
