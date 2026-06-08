#!/usr/bin/env python3
"""
Spec 同行评审脚本——模拟 Senior Engineer 做结构化评审。

用法:
    python peer-review-spec.py <spec-file.md>
    python peer-review-spec.py <spec-file.md> --strict
    python peer-review-spec.py <spec-file.md> --json

评审维度:
    1. 完整性（Completeness）- 四要素 + 执行计划 + 验收标准
    2. 具体性（Specificity）- 数值、边界、可测量
    3. 一致性（Consistency）- 内部自洽，无冲突
    4. 可测试性（Testability）- 能写出测试用例
    5. 风险（Risk）- 边界、异常、回滚

问题分级:
    🔴 Blocker  - 必须修复，否则 spec 不可用
    🟡 Warning  - 强烈建议修复，影响执行
    🟢 Kudos    - 做得好的地方

退出码:
    0 - 无 Blocker
    1 - 有 Blocker
    2 - 文件不存在
"""

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))

try:
    from lib.spec_parser import read_spec, extract_section, extract_non_goals, extract_tasks
except ImportError:
    def read_spec(filepath):
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
            r"##?\s*不做.*?\n(.*?)(?:\n##|\Z)",
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1)
                items = re.findall(r"^[-*]\s*(?:\[\s*[xX]?\s*\]\s*)?(.*?)$", section, re.MULTILINE)
                return [item.strip() for item in items if item.strip()]
        return []

    def extract_tasks(content):
        section = extract_section(content, ["任务拆解", "Task Breakdown", "任务"])
        if not section:
            return []
        tasks = []
        for match in re.findall(r"^[-*]\s*(?:\[\s*\]\s*)?(.*?)$", section, re.MULTILINE):
            task_text = match.strip()
            if task_text and not task_text.startswith("placeholder"):
                tasks.append(task_text)
        return tasks


# ── 评审规则引擎 ──

def check_completeness(content):
    """检查完整性：四要素 + 执行计划 + 验收标准"""
    issues = []
    kudos = []

    # 四要素
    what = extract_section(content, ["做什么", "What", "功能描述", "功能概述"])
    why = extract_section(content, ["为什么做", "Why", "背景", "问题背景", "动机"])
    constraints = extract_section(content, ["约束", "Constraints", "技术约束", "限制条件"])
    non_goals = extract_non_goals(content)

    if not what:
        issues.append(("blocker", "缺少 What 部分", "spec 必须说明'做什么'"))
    if not why:
        issues.append(("warning", "缺少 Why 部分", "没有'为什么做'会导致方向偏差"))
    if not constraints:
        issues.append(("blocker", "缺少 Constraints 部分", "没有约束等于没有质量标准"))
    if not non_goals:
        issues.append(("blocker", "缺少 Non-Goals", "没有非目标会导致范围蔓延"))

    # 执行计划
    plan = extract_section(content, ["执行计划", "Execution Plan", "实施计划"])
    if not plan:
        issues.append(("warning", "缺少执行计划", "开发者不知道从哪里开始"))
    else:
        kudos.append(("执行计划", "已包含执行计划，开发者有明确路径"))

    # 验收标准
    ac = extract_section(content, ["验收标准", "Acceptance Criteria", "验收"])
    if not ac:
        issues.append(("warning", "缺少验收标准", "无法定义'完成'"))

    # 接口设计（如果适用）
    api = extract_section(content, ["接口设计", "API Design", "API"])
    if api and ("请求体" not in api and "响应" not in api and "错误码" not in api):
        issues.append(("warning", "接口设计不完整", "应包含请求体、响应体、错误码"))

    return issues, kudos


