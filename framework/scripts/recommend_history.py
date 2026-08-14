#!/usr/bin/env python3
"""历史复用两级召回：先目录，再用例。

用法:
    # 一级：列候选 history 目录
    python3 recommend_history.py --history-root .testcase-assets/history \\
      --module "组织树" --list-dirs

    # 二级：在指定目录下列用例摘要
    python3 recommend_history.py --history-root .testcase-assets/history \\
      --dir 20260721_xxx --list-cases
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from testcase_common import load_markdown_file, text

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_aliases(rules_path: Path | None) -> dict[str, list[str]]:
    if not rules_path or not rules_path.is_file() or yaml is None:
        return {}
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    return data.get("module_alias") or {}


def score_dir(name: str, module: str, aliases: dict[str, list[str]]) -> tuple[int, str]:
    score = 0
    reasons = []
    name_l = name.lower()
    module_l = module.lower()
    if module_l and module_l in name_l:
        score += 5
        reasons.append(f"目录含模块「{module}」")
    for key, words in aliases.items():
        if key.lower() in module_l or key.lower() in name_l:
            for w in words:
                if str(w).lower() in name_l:
                    score += 3
                    reasons.append(f"别名「{w}」")
                    break
    # 分词粗匹配
    for token in re.findall(r"[\u4e00-\u9fff]{2,}", module):
        if token in name:
            score += 2
            reasons.append(f"字面「{token}」")
    return score, "；".join(reasons[:3]) or "弱相关"


def list_dirs(history_root: Path, module: str, aliases: dict, limit: int) -> list[dict]:
    rows = []
    if not history_root.is_dir():
        return rows
    for path in sorted(history_root.iterdir(), reverse=True):
        if not path.is_dir():
            continue
        draft = path / "2-用例定稿.md"
        if not draft.is_file():
            continue
        score, reason = score_dir(path.name, module, aliases)
        try:
            _meta, cases = load_markdown_file(draft)
            count = len(cases)
        except (OSError, ValueError):
            count = 0
        rows.append(
            {
                "dir": path.name,
                "path": str(path),
                "score": score,
                "reason": reason,
                "count": count,
            }
        )
    rows.sort(key=lambda r: (-r["score"], r["dir"]))
    # 无分数时仍返回最近 limit 个（目录名已 reverse 扫描，保持原序再截断）
    strong = [r for r in rows if r["score"] > 0]
    if strong:
        return strong[:limit]
    return rows[:limit]


def list_cases(run_dir: Path, keyword: str = "", limit: int = 30) -> list[dict]:
    draft = run_dir / "2-用例定稿.md"
    if not draft.is_file():
        return []
    _meta, cases = load_markdown_file(draft)
    rows = []
    for case in cases:
        title = text(case.get("test_point"))
        if keyword and keyword not in title and keyword not in text(case.get("module")):
            continue
        rows.append(
            {
                "id": text(case.get("id")),
                "test_point": title,
                "type": text(case.get("type")),
                "priority": text(case.get("priority")),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-root", type=Path, required=True)
    parser.add_argument("--module", default="", help="当前测试对象/模块名")
    parser.add_argument("--rules", type=Path, default=None)
    parser.add_argument("--list-dirs", action="store_true")
    parser.add_argument("--dir", default="", help="history 子目录名")
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--keyword", default="", help="二级筛选测试点关键字")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    aliases = load_aliases(args.rules)
    lines: list[str] = []

    if args.list_dirs:
        rows = list_dirs(args.history_root, args.module, aliases, args.limit)
        lines.append("# 历史目录候选（一级）")
        lines.append("")
        lines.append(f"- 模块线索：{args.module or '（未提供）'}")
        lines.append("")
        if not rows:
            lines.append("（无 history 定稿）")
        for i, row in enumerate(rows, start=1):
            lines.append(
                f"[{i}] `{row['dir']}`  {row['count']} 条  ← {row['reason']}（分 {row['score']}）"
            )
        lines.append("")
        lines.append("请选择目录编号，或回复“跳过”。选定后再列用例。")
    elif args.list_cases:
        if not args.dir:
            print("[FAIL] --list-cases 需要 --dir")
            return 2
        run_dir = args.history_root / args.dir
        if not run_dir.is_dir():
            run_dir = Path(args.dir)
        rows = list_cases(run_dir, keyword=args.keyword, limit=max(args.limit, 30))
        lines.append(f"# 历史用例候选（二级）— `{run_dir.name}`")
        lines.append("")
        if not rows:
            lines.append("（无用例或关键字无匹配）")
        for i, row in enumerate(rows, start=1):
            lines.append(
                f"[{i}] {row['id']}  {row['test_point']}  {row['type']}  {row['priority']}"
            )
        lines.append("")
        lines.append("请输入要复用的编号（可多选），或“跳过”。未经勾选不得复制。")
    else:
        print("[FAIL] 请指定 --list-dirs 或 --list-cases")
        return 2

    output = "\n".join(lines) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"[OK] 已写入: {args.output}")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
