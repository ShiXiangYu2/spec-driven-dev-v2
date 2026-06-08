#!/usr/bin/env python3
"""
环境检测脚本——检测开发环境，推荐可用的 SDD 工具。

用法:
    python check-env.py
    python check-env.py --check openspec
    python check-env.py --check spec-kit
    python check-env.py --check superpowers
    python check-env.py --json

输出:
    人类可读的报告（默认）或 JSON（--json 模式）
"""

import subprocess
import sys
import json
import argparse
from pathlib import Path


def run_cmd(cmd, shell=False):
    """运行命令，返回 (stdout, stderr, returncode)。失败时返回 None。"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            shell=shell,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def check_python():
    version = run_cmd(["python3", "--version"])
    if not version:
        version = run_cmd(["python", "--version"])
    return version


def check_node():
    return run_cmd(["node", "--version"])


def check_npm():
    return run_cmd(["npm", "--version"])


def check_uv():
    return run_cmd(["uv", "--version"])


def check_git():
    return run_cmd(["git", "--version"])


def check_pip():
    return run_cmd(["pip3", "--version"])


def check_claude_code():
    """检测是否在 Claude Code 环境中。"""
    # 检查是否存在 Claude Code 特有的环境变量或路径
    home = Path.home()
    claude_dir = home / ".claude"
    if claude_dir.exists():
        return "detected"
    return None


def check_npx_package(package_name):
    """检查某个 npx 包是否可用。"""
    result = run_cmd(["npx", "--yes", package_name, "--version"])
    return result is not None


def detect_environment():
    """完整环境检测。"""
    return {
        "python": check_python(),
        "node": check_node(),
        "npm": check_npm(),
        "uv": check_uv(),
        "git": check_git(),
        "pip": check_pip(),
        "claude_code": check_claude_code(),
    }


def recommend_tools(env):
    """根据环境推荐工具。"""
    recommendations = []

    has_node = env.get("node") is not None
    has_npm = env.get("npm") is not None
    has_python = env.get("python") is not None
    has_uv = env.get("uv") is not None
    has_git = env.get("git") is not None
    has_claude = env.get("claude_code") is not None

    # 推荐逻辑
    if has_node and has_npm:
        recommendations.append({
            "tool": "OpenSpec",
            "available": True,
            "install": "npm install -g openspec-cn",
            "reason": "Node.js 和 npm 已安装，可立即使用",
        })
    else:
        recommendations.append({
            "tool": "OpenSpec",
            "available": False,
            "reason": "需要 Node.js + npm（未检测到）",
        })

    if has_python and has_uv:
        recommendations.append({
            "tool": "Spec-Kit",
            "available": True,
            "install": "pip install uv && git clone https://github.com/github/spec-kit.git",
            "reason": "Python 和 uv 已安装，可立即使用",
        })
    else:
        recommendations.append({
            "tool": "Spec-Kit",
            "available": False,
            "reason": f"需要 Python + uv（Python: {'有' if has_python else '无'}, uv: {'有' if has_uv else '无'}）",
        })

    if has_claude:
        recommendations.append({
            "tool": "Superpowers",
            "available": True,
            "install": "/plugin marketplace add obra/superpowers-marketplace && /plugin install superpowers@superpowers-marketplace",
            "reason": "Claude Code 环境已检测到",
        })
    else:
        recommendations.append({
            "tool": "Superpowers",
            "available": False,
            "reason": "仅支持 Claude Code 环境",
        })

    # spec-first 总是可用
    recommendations.append({
        "tool": "spec-first (AGENTS.md)",
        "available": True,
        "install": "无需安装",
        "reason": "零依赖，任何环境都可用",
    })

    # 确定首选推荐
    available_tools = [r for r in recommendations if r["available"]]
    if available_tools:
        # 优先级：OpenSpec > Spec-Kit > Superpowers > spec-first
        priority = ["OpenSpec", "Spec-Kit", "Superpowers", "spec-first (AGENTS.md)"]
        for p in priority:
            for tool in available_tools:
                if tool["tool"] == p:
                    tool["recommended"] = True
                    break
            else:
                continue
            break
        else:
            # 如果没有匹配优先级，推荐第一个可用的
            available_tools[0]["recommended"] = True

    return recommendations


def print_report(env, recommendations):
    """打印人类可读报告。"""
    print("🔍 环境检测报告")
    print("=" * 40)
    print()

    print("编程语言环境:")
    for name, key in [("Python", "python"), ("Node.js", "node"), ("npm", "npm"), ("uv", "uv")]:
        val = env.get(key)
        icon = "✅" if val else "❌"
        detail = f" ({val})" if val else " (未安装)"
        print(f"  {icon} {name}{detail}")

    print()
    print("版本管理:")
    val = env.get("git")
    icon = "✅" if val else "❌"
    detail = f" ({val})" if val else " (未安装)"
    print(f"  {icon} Git{detail}")

    print()
    print("AI 工具:")
    val = env.get("claude_code")
    icon = "✅" if val else "❌"
    print(f"  {icon} Claude Code{' (已检测到)' if val else ' (未检测到)'}")

    print()
    print("=" * 40)
    print()

    # 推荐方案
    recommended = None
    for r in recommendations:
        if r.get("recommended"):
            recommended = r
            break

    if recommended:
        print(f"🎯 推荐方案: {recommended['tool']}")
        print(f"   理由: {recommended['reason']}")
        if recommended.get("install") and recommended["install"] != "无需安装":
            print(f"   安装: {recommended['install']}")
        print()

    print("所有可用方案:")
    for r in recommendations:
        icon = "✅" if r["available"] else "❌"
        rec_mark = " 🎯 推荐" if r.get("recommended") else ""
        print(f"  {icon} {r['tool']}{rec_mark}")
        print(f"     {r['reason']}")

    print()
    if recommended and recommended["tool"] == "spec-first (AGENTS.md)":
        print("💡 你的环境目前只有纯文档方案可用。这完全没问题——")
        print("   AGENTS.md + Markdown 模板就能防止 60% 以上的返工。")
        print("   如果以后安装了 Node.js，可以随时升级到 OpenSpec。")


def main():
    parser = argparse.ArgumentParser(
        description="检测 SDD 工具环境",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整环境检测
  python check-env.py

  # 检查特定工具是否可用
  python check-env.py --check openspec
  python check-env.py --check spec-kit
  python check-env.py --check superpowers

  # JSON 输出（用于 CI 集成）
  python check-env.py --json
        """
    )
    parser.add_argument("--check", choices=["openspec", "spec-kit", "superpowers"],
                        help="检查特定工具是否可用")
    parser.add_argument("--json", action="store_true",
                        help="输出 JSON 格式")
    args = parser.parse_args()

    env = detect_environment()

    if args.check:
        # 单个工具检查
        recommendations = recommend_tools(env)
        tool_map = {
            "openspec": "OpenSpec",
            "spec-kit": "Spec-Kit",
            "superpowers": "Superpowers",
        }
        target = tool_map[args.check]
        for r in recommendations:
            if r["tool"] == target:
                if args.json:
                    print(json.dumps(r, ensure_ascii=False, indent=2))
                else:
                    icon = "✅ 可用" if r["available"] else "❌ 不可用"
                    print(f"{target}: {icon}")
                    print(f"  原因: {r['reason']}")
                sys.exit(0 if r["available"] else 1)
        sys.exit(1)

    recommendations = recommend_tools(env)

    if args.json:
        output = {
            "environment": env,
            "recommendations": recommendations,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(env, recommendations)


if __name__ == "__main__":
    main()
