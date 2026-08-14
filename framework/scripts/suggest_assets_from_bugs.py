#!/usr/bin/env python3
"""从缺陷列表生成检查点/评审点候选（需人确认后追加，不自动写入 index）。

用法:
    python3 suggest_assets_from_bugs.py bugs.txt
    python3 suggest_assets_from_bugs.py bugs.md --prefix BUG --kind review
    python3 suggest_assets_from_bugs.py bugs.txt --checkpoints-index .testcase-assets/checkpoints-index.md

输入每行一条缺陷，支持：
  - 纯描述
  - ID\\t描述 或 ID: 描述 或 #123 描述
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

LINE_RE = re.compile(
    r"^(?:[#\[]?)(?P<id>[A-Za-z]*-?\d+)?[\]:\s\t.-]*(?P<title>.+)$"
)
MAX_ID_RE = re.compile(r"\[([A-Za-z]+)-(\d+)\]")


def parse_bug_lines(text: str) -> list[dict]:
    bugs = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") and len(line) < 4:
            # 允许 markdown 标题跳过；短 # 可能是编号
            if line.startswith("##"):
                continue
        if not line:
            continue
        match = LINE_RE.match(line)
        if not match:
            continue
        bug_id = (match.group("id") or "").strip()
        title = (match.group("title") or line).strip()
        if not title:
            continue
        bugs.append({"source_id": bug_id, "title": title})
    return bugs


def next_prefix_number(index_text: str, prefix: str) -> int:
    maximum = 0
    for match in MAX_ID_RE.finditer(index_text or ""):
        if match.group(1).upper() == prefix.upper():
            maximum = max(maximum, int(match.group(2)))
    return maximum + 1


def build_candidates(
    bugs: list[dict],
    *,
    prefix: str,
    start: int,
    kind: str,
) -> list[dict]:
    rows = []
    number = start
    for bug in bugs:
        asset_id = f"{prefix}-{number:02d}" if number < 100 else f"{prefix}-{number}"
        number += 1
        desc = bug["title"]
        if bug["source_id"]:
            source = bug["source_id"]
        else:
            source = "缺陷列表"
        if kind == "checkpoint":
            description = f"回归覆盖：{desc}（来源 {source}）"
        else:
            description = f"缺陷回归评审：{desc}（来源 {source}）"
        rows.append(
            {
                "id": asset_id,
                "description": description,
                "source": source,
                "title": desc,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="缺陷列表文本/Markdown")
    parser.add_argument(
        "--kind",
        choices=["review", "checkpoint", "both"],
        default="review",
        help="生成评审点 / 检查点 / 两者",
    )
    parser.add_argument("--prefix", default="BUG", help="编号前缀，默认 BUG")
    parser.add_argument(
        "--checkpoints-index",
        type=Path,
        default=None,
        help="用于读取已有最大编号",
    )
    parser.add_argument(
        "--review-index",
        type=Path,
        default=None,
        help="用于读取已有最大编号",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="写出候选 Markdown；默认打印到 stdout",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"[FAIL] 输入不存在: {args.input}")
        return 2

    bugs = parse_bug_lines(args.input.read_text(encoding="utf-8-sig"))
    if not bugs:
        print("[FAIL] 未解析到缺陷行")
        return 1

    cp_text = ""
    rev_text = ""
    if args.checkpoints_index and args.checkpoints_index.is_file():
        cp_text = args.checkpoints_index.read_text(encoding="utf-8")
    if args.review_index and args.review_index.is_file():
        rev_text = args.review_index.read_text(encoding="utf-8")

    lines = [
        "# 缺陷沉淀候选（请确认后追加，禁止脚本自动写入 index）",
        "",
        f"- 来源文件：`{args.input}`",
        f"- 解析条数：{len(bugs)}",
        "",
    ]

    kinds = []
    if args.kind in ("checkpoint", "both"):
        kinds.append("checkpoint")
    if args.kind in ("review", "both"):
        kinds.append("review")

    for kind in kinds:
        index_text = cp_text if kind == "checkpoint" else rev_text
        start = next_prefix_number(index_text, args.prefix)
        candidates = build_candidates(
            bugs, prefix=args.prefix, start=start, kind=kind
        )
        label = "检查点" if kind == "checkpoint" else "评审点"
        lines.append(f"## 建议追加的{label}")
        lines.append("")
        lines.append("| 编号 | 描述 | 来源 |")
        lines.append("|------|------|------|")
        for row in candidates:
            lines.append(
                f"| {row['id']} | {row['description']} | {row['source']} |"
            )
        lines.append("")
        lines.append("确认后：")
        if kind == "checkpoint":
            lines.append(
                "- 将上表追加到 `checkpoints-index.md` 对应分类末尾，编号只增不改。"
            )
        else:
            lines.append(
                "- 将上表追加到 `review-expectations-index.md` 的 BUG 或合适分类末尾。"
            )
        lines.append("")

    output = "\n".join(lines)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"[OK] 候选已写入: {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