def check_specificity(content):
    """检查具体性：数值、边界、可测量"""
    issues = []
    kudos = []

    # 全局搜索具体数值
    numeric_patterns = [
        r"\d+\s*(?:天|小时|分钟|秒|ms|毫秒|s|min|h|d)",
        r"\d+\s*(?:字符|个|条|次|页|MB|GB|KB)",
        r"[><=!]+\s*\d+%?",
        r"P\d{2,3}\s*<\s*\d+",
        r"cost\s*factor\s*=\s*\d+",
        r"版本\s*[vV]?\d+\.",
    ]
    numeric_found = sum(1 for p in numeric_patterns if re.search(p, content))

    if numeric_found < 2:
        issues.append(("warning", "具体数值不足",
                       f"Constraints 和 What 中仅找到 {numeric_found} 类具体数值，建议至少 2 处"))
    else:
        kudos.append(("具体性", f"找到 {numeric_found} 类具体数值，可测量、可验证"))

    # 检查边界条件
    boundary_keywords = ["边界", "异常", "错误", "失败", "超时", "空值", "null", "undefined", "最大", "最小", "限制"]
    boundary_found = sum(1 for kw in boundary_keywords if kw.lower() in content.lower())
    if boundary_found < 2:
        issues.append(("warning", "边界条件覆盖不足",
                       f"仅提及 {boundary_found} 类边界情况，建议考虑错误处理、空值、超时等"))
    else:
        kudos.append(("边界条件", f"覆盖了 {boundary_found} 类边界/异常场景"))

    return issues, kudos


def check_consistency(content):
    """检查一致性：内部自洽"""
    issues = []
    kudos = []

    non_goals = extract_non_goals(content)
    what_section = extract_section(content, ["做什么", "What", "功能描述"]).lower()

    # 检查 Non-Goals 与 What 是否冲突
    conflicts = []
    for ng in non_goals:
        # 提取关键词（括号内的、中文词、英文词）
        keywords = []
        paren = re.search(r"（(.+?)）", ng)
        if paren:
            keywords.extend([k.strip() for k in paren.group(1).split("/")])
        words = re.findall(r"[一-龥]{2,}|[a-zA-Z]{3,}", ng)
        keywords.extend(words)

        for kw in set(keywords):
            if len(kw) >= 3 and kw.lower() in what_section:
                conflicts.append((ng, kw))
                break

    if conflicts:
        for ng, kw in conflicts[:3]:
            issues.append(("blocker", f"Non-Goals 与 What 冲突",
                           f"Non-Goals 说'不做 {ng}'，但 What 中提到了 '{kw}'。请明确范围"))
    else:
        kudos.append(("一致性", "Non-Goals 与 What 无冲突"))

    # 检查任务拆解是否超纲
    tasks = extract_tasks(content)
    for task in tasks:
        for ng in non_goals:
            ng_keywords = re.findall(r"[一-龥]{2,}|[a-zA-Z]{3,}", ng)
            for kw in ng_keywords:
                if len(kw) >= 3 and kw.lower() in task.lower():
                    issues.append(("blocker", f"任务拆解超出范围",
                                   f"任务 '{task[:40]}...' 涉及 Non-Goals 中的 '{kw}'"))
                    break
            else:
                continue
            break

    return issues, kudos


def check_testability(content):
    """检查可测试性：能写出测试用例"""
    issues = []
    kudos = []

    ac = extract_section(content, ["验收标准", "Acceptance Criteria", "验收"])
    if ac:
        # 检查是否有可验证的条目
        checkboxes = re.findall(r"^\s*[-*]?\s*\[\s*[xX ]?\s*\]", ac, re.MULTILINE)
        if len(checkboxes) >= 3:
            kudos.append(("可测试性", f"验收标准有 {len(checkboxes)} 个可勾选项，可直接转化为测试用例"))
        elif len(checkboxes) >= 1:
            issues.append(("warning", "验收标准条目偏少",
                           f"只有 {len(checkboxes)} 个验收项，建议至少 3 条覆盖主要路径和边界"))
        else:
            issues.append(("warning", "验收标准无可勾选项",
                           "建议用 '- [ ] 条件' 格式写出可验证的验收标准"))

    # 检查是否提到了测试
    test_mentions = re.findall(r"测试|test|单元测试|集成测试|覆盖率", content, re.IGNORECASE)
    if len(test_mentions) >= 2:
        kudos.append(("测试意识", "spec 中考虑了测试策略"))
    else:
        issues.append(("warning", "缺少测试策略",
                       "建议说明测试覆盖要求（单元/集成/覆盖率）"))

    return issues, kudos


