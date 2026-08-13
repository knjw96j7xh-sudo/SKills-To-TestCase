#!/usr/bin/env python3
"""用例解析与导出共用规则（优先级、MD 表、JSON 加载、排序）。"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

# 保证同目录脚本互相 import 时路径稳定（importlib / 异目录调用）
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


FIELDS = (
    "id",
    "module",
    "test_point",
    "precondition",
    "steps",
    "expected",
    "checkpoint",
    "type",
    "priority",
    "remark",
)

HEADER_TO_FIELD = {
    "用例ID": "id",
    "所属模块": "module",
    "测试点": "test_point",
    "前置条件": "precondition",
    "操作步骤": "steps",
    "预期结果": "expected",
    "关联检查点": "checkpoint",
    "场景类型": "type",
    "优先级": "priority",
    "备注": "remark",
}

VALID_TYPES = {"正向", "异常", "边界", "并发"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
TYPE_ORDER = ["正向", "异常", "边界", "并发"]

# 与 README / project.config / testcase-table-config 一致
TYPE_PRIORITY = {
    "正向": "P1",
    "异常": "P0",
    "边界": "P1",
    "并发": "P2",
}

PRIORITY_TO_JIRA = {
    "P0": "High",
    "P1": "Medium",
    "P2": "Low",
    "P3": "Low",
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
}

CASE_ID_RE = re.compile(r"^[A-Za-z]+-\d+[A-Za-z]*$")
CASE_ID_SORT_RE = re.compile(r"^([A-Za-z]+)-(\d+)([A-Za-z]*)$", re.IGNORECASE)

PINNED_DEPENDENCIES = {
    "json-repair": "0.61.2",
    "openpyxl": "3.1.5",
    "PyYAML": "6.0.3",
}


def text(value) -> str:
    return "" if value is None else str(value).strip()


def default_priority_for_type(scene_type: str) -> str:
    return TYPE_PRIORITY.get(text(scene_type), "P1")


def priority_to_jira(priority_text: str, scene_type: str = "") -> str:
    """显式优先级优先；否则按场景类型默认规则映射到 Jira。"""
    raw = text(priority_text)
    if raw in PRIORITY_TO_JIRA:
        return PRIORITY_TO_JIRA[raw]
    match = re.fullmatch(r"P(\d)", raw, re.IGNORECASE)
    if match:
        level = int(match.group(1))
        if level <= 0:
            return "High"
        if level == 1:
            return "Medium"
        return "Low"
    return PRIORITY_TO_JIRA[default_priority_for_type(scene_type)]


def case_sort_key(case_id: str):
    match = CASE_ID_SORT_RE.match(text(case_id))
    if match:
        prefix, number, suffix = match.groups()
        return (prefix.upper(), int(number), suffix.lower())
    return ("~", 99999, text(case_id))


def max_case_number(case_ids) -> int:
    maximum = 0
    for case_id in case_ids:
        match = CASE_ID_SORT_RE.match(text(case_id))
        if match:
            maximum = max(maximum, int(match.group(2)))
    return maximum


def split_markdown_row(line: str) -> list[str]:
    return [cell.strip().replace("<br>", "\n") for cell in line.strip().strip("|").split("|")]


def is_case_id(value: str) -> bool:
    return bool(CASE_ID_RE.fullmatch(text(value)))


def parse_markdown_cases(content: str) -> tuple[dict, list[dict]]:
    """解析 Markdown 用例表，返回 (meta, cases)。"""
    lines = content.splitlines()
    column_map: dict[int, str] = {}
    cases: list[dict] = []
    title = ""

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") and not title:
            title = stripped[3:].strip()
        if stripped.startswith("|") and "用例ID" in stripped:
            headers = split_markdown_row(stripped)
            column_map = {
                index: HEADER_TO_FIELD[header]
                for index, header in enumerate(headers)
                if header in HEADER_TO_FIELD
            }
            continue
        if not column_map or not stripped.startswith("|"):
            continue
        if re.match(r"^\|\s*:?-{2,}", stripped):
            continue
        cells = split_markdown_row(stripped)
        case_id_index = next((index for index, field in column_map.items() if field == "id"), None)
        if case_id_index is None or case_id_index >= len(cells):
            continue
        if not is_case_id(cells[case_id_index]):
            continue
        case = {field: cells[index] if index < len(cells) else "" for index, field in column_map.items()}
        for field in FIELDS:
            case.setdefault(field, "")
        if not text(case.get("priority")):
            case["priority"] = default_priority_for_type(case.get("type", ""))
        cases.append(case)

    if not column_map:
        raise ValueError("Markdown 中未找到包含“用例ID”的表头")
    return {"project": title, "module": title}, cases


def load_markdown_file(path: Path) -> tuple[dict, list[dict]]:
    return parse_markdown_cases(path.read_text(encoding="utf-8-sig"))


def load_json_file(path: Path) -> tuple[dict, list[dict]]:
    data = load_json_robust(str(path))
    meta = data.get("meta", {}) if isinstance(data, dict) else {}
    cases = data.get("testcases", []) if isinstance(data, dict) else []
    if not isinstance(cases, list):
        raise ValueError("JSON 中 testcases 必须是数组")
    return meta if isinstance(meta, dict) else {}, cases


def load_cases(path: Path) -> tuple[dict, list[dict]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_json_file(path)
    if suffix == ".md":
        return load_markdown_file(path)
    raise ValueError("仅支持 .json 或 .md 输入")


def ensure_package(package: str, import_name: str | None = None) -> None:
    """按 requirements.lock 锁定版本安装缺失依赖。"""
    if import_name is None:
        import_name = package.replace("-", "_")
    expected = PINNED_DEPENDENCIES[package]
    requirement = f"{package}=={expected}"
    try:
        if version(package) == expected:
            __import__(import_name)
            return
    except (ImportError, PackageNotFoundError):
        pass

    try:
        print(f"[INSTALL] 正在安装 {requirement} ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", requirement, "-q"],
            stdout=subprocess.DEVNULL,
        )
        print(f"[INSTALL] {requirement} 安装完成")
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"无法安装锁定依赖 {requirement}") from error


def load_json_robust(filepath: str) -> dict:
    """加载 JSON；失败时用 json_repair 修复，兼容 LLM 常见格式错误。"""
    ensure_package("json-repair", "json_repair")
    from json_repair import repair_json

    with open(filepath, "r", encoding="utf-8") as handle:
        raw = handle.read()

    if not raw.strip():
        raise ValueError(f"文件为空: {filepath}")

    try:
        data = json.loads(raw)
        if isinstance(data, (dict, list)):
            return data if isinstance(data, dict) else {"testcases": data}
    except json.JSONDecodeError:
        pass

    repaired = repair_json(raw)
    data = json.loads(repaired)
    if isinstance(data, (dict, list)):
        return data if isinstance(data, dict) else {"testcases": data}
    raise ValueError(f"修复后的 JSON 格式异常: {type(data).__name__}")


def build_export_payload(
    cases: list[dict],
    *,
    project: str = "",
    module: str = "",
    generated_at: str = "",
) -> dict:
    from datetime import date

    normalized = []
    for case in cases:
        item = {field: text(case.get(field)) for field in FIELDS}
        if not item["priority"]:
            item["priority"] = default_priority_for_type(item["type"])
        normalized.append(item)
    normalized.sort(key=lambda case: case_sort_key(case.get("id", "")))

    return {
        "meta": {
            "project": project or "测试用例",
            "module": module or "",
            "generated_at": generated_at or date.today().isoformat(),
        },
        "testcases": normalized,
    }
