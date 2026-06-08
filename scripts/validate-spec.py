#!/usr/bin/env python3
"""
Spec 文档完整性验证脚本

用法:
    python validate-spec.py <spec-file.md>
    python validate-spec.py <spec-file.md> --strict

检查项:
    - 文件存在且可读
    - 包含 What / Why / Constraints / Non-Goals 四要素
    - Non-Goals 至少有 3 条
    - What 具体到可测试（包含至少一个具体行为描述）
    - Constraints 有具体技术约束（非抽象描述）

退出码:
    0 - 验证通过
    1 - 验证失败（缺少必要要素）
    2 - 文件不存在或不可读
"""

import sys
import re
import argparse
from pathlib import Path

# 添加 lib 到路径
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))

try:
    from lib.spec_parser import read_spec, extract_section
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


def check_what(content):
    """检查是否包含 What 且具体可测试"""
    what_section = extract_section(content, ["做什么", "What", "功能描述", "功能概述", "需求描述"])
    has_what = bool(what_section)

    # 检查是否有具体行为（包含动词+名词+具体值）
    concrete_patterns = [
        r'可以\s*\w+\s*\w+',
        r'返回\s*\w+',
        r'支持\s*\w+',
        r'\d+\s*(天|小时|分钟|秒|ms|毫秒)',
        r'\d+\s*(字符|个|条)',
        r'>=?\s*\d+%'
    ]
    is_concrete = any(re.search(p, content) for p in concrete_patterns)

    return has_what, is_concrete


def check_why(content):
    """检查是否包含 Why"""
    why_section = extract_section(content, ["为什么做", "Why", "背景", "问题背景", "动机", "目的"])
    return bool(why_section)


def check_constraints(content):
    """检查是否包含 Constraints 且有具体技术约束"""
    c_section = extract_section(content, ["约束", "Constraints", "技术约束", "限制条件"])
    has_constraints = bool(c_section)

    # 检查是否有具体约束（包含技术关键词或具体值）
    concrete_patterns = [
        r'bcrypt|jwt|oauth|ssl|tls|https',
        r'\d+\s*(天|小时|分钟|秒|ms)',
        r'>=?\s*\d+%',
        r'\d+\s*(字符|个|条)',
        r'P\d{2,3}\s*<\s*\d+',
        r'响应时间|并发|吞吐量|QPS|TPS'
    ]
    is_concrete = any(re.search(p, content, re.IGNORECASE) for p in concrete_patterns)

    return has_constraints, is_concrete


def check_non_goals(content):
    """检查 Non-Goals 数量"""
    ng_section = extract_section(content, ["非目标", "Non-Goals", "不做", "排除", "Out of Scope"])
    if not ng_section:
        return False, 0

    # 统计列表项（- 或 * 或 [ ] 开头）
    items = re.findall(r'^[\s]*[-*\d+\.][\s]+', ng_section, re.MULTILINE)
    return True, len(items)


def validate_spec(filepath, strict=False):
    content = read_spec(filepath)

    results = []
    passed = 0
    failed = 0

    # 检查 What
    has_what, what_concrete = check_what(content)
    if has_what:
        if strict and not what_concrete:
            results.append("⚠️  What: 有 What 部分，但描述不够具体（建议包含具体行为/数值）")
            failed += 1
        else:
            results.append("✅  What: 已包含且具体可测试" if what_concrete else "✅  What: 已包含")
            passed += 1
    else:
        results.append("❌  What: 缺少做什么部分")
        failed += 1

    # 检查 Why
    if check_why(content):
        results.append("✅  Why: 已包含")
        passed += 1
    else:
        results.append("❌  Why: 缺少为什么做部分")
        failed += 1

    # 检查 Constraints
    has_constraints, constraints_concrete = check_constraints(content)
    if has_constraints:
        if strict and not constraints_concrete:
            results.append("⚠️  Constraints: 有约束部分，但缺少具体技术约束（建议包含具体值）")
            failed += 1
        else:
            results.append("✅  Constraints: 已包含且具体" if constraints_concrete else "✅  Constraints: 已包含")
            passed += 1
    else:
        results.append("❌  Constraints: 缺少约束部分")
        failed += 1

    # 检查 Non-Goals
    has_ng, ng_count = check_non_goals(content)
    if has_ng:
        if ng_count >= 3:
            results.append(f"✅  Non-Goals: 已包含 {ng_count} 条（≥3）")
            passed += 1
        else:
            results.append(f"⚠️  Non-Goals: 只有 {ng_count} 条，建议至少 3 条")
            failed += 1
    else:
        results.append("❌  Non-Goals: 缺少非目标部分")
        failed += 1

    # 输出结果
    print(f"\n📋 Spec 验证报告: {filepath}")
    print("=" * 50)
    for r in results:
        print(f"  {r}")
    print("=" * 50)
    print(f"\n通过: {passed} / 失败: {failed}")

    if failed == 0:
        print("🎉 验证通过！Spec 文档完整。\n")
        return 0
    else:
        print("⚠️  验证未通过，请补充缺失项。\n")
        return 1


def main():
    parser = argparse.ArgumentParser(description='验证 Spec 文档完整性')
    parser.add_argument('filepath', help='Spec 文件路径')
    parser.add_argument('--strict', action='store_true',
                        help='严格模式：要求 What 和 Constraints 必须包含具体数值')
    args = parser.parse_args()

    exit_code = validate_spec(args.filepath, args.strict)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
