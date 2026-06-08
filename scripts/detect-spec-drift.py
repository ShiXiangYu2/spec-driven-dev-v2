#!/usr/bin/env python3
"""
Spec 漂移检测脚本——检测 spec 是否还反映代码的当前真相。

用法:
    python detect-spec-drift.py --spec AGENTS.md --code-dir ./src
    python detect-spec-drift.py --spec specs/feature.md --code-dir ./src
    python detect-spec-drift.py --spec AGENTS.md --code-dir ./src --json

检测类型:
    1. Non-Goals 漂移（范围蔓延）——带权重机制降低误报
    2. 接口签名漂移
    3. 技术约束漂移
    4. AGENTS.md 过时
    5. 依赖版本漂移

退出码:
    0 - 无漂移
    1 - 有漂移
    2 - 文件不存在或不可读

示例:
    # 基础检测
    python detect-spec-drift.py --spec AGENTS.md --code-dir ./src

    # JSON 输出（用于 CI 集成）
    python detect-spec-drift.py --spec AGENTS.md --code-dir ./src --json

    # 只检测 Non-Goals 漂移
    python detect-spec-drift.py --spec AGENTS.md --code-dir ./src --skip-api --skip-tech
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
    from lib.spec_parser import (
        read_file,
        read_spec,
        extract_section,
        extract_non_goals,
        extract_api_definitions,
        extract_tech_stack,
        extract_data_models,
    )
except ImportError:
    # 降级：如果 lib 不可用，使用内联实现
    def read_file(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except (FileNotFoundError, Exception):
            return None

    def read_spec(filepath):
        content = read_file(filepath)
        if content is None:
            print(f"❌ 错误: Spec 文件不存在: {filepath}")
            sys.exit(2)
        return content

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

    def extract_non_goals(content):
        patterns = [
            r"##?\s*非目标.*?\n(.*?)(?:\n##|\Z)",
            r"##?\s*Non-Goals.*?\n(.*?)(?:\n##|\Z)",
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1)
                items = re.findall(r"^[-*]\s*(?:\[\s*[xX]?\s*\]\s*)?(.*?)$", section, re.MULTILINE)
                return [item.strip() for item in items if item.strip()]
        return []

    def extract_api_definitions(content):
        apis = []
        api_section = re.search(r"##?\s*(?:接口设计|API Design).*?\n(.*?)(?:\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
        if api_section:
            section = api_section.group(1)
            for match in re.finditer(r"(GET|POST|PUT|DELETE|PATCH)\s+([/\w:{}-]+)", section, re.IGNORECASE):
                apis.append({"method": match.group(1).upper(), "path": match.group(2)})
        return apis

    def extract_tech_stack(content):
        tech = {}
        framework_match = re.search(r"(?:前端框架|后端框架|框架)[：:]\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
        if framework_match:
            tech["framework"] = framework_match.group(1).strip()
        db_match = re.search(r"(?:数据库|DB)[：:]\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
        if db_match:
            tech["database"] = db_match.group(1).strip()
        bcrypt_match = re.search(r"bcrypt.*?cost\s*factor\s*=\s*(\d+)", content, re.IGNORECASE)
        if bcrypt_match:
            tech["bcrypt_cost"] = bcrypt_match.group(1)
        jwt_match = re.search(r"(?:JWT|token).*?(\d+)\s*(?:天|day)", content, re.IGNORECASE)
        if jwt_match:
            tech["jwt_days"] = jwt_match.group(1)
        return tech

    extract_data_models = lambda c: []


# ── Non-Goals 漂移检测权重机制 ──

# 文件类型权重：路由文件 > 模型文件 > 配置文件 > 工具文件 > 测试文件 > 注释
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

# 代码特征权重：包含路由定义 > 包含模型定义 > 包含导入 > 纯文本提及
CODE_FEATURE_WEIGHTS = {
    "route_definition": 2.0,    # .get('/path'), router.post(), @app.route()
    "model_definition": 1.5,    # class User:, new Schema(), model()
    "function_export": 1.0,     # export function, def login()
    "import_statement": 0.5,    # import oauth, require('passport')
    "text_mention": 0.2,        # 纯文本提及
    "comment_only": 0.0,        # 仅在注释中出现 → 不计入
}

# 漂移判定阈值
DRIFT_THRESHOLD = 2.0


def classify_file(filepath):
    """根据文件路径分类文件类型。"""
    path_lower = str(filepath).lower()
    for ftype, keywords in [
        ("route", ["route", "controller", "handler", "endpoint", "api"]),
        ("model", ["model", "entity", "schema", "domain"]),
        ("service", ["service", "business", "usecase", "logic", "core"]),
        ("config", ["config", "setting", "env"]),
        ("middleware", ["middleware", "guard", "interceptor", "plugin"]),
        ("util", ["util", "helper", "lib", "common", "shared"]),
        ("test", ["test", "spec", "e2e"]),
    ]:
        if any(kw in path_lower for kw in keywords):
            return ftype
    return "other"


def extract_code_features(content, keyword):
    """提取代码中与关键词相关的特征。"""
    features = []
    keyword_lower = keyword.lower()
    lines = content.split("\n")

    for line in lines:
        line_lower = line.lower().strip()
        if keyword_lower not in line_lower:
            continue

        # 跳过纯注释行
        if line.strip().startswith("//") or line.strip().startswith("#") or line.strip().startswith("*"):
            features.append("comment_only")
            continue

        # 路由定义
        if re.search(r"\.(get|post|put|delete|patch)\s*\(", line_lower):
            features.append("route_definition")
            continue

        # 模型定义
        if re.search(r"(?:class|struct|interface|type)\s+\w+", line_lower):
            features.append("model_definition")
            continue

        # 函数导出/定义
        if re.search(r"(?:export\s+(?:default\s+)?(?:function|const|class)|def\s+\w+|function\s+\w+)", line_lower):
            features.append("function_export")
            continue

        # 导入语句
        if re.search(r"(?:import|require|from|include)", line_lower):
            features.append("import_statement")
            continue

        # 纯文本提及
        features.append("text_mention")

    return features


def scan_codebase_for_features(code_dir, keywords):
    """扫描代码库，返回带权重的匹配结果。"""
    matches = []
    code_path = Path(code_dir)

    for pattern in ["**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "**/*.py", "**/*.go", "**/*.rs"]:
        for filepath in code_path.glob(pattern):
            try:
                content = filepath.read_text(encoding="utf-8")
                for keyword in keywords:
                    if keyword.lower() not in content.lower():
                        continue

                    # 计算权重
                    file_type = classify_file(filepath.relative_to(code_path))
                    file_weight = FILE_TYPE_WEIGHTS.get(file_type, 1.0)

                    features = extract_code_features(content, keyword)
                    if not features:
                        continue

                    # 取最高权重的特征
                    feature_weights = [CODE_FEATURE_WEIGHTS.get(f, 0.2) for f in features]
                    max_feature_weight = max(feature_weights) if feature_weights else 0

                    total_weight = file_weight * max_feature_weight

                    # 只记录超过阈值的匹配
                    if total_weight >= DRIFT_THRESHOLD:
                        matches.append({
                            "keyword": keyword,
                            "file": str(filepath.relative_to(code_path)),
                            "file_type": file_type,
                            "weight": round(total_weight, 1),
                            "features": list(set(features)),
                        })
            except Exception:
                continue

    # 去重：同一关键词在同一文件只保留一次
    seen = set()
    unique_matches = []
    for m in matches:
        key = (m["keyword"], m["file"])
        if key not in seen:
            seen.add(key)
            unique_matches.append(m)

    return unique_matches


def find_config_value(code_dir, config_name):
    """查找配置文件中的值。"""
    code_path = Path(code_dir)

    pkg_path = code_path / "package.json"
    if pkg_path.exists():
        try:
            content = pkg_path.read_text(encoding="utf-8")
            dep_pattern = rf'"{re.escape(config_name)}"\s*:\s*"([^"]+)"'
            match = re.search(dep_pattern, content)
            if match:
                return match.group(1), "package.json"
        except Exception:
            pass

    pyproject_path = code_path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            content = pyproject_path.read_text(encoding="utf-8")
            dep_pattern = rf"{re.escape(config_name)}\s*=\s*['\"]([^'\"]+)['\"]"
            match = re.search(dep_pattern, content)
            if match:
                return match.group(1), "pyproject.toml"
        except Exception:
            pass

    return None, None


def scan_existing_routes(code_dir):
    """扫描代码库中已有的路由。"""
    routes = []
    code_path = Path(code_dir)

    for pattern in ["**/*.js", "**/*.ts", "**/*.py", "**/*.go"]:
        for filepath in code_path.glob(pattern):
            try:
                content = filepath.read_text(encoding="utf-8")
                route_patterns = [
                    r"\.(get|post|put|delete|patch)\s*\(\s*['\"]([/\w:{}-]+)['\"]",
                    r"@app\.(route|get|post|put|delete)\s*\(\s*['\"]([/\w:{}-]+)['\"]",
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


def check_non_goal_drift(non_goals, code_dir):
    """检查 Non-Goals 是否已在代码中实现（范围蔓延）——带权重机制。"""
    drifts = []

    for ng in non_goals:
        keywords = []
        # 提取括号内的内容
        paren_match = re.search(r"（(.+?)）", ng)
        if paren_match:
            keywords.extend(paren_match.group(1).split("/"))
        # 提取主要名词（至少3个字符的单词或2个字符的中文）
        words = re.findall(r"[一-龥]{2,}|[a-zA-Z]{3,}", ng)
        keywords.extend(words)

        keywords = list(set([k.lower() for k in keywords if len(k) >= 2]))
        if not keywords:
            continue

        matches = scan_codebase_for_features(code_dir, keywords)
        if matches:
            # 按权重排序，只取最高权重的
            matches.sort(key=lambda x: x["weight"], reverse=True)
            top_matches = matches[:3]
            drifts.append({
                "type": "Non-Goals 漂移",
                "severity": "严重",
                "spec_says": ng,
                "code_has": [f"{m['file']} (权重: {m['weight']}, 特征: {', '.join(m['features'][:2])})" for m in top_matches],
                "suggestion": "将此项从 Non-Goals 移除，或清理代码中意外实现的部分",
            })

    return drifts


def check_api_drift(spec_apis, code_routes):
    """检查 spec 中的接口是否与代码一致。"""
    drifts = []

    for spec_api in spec_apis:
        found = False
        for code_route in code_routes:
            if (spec_api["method"] == code_route["method"] and
                spec_api["path"] == code_route["path"]):
                found = True
                break

        if not found:
            drifts.append({
                "type": "接口签名漂移",
                "severity": "警告",
                "spec_says": f"{spec_api['method']} {spec_api['path']}",
                "code_has": "未找到匹配路由",
                "suggestion": "检查接口是否已实现，或更新 spec 中的接口定义",
            })

    return drifts


def check_tech_drift(spec_tech, code_dir):
    """检查技术约束是否被违反。"""
    drifts = []

    if spec_tech.get("bcrypt_cost"):
        code_path = Path(code_dir)
        for pattern in ["**/*.js", "**/*.ts", "**/*.py"]:
            for filepath in code_path.glob(pattern):
                try:
                    content = filepath.read_text(encoding="utf-8")
                    if "bcrypt" in content.lower():
                        cost_match = re.search(r"cost\s*[=:]\s*(\d+)", content)
                        if cost_match:
                            actual_cost = cost_match.group(1)
                            expected_cost = spec_tech["bcrypt_cost"]
                            if actual_cost != expected_cost:
                                drifts.append({
                                    "type": "技术约束漂移",
                                    "severity": "警告",
                                    "spec_says": f"bcrypt cost factor = {expected_cost}",
                                    "code_has": f"bcrypt cost factor = {actual_cost} ({filepath.relative_to(code_path)})",
                                    "suggestion": "统一 cost factor 值",
                                })
                except Exception:
                    continue

    return drifts


def check_agents_drift(spec_content, code_dir):
    """检查 AGENTS.md 是否过时。"""
    drifts = []

    framework_match = re.search(r"(?:前端框架|后端框架|框架)[：:]\s*([A-Za-z]+)\s*([\d.]+)?", spec_content, re.IGNORECASE)
    if framework_match:
        framework = framework_match.group(1)
        spec_version = framework_match.group(2)

        pkg_path = Path(code_dir) / "package.json"
        if pkg_path.exists() and spec_version:
            try:
                pkg_content = pkg_path.read_text(encoding="utf-8")
                dep_pattern = rf'"{re.escape(framework.lower())}"\s*:\s*"[\^~]?([\d.]+)"'
                dep_match = re.search(dep_pattern, pkg_content, re.IGNORECASE)
                if dep_match:
                    code_version = dep_match.group(1)
                    if not code_version.startswith(spec_version.split(".")[0]):
                        drifts.append({
                            "type": "AGENTS.md 过时",
                            "severity": "警告",
                            "spec_says": f"{framework} {spec_version}",
                            "code_has": f"{framework} {code_version}",
                            "suggestion": f"更新 AGENTS.md 为 {framework} {code_version}",
                        })
            except Exception:
                pass

    return drifts


def print_report(drifts, spec_path, code_dir):
    """打印人类可读报告。"""
    print("📋 Spec 漂移检测报告")
    print("=" * 50)
    print(f"Spec: {spec_path}")
    print(f"代码目录: {code_dir}")
    print()

    if not drifts:
        print("🎉 未发现漂移！Spec 与代码完全一致。")
        print("=" * 50)
        return

    severe = [d for d in drifts if d["severity"] == "严重"]
    warnings = [d for d in drifts if d["severity"] == "警告"]

    if severe:
        print(f"🔴 严重 ({len(severe)}):")
        for drift in severe:
            print(f"  [{drift['type']}]")
            print(f"    Spec: {drift['spec_says']}")
            if isinstance(drift['code_has'], list):
                for ch in drift['code_has']:
                    print(f"    Code: {ch}")
            else:
                print(f"    Code: {drift['code_has']}")
            print(f"    建议: {drift['suggestion']}")
        print()

    if warnings:
        print(f"🟡 警告 ({len(warnings)}):")
        for drift in warnings:
            print(f"  [{drift['type']}]")
            print(f"    Spec: {drift['spec_says']}")
            if isinstance(drift['code_has'], list):
                for ch in drift['code_has']:
                    print(f"    Code: {ch}")
            else:
                print(f"    Code: {drift['code_has']}")
            print(f"    建议: {drift['suggestion']}")
        print()

    print("=" * 50)
    print(f"严重: {len(severe)} / 警告: {len(warnings)}")

    if severe:
        print("⚠️  请先修复严重项。")
    if warnings:
        print("💡 建议处理警告项，保持 spec 与代码同步。")


def main():
    parser = argparse.ArgumentParser(
        description="检测 Spec 是否漂移",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础检测
  python detect-spec-drift.py --spec AGENTS.md --code-dir ./src

  # JSON 输出（用于 CI 集成）
  python detect-spec-drift.py --spec AGENTS.md --code-dir ./src --json

  # 只检测 Non-Goals 漂移
  python detect-spec-drift.py --spec AGENTS.md --code-dir ./src --skip-api --skip-tech
        """
    )
    parser.add_argument("--spec", required=True, help="Spec 文件路径")
    parser.add_argument("--code-dir", default=".", help="代码目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--skip-api", action="store_true", help="跳过接口漂移检测")
    parser.add_argument("--skip-tech", action="store_true", help="跳过技术约束漂移检测")
    args = parser.parse_args()

    spec_content = read_spec(args.spec)
    non_goals = extract_non_goals(spec_content)
    spec_tech = extract_tech_stack(spec_content)
    spec_apis = extract_api_definitions(spec_content)

    code_routes = scan_existing_routes(args.code_dir)

    drifts = []
    drifts.extend(check_non_goal_drift(non_goals, args.code_dir))
    if not args.skip_api:
        drifts.extend(check_api_drift(spec_apis, code_routes))
    if not args.skip_tech:
        drifts.extend(check_tech_drift(spec_tech, args.code_dir))
    drifts.extend(check_agents_drift(spec_content, args.code_dir))

    if args.json:
        output = {
            "spec_file": args.spec,
            "code_dir": args.code_dir,
            "drifts": drifts,
            "summary": {
                "severe": len([d for d in drifts if d["severity"] == "严重"]),
                "warnings": len([d for d in drifts if d["severity"] == "警告"]),
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(drifts, args.spec, args.code_dir)

    if any(d["severity"] == "严重" for d in drifts):
        sys.exit(1)
    if drifts:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
