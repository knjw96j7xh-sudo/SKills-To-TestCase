#!/usr/bin/env python3
"""一键导出：质检 → MD→JSON → CSV/Excel/XMind，支持冒烟子集过滤。

用法:
    python3 export_all.py <2-用例定稿.md> --out-dir <目录> --formats j,e,x
    python3 export_all.py draft.md --out-dir out --formats e --priority P0,P1
    python3 export_all.py draft.md --out-dir out --formats j --ids TC-001,TC-005
    python3 export_all.py draft.md --out-dir out --formats x --module-filter 组织树
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from testcase_common import (
    build_export_payload,
    case_sort_key,
    load_markdown_file,
    text,
)

FORMAT_MAP = {
    "j": "jira",
    "jira": "jira",
    "csv": "jira",
    "e": "excel",
    "excel": "excel",
    "xlsx": "excel",
    "x": "xmind",
    "xmind": "xmind",
}


def filter_cases(
    cases: list[dict],
    *,
    priorities: set[str] | None,
    modules: set[str] | None,
    ids: set[str] | None,
) -> list[dict]:
    result = []
    for case in cases:
        cid = text(case.get("id"))
        if ids and cid not in ids:
            continue
        if priorities and text(case.get("priority")).upper() not in priorities:
            continue
        if modules:
            mod = text(case.get("module"))
            if not any(m in mod or mod == m for m in modules):
                continue
        result.append(case)
    result.sort(key=lambda c: case_sort_key(c.get("id", "")))
    return result


def write_filtered_md(cases: list[dict], path: Path, title: str) -> None:
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
    lines = [f"## {title}", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["--------"] * len(headers)) + "|")
    for case in cases:
        cells = []
        for key in keys:
            val = text(case.get(key)).replace("\n", "<br>")
            cells.append(val)
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_cmd(args: list[str]) -> int:
    print(f"[RUN] {' '.join(args)}")
    result = subprocess.run(args, check=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_md", type=Path, help="2-用例定稿.md")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="输出目录，默认与定稿同目录",
    )
    parser.add_argument(
        "--formats",
        default="j,e,x",
        help="导出格式：j/jira, e/excel, x/xmind，逗号分隔",
    )
    parser.add_argument("--project", default="", help="meta.project")
    parser.add_argument("--module", default="", help="meta.module")
    parser.add_argument(
        "--priority",
        default="",
        help="冒烟子集：优先级，如 P0,P1",
    )
    parser.add_argument(
        "--module-filter",
        default="",
        help="冒烟子集：所属模块关键字，逗号分隔",
    )
    parser.add_argument(
        "--ids",
        default="",
        help="冒烟子集：用例 ID，逗号分隔",
    )
    parser.add_argument(
        "--skip-quality",
        action="store_true",
        help="跳过质检（不推荐）",
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="质检不使用 --strict（WARN 也不阻断时用默认 strict）",
    )
    parser.add_argument(
        "--author",
        default="",
        help="Excel 默认编写人",
    )
    parser.add_argument(
        "--csv-tool",
        default="jira",
        choices=["jira", "tapd", "zentao"],
        help="CSV 工具模板，默认 jira",
    )
    args = parser.parse_args()

    input_md = args.input_md.resolve()
    if not input_md.is_file():
        print(f"[FAIL] 输入不存在: {input_md}")
        return 2

    out_dir = (args.out_dir or input_md.parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        meta, cases = load_markdown_file(input_md)
    except (OSError, ValueError) as error:
        print(f"[FAIL] 解析定稿失败: {error}")
        return 2

    priorities = {
        p.strip().upper() for p in args.priority.split(",") if p.strip()
    } or None
    modules = {
        m.strip() for m in args.module_filter.split(",") if m.strip()
    } or None
    ids = {i.strip() for i in args.ids.split(",") if i.strip()} or None

    filtered = filter_cases(
        cases, priorities=priorities, modules=modules, ids=ids
    )
    if not filtered:
        print("[FAIL] 过滤后无用例，请检查 --priority / --module-filter / --ids")
        return 1

    subset = bool(priorities or modules or ids)
    work_md = input_md
    if subset:
        work_md = out_dir / "2-用例定稿-子集.md"
        title = text(meta.get("module")) or text(meta.get("project")) or "用例子集"
        write_filtered_md(filtered, work_md, title)
        print(f"[OK] 子集定稿: {work_md}（{len(filtered)}/{len(cases)} 条）")

    scripts = _SCRIPTS_DIR
    audit = out_dir / "audit-summary.md"

    if not args.skip_quality:
        quality_cmd = [
            sys.executable,
            str(scripts / "testcase_quality.py"),
            str(work_md),
            "--audit-output",
            str(audit),
        ]
        if not args.no_strict:
            quality_cmd.append("--strict")
        code = run_cmd(quality_cmd)
        if code != 0:
            print("[FAIL] 质检未通过，已中止导出。请查看 audit-summary.md")
            return code

    project = text(args.project) or text(meta.get("project")) or "测试用例"
    module = text(args.module) or text(meta.get("module")) or ""
    export_json = out_dir / "export_data.json"
    payload = build_export_payload(
        filtered,
        project=project,
        module=module,
        generated_at=date.today().isoformat(),
    )
    export_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] JSON: {export_json}（{len(filtered)} 条）")

    formats_raw = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    formats = []
    for item in formats_raw:
        mapped = FORMAT_MAP.get(item)
        if not mapped:
            print(f"[FAIL] 未知格式: {item}（支持 j/e/x 或 jira/excel/xmind）")
            return 2
        if mapped not in formats:
            formats.append(mapped)

    if not formats:
        print("[FAIL] 未指定有效 --formats")
        return 2

    failed = 0
    excel_path = out_dir / ("testcases-smoke.xlsx" if subset else "testcases.xlsx")
    for fmt in formats:
        if fmt == "jira":
            csv_name = {
                "jira": "jira_export.csv",
                "tapd": "tapd_export.csv",
                "zentao": "zentao_export.csv",
            }[args.csv_tool]
            if subset:
                stem = Path(csv_name).stem
                csv_name = f"{stem}-smoke.csv"
            csv_path = out_dir / csv_name
            cmd = [
                sys.executable,
                str(scripts / "md_to_csv.py"),
                str(work_md),
                str(csv_path),
                "--tool",
                args.csv_tool,
            ]
            if run_cmd(cmd) != 0:
                failed += 1
        elif fmt == "excel":
            cmd = [
                sys.executable,
                str(scripts / "export_excel.py"),
                str(export_json),
                str(excel_path),
            ]
            if args.author:
                cmd.extend(["--author", args.author])
            if run_cmd(cmd) != 0:
                failed += 1
            else:
                # Excel 后再跑公式审计
                if not args.skip_quality:
                    run_cmd(
                        [
                            sys.executable,
                            str(scripts / "testcase_quality.py"),
                            str(export_json),
                            "--audit-output",
                            str(audit),
                            "--xlsx",
                            str(excel_path),
                        ]
                    )
        elif fmt == "xmind":
            xmind_path = out_dir / (
                "testcases-smoke.xmind" if subset else "testcases.xmind"
            )
            if (
                run_cmd(
                    [
                        sys.executable,
                        str(scripts / "export_xmind.py"),
                        str(export_json),
                        str(xmind_path),
                    ]
                )
                != 0
            ):
                failed += 1

    if failed:
        print(f"[FAIL] 有 {failed} 个导出步骤失败")
        return 1

    print(
        f"[OK] 导出完成：{len(filtered)} 条 → {out_dir}"
        + ("（冒烟子集）" if subset else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
