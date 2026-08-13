#!/usr/bin/env python3
"""将用例定稿 Markdown 转换为 export_data.json。

用法:
    python3 md_to_json.py <input.md> <output.json> [--project NAME] [--module NAME]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from testcase_common import build_export_payload, load_markdown_file, text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="2-用例定稿.md 或含用例表的 Markdown")
    parser.add_argument("output", type=Path, help="export_data.json 输出路径")
    parser.add_argument("--project", default="", help="meta.project，默认取文内一级标题")
    parser.add_argument("--module", default="", help="meta.module，默认取文内标题或空")
    parser.add_argument("--generated-at", default="", help="meta.generated_at，默认今天")
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"[FAIL] 输入文件不存在: {args.input}")
        return 2

    try:
        meta, cases = load_markdown_file(args.input)
    except (OSError, ValueError) as error:
        print(f"[FAIL] {error}")
        return 2

    if not cases:
        print("[FAIL] 未解析到任何用例，请检查 Markdown 表格格式")
        return 1

    project = text(args.project) or text(meta.get("project")) or "测试用例"
    module = text(args.module) or text(meta.get("module")) or ""
    generated_at = text(args.generated_at) or date.today().isoformat()
    payload = build_export_payload(
        cases,
        project=project,
        module=module,
        generated_at=generated_at,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] JSON 已生成: {args.output}（共 {len(cases)} 条用例）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
