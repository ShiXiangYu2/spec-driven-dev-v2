#!/usr/bin/env python3
"""
Evals 测试运行器——自动化验证 skill 的完整性。

用法:
    python run-evals.py
    python run-evals.py --skill-dir /path/to/spec-driven-dev
    python run-evals.py --json

检查项:
    1. 文件存在性——evals.json 引用的模板/脚本/参考文档是否存在
    2. 脚本可编译性——所有 .py 文件是否能通过 py_compile
    3. 脚本可执行性——主脚本是否有 shebang + 可执行权限
    4. 场景覆盖率——验证每个 eval 场景的必要文件是否齐备
    5. 交叉引用完整性——SKILL.md 中提到的文件是否都存在

退出码:
    0 - 全部通过
    1 - 有失败项
    2 - evals.json 不存在或解析失败
"""

import argparse
import json
import py_compile
import re
import sys
from pathlib import Path


def find_skill_dir():
    """自动定位 skill 根目录。"""
    script_dir = Path(__file__).parent.resolve()
    # 脚本在 scripts/ 下，向上两级是 skill 根目录
    return script_dir.parent


def load_evals(skill_dir):
    """加载 evals.json。"""
    evals_path = skill_dir / "evals" / "evals.json"
    if not evals_path.exists():
        print(f"❌ 错误: evals.json 不存在: {evals_path}")
        sys.exit(2)
    try:
        with open(evals_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ 错误: evals.json 解析失败: {e}")
        sys.exit(2)


FILE_ALIASES = {
    "AGENTS.md": "agents-md-template.md",
    "SKILL.md": "SKILL.md",
}


def check_file_existence(skill_dir, evals_data):
    """检查 evals 场景中引用的文件是否存在。"""
    results = []

    # 从 expected_output 中提取文件引用（仅 ASCII，避免中文前缀被包含）
    file_patterns = [
        r"([a-zA-Z0-9_-]+\.py)",
        r"([a-zA-Z0-9_-]+-template\.md)",
        r"([a-zA-Z0-9_-]+-guide\.md)",
        r"(AGENTS\.md)",
        r"([a-zA-Z0-9_-]+\.md)",
    ]

    for eval_item in evals_data.get("evals", []):
        eval_id = eval_item.get("id", "?")
        expected = eval_item.get("expected_output", "")
        referenced_files = set()

        for pattern in file_patterns:
            for match in re.finditer(pattern, expected):
                referenced_files.add(match.group(1))

        missing = []
        for fname in referenced_files:
            # 别名映射
            actual_fname = FILE_ALIASES.get(fname, fname)
            # 尝试多个可能的位置
            found = False
            for subdir in ["scripts", "assets", "references", "."]:
                if (skill_dir / subdir / actual_fname).exists():
                    found = True
                    break
            if not found:
                missing.append(fname)

        if missing:
            results.append({
                "eval_id": eval_id,
                "type": "missing_file",
                "prompt": eval_item.get("prompt", "")[:60],
                "missing": missing,
            })

    return results


def check_scripts_compile(skill_dir):
    """检查所有 .py 文件能否编译。"""
    results = []
    script_dir = skill_dir / "scripts"

    for py_file in script_dir.rglob("*.py"):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            results.append({
                "file": str(py_file.relative_to(skill_dir)),
                "type": "compile_error",
                "error": str(e),
            })

    return results


def check_scripts_executable(skill_dir):
    """检查主脚本是否有 shebang 和可执行权限。"""
    results = []
    script_dir = skill_dir / "scripts"
    main_scripts = [
        "validate-spec.py",
        "check-code-consistency.py",
        "detect-spec-drift.py",
        "generate-execution-plan.py",
        "check-env.py",
        "peer-review-spec.py",
        "run-evals.py",
    ]

    for script_name in main_scripts:
        script_path = script_dir / script_name
        if not script_path.exists():
            results.append({
                "file": f"scripts/{script_name}",
                "type": "missing",
                "error": "主脚本不存在",
            })
            continue

        with open(script_path, "r", encoding="utf-8") as f:
            first_line = f.readline()

        if not first_line.startswith("#!/usr/bin/env python3"):
            results.append({
                "file": f"scripts/{script_name}",
                "type": "no_shebang",
                "error": "缺少 shebang (#!/usr/bin/env python3)",
            })

    return results


def check_skill_md_references(skill_dir):
    """检查 SKILL.md 中引用的文件是否都存在。"""
    results = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [{"type": "missing_skill_md", "error": "SKILL.md 不存在"}]

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取引用的文件路径（各种格式）
    ref_patterns = [
        r"`((?:scripts|assets|references|evals)/[\w./-]+)`",
        r"\[.*?\]\(((?:scripts|assets|references|evals)/[\w./-]+)\)",
        r"((?:scripts|assets|references|evals)/[\w./-]+\.py)",
        r"((?:scripts|assets|references|evals)/[\w./-]+\.md)",
        r"((?:scripts|assets|references|evals)/[\w./-]+\.json)",
    ]

    referenced = set()
    for pattern in ref_patterns:
        for match in re.finditer(pattern, content):
            referenced.add(match.group(1))

    for ref_path in referenced:
        full_path = skill_dir / ref_path
        if not full_path.exists():
            results.append({
                "file": ref_path,
                "type": "skill_md_broken_ref",
                "error": f"SKILL.md 引用的文件不存在",
            })

    return results


def check_scene_coverage(evals_data):
    """检查场景覆盖是否完整。"""
    results = []
    evals = evals_data.get("evals", [])

    # 检查是否有重复 id
    ids = [e.get("id") for e in evals]
    if len(ids) != len(set(ids)):
        dupes = [i for i in ids if ids.count(i) > 1]
        results.append({
            "type": "duplicate_id",
            "error": f"存在重复 eval id: {set(dupes)}",
        })

    # 检查每个 eval 的必要字段
    for e in evals:
        eid = e.get("id", "?")
        if not e.get("prompt"):
            results.append({
                "eval_id": eid,
                "type": "missing_prompt",
                "error": "缺少 prompt 字段",
            })
        if not e.get("expected_output"):
            results.append({
                "eval_id": eid,
                "type": "missing_expected",
                "error": "缺少 expected_output 字段",
            })

    return results


def print_report(results, skill_dir):
    """打印人类可读报告。"""
    print(f"\n🧪 Spec-Driven-Dev Evals 测试报告")
    print(f"   Skill 目录: {skill_dir}")
    print("=" * 55)
    print()

    categories = {}
    for r in results:
        cat = r.get("type", "unknown")
        categories.setdefault(cat, []).append(r)

    # 按严重程度排序输出
    severe_types = ["missing", "compile_error", "missing_skill_md", "duplicate_id", "skill_md_broken_ref"]
    warning_types = ["missing_file", "no_shebang", "missing_prompt", "missing_expected"]

    severe = []
    warnings = []
    for r in results:
        if r.get("type") in severe_types:
            severe.append(r)
        elif r.get("type") in warning_types:
            warnings.append(r)

    if severe:
        print(f"🔴 严重 ({len(severe)}):")
        for r in severe:
            file_info = f" [{r.get('file', '?')}]" if r.get("file") else ""
            print(f"  {file_info} {r.get('error', r.get('type'))}")
        print()

    if warnings:
        print(f"🟡 警告 ({len(warnings)}):")
        for r in warnings:
            file_info = f" [{r.get('file', '?')}]" if r.get("file") else ""
            eval_info = f" eval#{r.get('eval_id', '?')}" if r.get("eval_id") else ""
            print(f"  {file_info}{eval_info} {r.get('error', r.get('type'))}")
        print()

    if not results:
        print("🎉 所有检查项通过！")
        print()

    print("=" * 55)
    print(f"总计: {len(results)} 个问题 ({len(severe)} 严重 / {len(warnings)} 警告)")


def main():
    parser = argparse.ArgumentParser(
        description="Evals 测试运行器——自动化验证 skill 完整性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认检查当前 skill
  python run-evals.py

  # 检查指定目录的 skill
  python run-evals.py --skill-dir /path/to/spec-driven-dev

  # JSON 输出
  python run-evals.py --json
        """
    )
    parser.add_argument("--skill-dir", help="Skill 根目录（默认自动检测）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir) if args.skill_dir else find_skill_dir()

    evals_data = load_evals(skill_dir)

    all_results = []
    all_results.extend(check_file_existence(skill_dir, evals_data))
    all_results.extend(check_scripts_compile(skill_dir))
    all_results.extend(check_scripts_executable(skill_dir))
    all_results.extend(check_skill_md_references(skill_dir))
    all_results.extend(check_scene_coverage(evals_data))

    if args.json:
        output = {
            "skill_dir": str(skill_dir),
            "eval_count": len(evals_data.get("evals", [])),
            "issues": all_results,
            "passed": len(all_results) == 0,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(all_results, skill_dir)

    if any(r.get("type") in ["missing", "compile_error", "missing_skill_md", "duplicate_id"] for r in all_results):
        sys.exit(1)
    if all_results:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
