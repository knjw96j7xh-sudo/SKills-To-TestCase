#!/usr/bin/env python3
"""增量变更合并：基线定稿 + 变更集 → 完整有效用例表。

用法:
    python3 merge_cases.py \
      --baseline history/旧/2-用例定稿.md \
      --changeset history/新/1-变更集.md \
      --output history/新/1-评审记要.md

变更集须含「### 新增」「### 修改」「### 废弃」小节（表格）。
废弃表至少含「用例ID」列；新增/修改为完整用例表列。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from testcase_common import (
    FIELDS,
    HEADER_TO_FIELD,
    case_sort_key,
    is_case_id,
    load_markdown_file,
    split_markdown_row,
    text,
)

SECTION_RE = re.compile(r"^###\s+(新增|修改|废弃)\s*$")


def _parse_table_block(lines: list[str]) -> list[dict]:
    """从若干行中解析第一个 Markdown 表为 case dict 列表。"""
    column_map: dict[int, str] = {}
    rows: list[dict] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and ("用例ID" in stripped or "用例 Id" in stripped):
            headers = split_markdown_row(stripped)
            column_map = {
                index: HEADER_TO_FIELD.get(header, header)
                for index, header in enumerate(headers)
            }
            # 规范化：未知中文头尽量映射
            for index, header in enumerate(headers):
                if header in HEADER_TO_FIELD:
                    column_map[index] = HEADER_TO_FIELD[header]
                elif header in ("废弃原因", "原因"):
                    column_map[index] = "retire_reason"
                elif header == "测试点":
                    column_map[index] = "test_point"
            continue
        if not column_map or not stripped.startswith("|"):
            continue
        if re.match(r"^\|\s*:?-{2,}", stripped):
            continue
        cells = split_markdown_row(stripped)
        case: dict = {}
        for index, field in column_map.items():
            case[field] = cells[index] if index < len(cells) else ""
        cid = text(case.get("id") or case.get("用例ID"))
        if not cid and "id" not in case:
            # 找第一列像 ID 的
            for value in case.values():
                if is_case_id(text(value)):
                    cid = text(value)
                    case["id"] = cid
                    break
        else:
            case["id"] = cid
        if not is_case_id(case.get("id", "")):
            continue
        for field in FIELDS:
            case.setdefault(field, "")
        rows.append(case)
    return rows


def parse_changeset(path: Path) -> dict[str, list[dict]]:
    content = path.read_text(encoding="utf-8-sig")
    lines = content.splitlines()
    sections: dict[str, list[str]] = {"新增": [], "修改": [], "废弃": []}
    current: str | None = None
    for line in lines:
        match = SECTION_RE.match(line.strip())
        if match:
            current = match.group(1)
            continue
        if current:
            sections[current].append(line)

    result = {
        "add": _parse_table_block(sections["新增"]),
        "modify": _parse_table_block(sections["修改"]),
        "retire": _parse_table_block(sections["废弃"]),
    }
    return result


def merge_cases(
    baseline: list[dict],
    add: list[dict],
    modify: list[dict],
    retire: list[dict],
) -> tuple[list[dict], list[str]]:
    """返回 (合并后用例, 错误列表)。错误非空时调用方应失败。"""
    errors: list[str] = []
    by_id: dict[str, dict] = {}
    for case in baseline:
        cid = text(case.get("id"))
        if not cid:
            continue
        if cid in by_id:
            errors.append(f"基线重复 ID: {cid}")
        by_id[cid] = dict(case)

    retire_ids = []
    for case in retire:
        cid = text(case.get("id"))
        if not cid:
            errors.append("废弃表存在空用例ID")
            continue
        if cid not in by_id:
            errors.append(f"废弃 ID 不在基线: {cid}")
            continue
        retire_ids.append(cid)

    for cid in retire_ids:
        by_id.pop(cid, None)

    for case in modify:
        cid = text(case.get("id"))
        if not cid:
            errors.append("修改表存在空用例ID")
            continue
        if cid in retire_ids:
            errors.append(f"修改 ID 已在废弃列表: {cid}")
            continue
        if cid not in by_id:
            errors.append(f"修改 ID 不在基线: {cid}")
            continue
        # 禁止改号：变更集行 ID 即目标 ID
        row = dict(case)
        for field in FIELDS:
            row.setdefault(field, "")
        row["remark"] = ""
        by_id[cid] = row

    baseline_ids = {text(c.get("id")) for c in baseline}
    for case in add:
        cid = text(case.get("id"))
        if not cid:
            errors.append("新增表存在空用例ID")
            continue
        if cid in baseline_ids and cid not in retire_ids:
            errors.append(f"新增 ID 与基线冲突: {cid}")
            continue
        if cid in by_id:
            errors.append(f"新增 ID 冲突: {cid}")
            continue
        row = dict(case)
        for field in FIELDS:
            row.setdefault(field, "")
        # 生成链路备注强制空
        row["remark"] = ""
        by_id[cid] = row

    merged = sorted(by_id.values(), key=lambda c: case_sort_key(c.get("id", "")))
    return merged, errors


def cases_to_markdown(
    cases: list[dict],
    *,
    title: str,
    summary_lines: list[str] | None = None,
) -> str:
    headers = [
        "用例ID",
        "所属模块",
        "测试点",
        "前置条件",
        "操作步骤",
        "预期结果",
        "关联检查点",
        "场景类型",
        "优先级",
        "备注",
    ]
    keys = [
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
    ]
    lines: list[str] = []
    if summary_lines:
        lines.extend(summary_lines)
        lines.append("")
    lines.append(f"## {title}")
    lines.append("")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["--------"] * len(headers)) + "|")
    for case in cases:
        cells = [text(case.get(k)).replace("\n", "<br>") for k in keys]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="基线 2-用例定稿.md")
    parser.add_argument("--changeset", type=Path, required=True, help="1-变更集.md")
    parser.add_argument("--output", type=Path, required=True, help="合并输出 MD")
    parser.add_argument("--title", default="", help="输出表标题，默认取基线标题")
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="存在校验错误时仍写出结果（默认失败不写）",
    )
    args = parser.parse_args()

    if not args.baseline.is_file():
        print(f"[FAIL] 基线不存在: {args.baseline}")
        return 2
    if not args.changeset.is_file():
        print(f"[FAIL] 变更集不存在: {args.changeset}")
        return 2

    try:
        meta, baseline = load_markdown_file(args.baseline)
    except (OSError, ValueError) as error:
        print(f"[FAIL] 基线解析失败: {error}")
        return 2

    try:
        parts = parse_changeset(args.changeset)
    except (OSError, ValueError) as error:
        print(f"[FAIL] 变更集解析失败: {error}")
        return 2

    add, modify, retire = parts["add"], parts["modify"], parts["retire"]
    print(
        f"[INFO] 基线 {len(baseline)} 条 | 新增 {len(add)} | 修改 {len(modify)} | 废弃 {len(retire)}"
    )

    merged, errors = merge_cases(baseline, add, modify, retire)
    for err in errors:
        print(f"[ERROR] {err}")

    if errors and not args.allow_warnings:
        print(f"[FAIL] 合并校验失败（{len(errors)} 项），未写入输出")
        return 1

    title = text(args.title) or text(meta.get("module")) or text(meta.get("project")) or "用例表"
    summary = [
        "## 变更合并摘要",
        f"- 基线：`{args.baseline}`（{len(baseline)} 条）",
        f"- 新增：{', '.join(text(c.get('id')) for c in add) or '无'}",
        f"- 修改：{', '.join(text(c.get('id')) for c in modify) or '无'}",
        f"- 废弃：{', '.join(text(c.get('id')) for c in retire) or '无'}",
        f"- 合并后有效：{len(merged)} 条",
    ]
    if errors:
        summary.append(f"- 校验问题：{len(errors)}（已 --allow-warnings 输出）")

    md = cases_to_markdown(merged, title=title, summary_lines=summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    print(f"[OK] 已写入: {args.output}（有效 {len(merged)} 条）")
    return 0 if not errors else (0 if args.allow_warnings else 1)


if __name__ == "__main__":
    raise SystemExit(main())
