#!/usr/bin/env python3
"""阶段产物门禁：不信 Agent 自述，只认退出码与磁盘产物。

用法:
    python3 gate_stage.py --stage init
    python3 gate_stage.py --stage merge --run-dir history/xxx
    python3 gate_stage.py --stage draft --run-dir history/xxx
    python3 gate_stage.py --stage export --run-dir history/xxx --formats e,x,j
    python3 gate_stage.py --stage prepare --run-dir history/xxx

退出码 0=过关；1=未过关；2=参数错误。
过关时打印 [GATE OK]；失败打印 [GATE FAIL] 与缺失项。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from check_environment import run_checks
from framework_versions import check_versions, find_version_file

CASE_ID_RE = re.compile(r"[A-Za-z]+-\d+[A-Za-z]*")


def _resolve_run_dir(path: Path | None) -> Path | None:
    if path is None:
        return None
    p = path.resolve()
    if p.is_file():
        return p.parent
    return p


def _has_case_table(md_path: Path) -> bool:
    if not md_path.is_file():
        return False
    text = md_path.read_text(encoding="utf-8-sig", errors="replace")
    if "用例ID" not in text:
        return False
    return bool(CASE_ID_RE.search(text))


def _audit_has_blocking_error(audit_path: Path) -> bool:
    if not audit_path.is_file():
        return True
    text = audit_path.read_text(encoding="utf-8", errors="replace")
    # 简单启发式：出现 ERROR 计数且非 0
    if re.search(r"ERROR\s*[:：]\s*0\b", text, re.I):
        return False
    if re.search(r"\bERROR\b", text) and re.search(
        r"(阻断|失败|ERROR\s*[:：]\s*[1-9])", text
    ):
        return True
    # 无明确统计时：存在 audit 且含 [ERROR] 行
    if re.search(r"^\[ERROR\]", text, re.M):
        return True
    return False


def gate_init(start: Path) -> list[str]:
    fails: list[str] = []
    ok, lines, _ = run_checks(start)
    if not ok:
        fails.append("环境体检未通过（见上方 check_environment 输出）")
        # 仍把关键信息留给调用方：gate 会再打一遍精简
        for line in lines:
            if line.startswith("[FAIL]"):
                fails.append(line)
    ok_ver, _ = check_versions(find_version_file(start))
    if not ok_ver:
        fails.append("框架版本检查未通过")
    return fails


def gate_prepare(run_dir: Path) -> list[str]:
    fails = []
    path = run_dir / "0-用例准备.md"
    if not path.is_file():
        fails.append(f"缺少 {path.name}")
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "测试对象" not in text and "需求要素" not in text:
            fails.append("0-用例准备.md 内容过短或缺少需求要素")
    return fails


def gate_merge(run_dir: Path) -> list[str]:
    fails = []
    changeset = run_dir / "1-变更集.md"
    merged = run_dir / "1-评审记要.md"
    if not changeset.is_file():
        fails.append("缺少 1-变更集.md")
    else:
        text = changeset.read_text(encoding="utf-8", errors="replace")
        for section in ("新增", "修改", "废弃"):
            if f"### {section}" not in text and f"## {section}" not in text:
                # 允许只有部分小节，但至少有一个
                pass
        if "### 新增" not in text and "### 修改" not in text and "### 废弃" not in text:
            fails.append("1-变更集.md 缺少 ### 新增/修改/废弃 小节")
    if not merged.is_file():
        fails.append("缺少 1-评审记要.md（须先跑 merge_cases.py）")
    elif not _has_case_table(merged):
        fails.append("1-评审记要.md 未解析到用例表")
    # 合并摘要痕迹（merge_cases 会写）
    if merged.is_file():
        text = merged.read_text(encoding="utf-8", errors="replace")
        if "变更合并摘要" not in text and "合并后有效" not in text:
            fails.append(
                "1-评审记要.md 未见 merge_cases 摘要，疑似未走脚本合并"
            )
    return fails


def gate_draft(run_dir: Path) -> list[str]:
    fails = []
    draft = run_dir / "2-用例定稿.md"
    if not draft.is_file():
        fails.append("缺少 2-用例定稿.md")
    elif not _has_case_table(draft):
        fails.append("2-用例定稿.md 未解析到用例表")
    return fails


def gate_export(run_dir: Path, formats: list[str]) -> list[str]:
    fails = gate_draft(run_dir)
    audit = run_dir / "audit-summary.md"
    if not audit.is_file():
        fails.append("缺少 audit-summary.md（须先质检）")
    elif _audit_has_blocking_error(audit):
        # 宽松：有 audit 即可；若明确有 ERROR 行则失败
        if re.search(
            r"^\[ERROR\]",
            audit.read_text(encoding="utf-8", errors="replace"),
            re.M,
        ):
            fails.append("audit-summary.md 仍含 [ERROR]，须先修复定稿")

    fmt_set = set(formats)
    if fmt_set & {"e", "excel", "x", "xmind"}:
        if not (run_dir / "export_data.json").is_file():
            fails.append("缺少 export_data.json（须 md_to_json 或 export_all）")
    if fmt_set & {"e", "excel"}:
        xlsx = list(run_dir.glob("testcases*.xlsx"))
        if not xlsx:
            fails.append("缺少 testcases.xlsx / testcases-smoke.xlsx")
    if fmt_set & {"x", "xmind"}:
        xmind = list(run_dir.glob("testcases*.xmind"))
        if not xmind:
            fails.append("缺少 testcases.xmind / testcases-smoke.xmind")
    if fmt_set & {"j", "jira", "csv", "tapd", "zentao"}:
        csvs = list(run_dir.glob("*export*.csv")) + list(run_dir.glob("jira_export*.csv"))
        if not csvs:
            fails.append("缺少 *export*.csv")
    return fails


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        required=True,
        choices=["init", "prepare", "merge", "draft", "export"],
        help="门禁阶段",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="运行目录 history/<run>/",
    )
    parser.add_argument(
        "--formats",
        default="j,e,x",
        help="export 阶段期望格式：j,e,x",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("."),
        help="init 阶段项目路径",
    )
    args = parser.parse_args()

    run_dir = _resolve_run_dir(args.run_dir)
    fails: list[str] = []

    if args.stage == "init":
        fails = gate_init(args.path.resolve())
    elif args.stage in ("prepare", "merge", "draft", "export"):
        if run_dir is None or not run_dir.is_dir():
            print("[GATE FAIL] 需要有效的 --run-dir")
            return 2
        if args.stage == "prepare":
            fails = gate_prepare(run_dir)
        elif args.stage == "merge":
            fails = gate_merge(run_dir)
        elif args.stage == "draft":
            fails = gate_draft(run_dir)
        else:
            formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
            fails = gate_export(run_dir, formats)
    else:
        print(f"[GATE FAIL] 未知阶段: {args.stage}")
        return 2

    if fails:
        print(f"[GATE FAIL] stage={args.stage}")
        for item in fails:
            print(f"  - {item}")
        print("  修复后重跑本命令；未过关不得进入下一阶段。")
        return 1

    print(f"[GATE OK] stage={args.stage}")
    if run_dir:
        print(f"  run-dir: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