def check_risk(content):
    """检查风险：边界、异常、回滚"""
    issues = []
    kudos = []

    # 检查回滚方案
    rollback = re.search(r"回滚|rollback|撤销|revert", content, re.IGNORECASE)
    if not rollback:
        issues.append(("warning", "缺少回滚方案",
                       "变更 spec 应包含回滚方案；功能 spec 建议考虑失败处理"))
    else:
        kudos.append(("风险意识", "已考虑回滚/失败处理方案"))

    # 检查依赖声明
    deps = extract_section(content, ["依赖", "Dependencies", "前置条件", "Prerequisites"])
    if deps:
        kudos.append(("依赖管理", "已声明依赖/前置条件"))

    # 检查数据迁移（如果是变更类 spec）
    migration = re.search(r"迁移|migration|数据变更|schema", content, re.IGNORECASE)
    if migration:
        if not re.search(r"回滚|rollback|备份|backup", content, re.IGNORECASE):
            issues.append(("blocker", "数据变更缺少安全保护",
                           "涉及数据迁移/Schema 变更时必须有备份或回滚方案"))
        else:
            kudos.append(("数据安全", "数据变更配套了保护措施"))

    return issues, kudos


def calculate_score(issues, kudos):
    """计算综合评分。"""
    blockers = len([i for i in issues if i[0] == "blocker"])
    warnings = len([i for i in issues if i[0] == "warning"])

    # 基础分 100，blocker -15，warning -5，kudos +3（封顶 +15）
    score = 100
    score -= blockers * 15
    score -= warnings * 5
    score += min(len(kudos) * 3, 15)
    return max(0, min(100, score))


def print_review(issues, kudos, score, spec_path):
    """打印评审报告。"""
    print(f"\n📋 Spec 同行评审报告: {spec_path}")
    print("=" * 55)
    print(f"综合评分: {'🟢' if score >= 80 else '🟡' if score >= 60 else '🔴'} {score}/100")
    print()

    blockers = [i for i in issues if i[0] == "blocker"]
    warnings = [i for i in issues if i[0] == "warning"]

    if blockers:
        print(f"🔴 Blocker ({len(blockers)})——必须修复:")
        for _, title, suggestion in blockers:
            print(f"  [{title}]")
            print(f"    建议: {suggestion}")
        print()

    if warnings:
        print(f"🟡 Warning ({len(warnings)})——强烈建议:")
        for _, title, suggestion in warnings:
            print(f"  [{title}]")
            print(f"    建议: {suggestion}")
        print()

    if kudos:
        print(f"🟢 Kudos ({len(kudos)})——做得好的地方:")
        for title, msg in kudos:
            print(f"  ✓ [{title}] {msg}")
        print()

    print("=" * 55)
    if blockers:
        print("⚠️  存在 Blocker，spec 尚未达到可执行标准。")
    elif warnings:
        print("💡 有 Warning 待优化，但不阻塞执行。")
    else:
        print("🎉 评审通过！这是一个高质量的 spec。")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Spec 同行评审——模拟 Senior Engineer 结构化评审",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础评审
  python peer-review-spec.py specs/user-login.md

  # 严格模式：warning 也视为失败
  python peer-review-spec.py specs/user-login.md --strict

  # JSON 输出（用于 CI 集成）
  python peer-review-spec.py specs/user-login.md --json
        """
    )
    parser.add_argument("filepath", help="Spec 文件路径")
    parser.add_argument("--strict", action="store_true",
                        help="严格模式：warning 也视为失败")
    parser.add_argument("--json", action="store_true",
                        help="输出 JSON 格式")
    args = parser.parse_args()

    content = read_spec(args.filepath)

    all_issues = []
    all_kudos = []

    for check_fn in [check_completeness, check_specificity, check_consistency, check_testability, check_risk]:
        issues, kudos = check_fn(content)
        all_issues.extend(issues)
        all_kudos.extend(kudos)

    score = calculate_score(all_issues, all_kudos)

    if args.json:
        output = {
            "spec_file": args.filepath,
            "score": score,
            "grade": "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 60 else "D",
            "blockers": [{"title": t, "suggestion": s} for lvl, t, s in all_issues if lvl == "blocker"],
            "warnings": [{"title": t, "suggestion": s} for lvl, t, s in all_issues if lvl == "warning"],
            "kudos": [{"category": c, "message": m} for c, m in all_kudos],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_review(all_issues, all_kudos, score, args.filepath)

    blockers = [i for i in all_issues if i[0] == "blocker"]
    warnings = [i for i in all_issues if i[0] == "warning"]

    if blockers:
        sys.exit(1)
    if args.strict and warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
