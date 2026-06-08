"""
Spec 解析公共模块。

被以下脚本共用：
- check-code-consistency.py
- detect-spec-drift.py
- generate-execution-plan.py
- validate-spec.py

提供统一的 spec 文件读取和章节提取功能。
"""

import re
import sys
from pathlib import Path


def read_file(filepath):
    """读取文件内容，失败时返回 None。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"❌ 错误: 无法读取文件 {filepath}: {e}")
        return None


def read_spec(filepath):
    """读取 spec 文件，失败时退出程序。"""
    content = read_file(filepath)
    if content is None:
        print(f"❌ 错误: Spec 文件不存在: {filepath}")
        sys.exit(2)
    return content


def extract_section(content, headings):
    """提取指定标题下的内容。

    支持格式：
        ## 做什么
        ## 1. 做什么（What）
        ## 2. Constraints

    Args:
        content: 文件完整内容
        headings: 标题列表，会按顺序尝试匹配

    Returns:
        标题下的内容字符串，未找到返回空字符串
    """
    for heading in headings:
        # 尝试多种标题格式：纯标题、带数字前缀、带括号副标题
        escaped = re.escape(heading)
        patterns = [
            # 标准格式：# 做什么 / ## 做什么 / ### 做什么
            rf"(?:^|\n)#{{1,3}}\s*{escaped}\s*\n",
            # 带数字前缀+副标题：## 1. 做什么（What）—— 描述
            rf"(?:^|\n)#{{1,3}}\s*\d+\.\s*{escaped}(?:\s*[（(].*?[）)])?.*?\s*\n",
            # 只有数字前缀：## 3. 约束
            rf"(?:^|\n)#{{1,3}}\s*\d+\.\s*{escaped}.*?\s*\n",
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                start = match.end()
                next_header = re.search(r"\n##?\s", content[start:])
                if next_header:
                    return content[start:start + next_header.start()].strip()
                return content[start:].strip()
    return ""


def extract_non_goals(content):
    """提取 Non-Goals 列表项。

    Returns:
        list[str]: Non-Goals 列表，每项是一个字符串
    """
    # 支持多种标题格式：
    #   ## 非目标
    #   ## 4. 非目标（Non-Goals）—— v1.0 不做
    #   ## Non-Goals
    heading_patterns = [
        r"##?\s*(?:\d+\.\s*)?非目标",
        r"##?\s*(?:\d+\.\s*)?Non-Goals",
        r"##?\s*(?:\d+\.\s*)?不做",
    ]
    for hp in heading_patterns:
        # 匹配标题行后的内容，直到下一个 ## 标题或文件结尾
        pattern = rf"(?:^|\n){hp}.*?\n(.*?)(?:\n\s*\n##|\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            section = match.group(1)
            items = re.findall(r"^[-*]\s*(?:\[\s*[xX]?\s*\]\s*)?(.*?)$", section, re.MULTILINE)
            return [item.strip() for item in items if item.strip()]
    return []


def extract_api_definitions(content):
    """从 spec 中提取接口定义。

    Returns:
        list[dict]: 每个元素包含 method 和 path
    """
    apis = []
    api_section = re.search(
        r"##?\s*(?:接口设计|API Design).*?\n(.*?)(?:\n##|\Z)",
        content, re.DOTALL | re.IGNORECASE
    )
    if not api_section:
        return apis

    section = api_section.group(1)
    for match in re.finditer(r"(GET|POST|PUT|DELETE|PATCH)\s+([/\w:{}-]+)", section, re.IGNORECASE):
        apis.append({
            "method": match.group(1).upper(),
            "path": match.group(2),
        })

    return apis


def extract_tech_stack(content):
    """从 spec 中提取技术栈约束。

    Returns:
        dict: 包含 framework, database, bcrypt_cost, jwt_days 等键
    """
    tech = {}

    framework_match = re.search(
        r"(?:前端框架|后端框架|框架)[：:]\s*(.+?)(?:\n|$)", content, re.IGNORECASE
    )
    if framework_match:
        tech["framework"] = framework_match.group(1).strip()

    db_match = re.search(
        r"(?:数据库|DB)[：:]\s*(.+?)(?:\n|$)", content, re.IGNORECASE
    )
    if db_match:
        tech["database"] = db_match.group(1).strip()

    bcrypt_match = re.search(r"bcrypt.*?cost\s*factor\s*=\s*(\d+)", content, re.IGNORECASE)
    if bcrypt_match:
        tech["bcrypt_cost"] = bcrypt_match.group(1)

    jwt_match = re.search(r"(?:JWT|token).*?(\d+)\s*(?:天|day)", content, re.IGNORECASE)
    if jwt_match:
        tech["jwt_days"] = jwt_match.group(1)

    return tech


def extract_data_models(content):
    """从数据模型章节提取模型名。

    Returns:
        list[str]: 模型名列表
    """
    section = extract_section(content, ["数据模型", "Data Model", "模型"])
    if not section:
        return []

    models = []
    for match in re.finditer(r"^([A-Z][a-zA-Z0-9_]*):", section, re.MULTILINE):
        models.append(match.group(1))

    return models


def extract_tasks(content):
    """从任务拆解章节提取任务列表。

    Returns:
        list[str]: 任务列表
    """
    section = extract_section(content, ["任务拆解", "Task Breakdown", "任务"])
    if not section:
        return []

    tasks = []
    for match in re.finditer(r"^[-*]\s*(?:\[\s*\]\s*)?(.*?)$", section, re.MULTILINE):
        task_text = match.group(1).strip()
        if task_text and not task_text.startswith("placeholder"):
            tasks.append(task_text)

    return tasks
