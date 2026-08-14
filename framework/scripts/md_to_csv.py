#!/usr/bin/env python3
"""将用例定稿 MD 转换为测试管理工具 CSV。

用法:
    python3 md_to_csv.py <input_md> <output_csv>
    python3 md_to_csv.py <input_md> <output_csv> --tool jira|tapd|zentao
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from testcase_common import load_markdown_file, priority_to_jira, text


def parse_steps(steps_text: str) -> list[tuple[str, str]]:
    """解析操作步骤文本，返回 (步骤编号, 动作) 列表。"""
    steps = []
    parts = re.split(r"(?:^|\s+)(\d+)\.\s+", steps_text or "")
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            step_no = parts[i]
            action = parts[i + 1].strip()
            if action:
                steps.append((step_no, action))
    return steps


def cases_to_export_rows(cases: list[dict], suite: str = "") -> list[dict]:
    rows = []
    for case in cases:
        steps = parse_steps(text(case.get("steps")))
        rows.append(
            {
                "case_id": text(case.get("id")),
                "title": text(case.get("test_point")),
                "preconditions": text(case.get("precondition")),
                "priority": priority_to_jira(
                    text(case.get("priority")), text(case.get("type"))
                ),
                "priority_raw": text(case.get("priority"))
                or priority_to_jira("", text(case.get("type"))),
                "steps": steps,
                "expected": text(case.get("expected")),
                "checkpoints": text(case.get("checkpoint")),
                "suite": suite,
                "scene_type": text(case.get("type")),
                "module": text(case.get("module")),
            }
        )
    return rows


def write_jira_csv(testcases: list[dict], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "序号",
                "标题",
                "描述",
                "优先级",
                "步骤ID",
                "步骤",
                "测试数据",
                "期望结果",
                "需求",
                "测试用例集",
            ]
        )
        for tc in testcases:
            if not tc["steps"]:
                writer.writerow(
                    [
                        tc["case_id"],
                        tc["title"],
                        tc["preconditions"],
                        tc["priority"],
                        "1",
                        tc["title"],
                        "",
                        tc["expected"],
                        tc["checkpoints"],
                        tc["suite"],
                    ]
                )
                continue
            first = True
            for step_no, action in tc["steps"]:
                if first:
                    writer.writerow(
                        [
                            tc["case_id"],
                            tc["title"],
                            tc["preconditions"],
                            tc["priority"],
                            step_no,
                            action,
                            "",
                            tc["expected"],
                            tc["checkpoints"],
                            tc["suite"],
                        ]
                    )
                    first = False
                else:
                    writer.writerow(
                        [
                            "",
                            "",
                            "",
                            tc["priority"],
                            step_no,
                            action,
                            "",
                            tc["expected"],
                            "",
                            "",
                        ]
                    )


def write_tapd_csv(testcases: list[dict], output_path: str) -> None:
    """Tapd 用例导入常用列（可按团队模板再调）。"""
    with open(output_path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "用例目录",
                "用例名称",
                "前置条件",
                "用例步骤",
                "预期结果",
                "用例类型",
                "优先级",
                "备注",
            ]
        )
        for tc in testcases:
            steps_text = "\n".join(
                f"{no}. {action}" for no, action in tc["steps"]
            ) or tc["title"]
            writer.writerow(
                [
                    tc["module"] or tc["suite"],
                    tc["title"],
                    tc["preconditions"],
                    steps_text,
                    tc["expected"],
                    tc["scene_type"] or "功能测试",
                    tc["priority_raw"] or tc["priority"],
                    tc["checkpoints"],
                ]
            )


def write_zentao_csv(testcases: list[dict], output_path: str) -> None:
    """禅道用例导入常用列。"""
    with open(output_path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "所属模块",
                "用例标题",
                "前置条件",
                "步骤",
                "预期",
                "关键词",
                "优先级",
                "用例类型",
                "适用阶段",
            ]
        )
        for tc in testcases:
            steps_text = "\n".join(
                f"{no}. {action}" for no, action in tc["steps"]
            ) or tc["title"]
            writer.writerow(
                [
                    tc["module"] or tc["suite"],
                    tc["title"],
                    tc["preconditions"],
                    steps_text,
                    tc["expected"],
                    tc["checkpoints"],
                    tc["priority_raw"] or tc["priority"],
                    tc["scene_type"] or "功能",
                    "功能测试阶段",
                ]
            )


WRITERS = {
    "jira": write_jira_csv,
    "tapd": write_tapd_csv,
    "zentao": write_zentao_csv,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_md", help="2-用例定稿.md")
    parser.add_argument("output_csv", help="输出 CSV 路径")
    parser.add_argument(
        "--tool",
        default="jira",
        choices=sorted(WRITERS.keys()),
        help="目标工具模板：jira / tapd / zentao",
    )
    args = parser.parse_args()

    input_path = args.input_md
    output_path = args.output_csv

    if not os.path.exists(input_path):
        print(f"[FAIL] 输入文件不存在: {input_path}")
        return 1
    if not input_path.endswith(".md"):
        print(f"[WARN] 输入文件不是 .md 格式: {input_path}")

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as error:
            print(f"[FAIL] 无法创建输出目录: {error}")
            return 1

    try:
        meta, cases = load_markdown_file(Path(input_path))
    except UnicodeDecodeError:
        print(f"[FAIL] 文件编码错误，请确保为 UTF-8: {input_path}")
        return 1
    except (OSError, ValueError) as error:
        print(f"[FAIL] {error}")
        return 1

    suite = text(meta.get("module")) or text(meta.get("project"))
    testcases = cases_to_export_rows(cases, suite=suite)
    if not testcases:
        print("[WARN] 未解析到任何用例，请检查 MD 文件格式是否正确")
        return 1

    try:
        WRITERS[args.tool](testcases, output_path)
    except PermissionError:
        print(f"[FAIL] 无写入权限: {output_path}")
        return 1
    except OSError as error:
        print(f"[FAIL] 写入 CSV 失败: {error}")
        return 1

    print(f"[OK] 已生成 {args.tool} CSV: {output_path}")
    print(f"  用例总数: {len(testcases)} 条")
    print("  编码: UTF-8 with BOM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
