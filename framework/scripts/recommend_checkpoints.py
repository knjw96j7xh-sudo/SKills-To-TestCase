#!/usr/bin/env python3
"""基于规则推荐检查点（可解释命中原因）。

用法:
    python3 recommend_checkpoints.py \\
      --checkpoints .testcase-assets/checkpoints-index.md \\
      --text "支持列表分页与附件上传" \\
      --rules .testcase-assets/recommend-rules.yaml

输出 Markdown，供阶段 2a 展示；不自动写入 index。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

CP_LINE_RE = re.compile(
    r"^\s*[-*]\s*\[(?P<id>[A-Za-z]+-\d+)\]\s*(?P<desc>.+?)\s*$"
)
DEFAULT_RULES = {
    "max_recommend": 15,
    "domain_keywords": {
        "列表": ["LIST", "列表", "分页", "筛选", "搜索"],
        "文件": ["FILE", "上传", "下载", "附件", "预览"],
        "风险": ["RISK", "并发", "权限", "越权", "超时"],
        "接口": ["API", "鉴权", "幂等", "参数"],
        "用户": ["UC", "登录", "注册", "验证码"],
    },
    "design_signals": {
        "分页": ["LIST"],
        "上传": ["FILE"],
        "下载": ["FILE"],
        "权限": ["RISK"],
        "角色": ["RISK", "UC"],
        "并发": ["RISK"],
        "接口": ["API"],
        "表单": ["UC", "LIST"],
        "导出": ["FILE", "LIST"],
    },
    "module_alias": {},
}


def load_rules(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return dict(DEFAULT_RULES)
    if yaml is None:
        return dict(DEFAULT_RULES)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    merged = dict(DEFAULT_RULES)
    for key in ("max_recommend", "domain_keywords", "design_signals", "module_alias"):
        if key in data and data[key] is not None:
            merged[key] = data[key]
    return merged


def parse_checkpoints(index_text: str) -> list[dict]:
    items = []
    current_category = ""
    for line in index_text.splitlines():
        heading = re.match(r"^#{2,3}\s+(.+)$", line.strip())
        if heading:
            current_category = heading.group(1).strip()
            continue
        match = CP_LINE_RE.match(line)
        if not match:
            # 兼容 | UC-01 | 描述 |
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and re.match(r"^[A-Za-z]+-\d+$", cells[0]):
                cp_id, desc = cells[0], cells[1]
            else:
                continue
        else:
            cp_id, desc = match.group("id"), match.group("desc")
        if "[已废弃]" in desc:
            continue
        items.append(
            {
                "id": cp_id,
                "desc": desc.strip(),
                "category": current_category,
                "prefix": cp_id.split("-")[0].upper(),
            }
        )
    return items


def score_checkpoint(item: dict, corpus: str, rules: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    corpus_l = corpus.lower()
    prefix = item["prefix"]
    blob = f"{item['id']} {item['desc']} {item['category']}".lower()

    for domain, keywords in (rules.get("domain_keywords") or {}).items():
        domain_hit = False
        for kw in keywords:
            kw_s = str(kw)
            kw_l = kw_s.lower()
            if kw_l not in corpus_l and kw_s.upper() not in corpus.upper():
                continue
            # 语料命中关键词后，检查点前缀或描述/分类相关则加分
            if prefix == kw_s.upper() or kw_l in blob or kw_s.upper() in item["id"].upper():
                score += 3
                reasons.append(f"域「{domain}」词「{kw}」→ {prefix}")
                domain_hit = True
                break
            if kw_l in corpus_l and (
                any(str(x).upper() == prefix for x in keywords if re.match(r"^[A-Za-z]+$", str(x)))
            ):
                score += 2
                reasons.append(f"域「{domain}」语料命中「{kw}」")
                domain_hit = True
                break
        if domain_hit:
            continue

    for signal, prefixes in (rules.get("design_signals") or {}).items():
        if str(signal).lower() in corpus_l:
            for p in prefixes:
                if prefix == str(p).upper():
                    score += 3
                    reasons.append(f"设计信号「{signal}」→ {p}")
                    break

    for token in re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", item["desc"]):
        if token.lower() in corpus_l:
            score += 1
            reasons.append(f"描述重合「{token}」")
            if len(reasons) >= 6:
                break

    seen: set[str] = set()
    uniq: list[str] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            uniq.append(reason)
    return score, uniq[:4]


def recommend(items: list[dict], corpus: str, rules: dict) -> list[dict]:
    ranked = []
    for item in items:
        score, reasons = score_checkpoint(item, corpus, rules)
        if score <= 0:
            continue
        ranked.append({**item, "score": score, "reasons": reasons})
    ranked.sort(key=lambda x: (-x["score"], x["id"]))
    limit = int(rules.get("max_recommend") or 15)
    return ranked[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument(
        "--text",
        default="",
        help="需求/设计摘要文本；也可用 --text-file",
    )
    parser.add_argument("--text-file", type=Path, default=None)
    parser.add_argument("--rules", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.checkpoints.is_file():
        print(f"[FAIL] 检查点索引不存在: {args.checkpoints}")
        return 2

    corpus = args.text
    if args.text_file and args.text_file.is_file():
        corpus = args.text_file.read_text(encoding="utf-8")
    if not corpus.strip():
        print("[FAIL] 请提供 --text 或 --text-file")
        return 2

    rules = load_rules(args.rules)
    items = parse_checkpoints(args.checkpoints.read_text(encoding="utf-8"))
    if not items:
        print("[FAIL] 未解析到检查点（期望 `- [UC-01] 描述` 或表格行）")
        return 1

    picks = recommend(items, corpus, rules)
    pick_ids = {p["id"] for p in picks}

    lines = [
        "# 检查点推荐（请确认，勿静默全选）",
        "",
        f"- 规则文件：`{args.rules or '内置默认'}`",
        f"- 推荐 {len(picks)} / 全部 {len(items)} 条",
        "",
        "## 预推荐",
        "",
    ]
    if not picks:
        lines.append("（无强命中，请手选或全选）")
    for p in picks:
        reason = "；".join(p["reasons"]) if p["reasons"] else "规则命中"
        lines.append(f"- [*] {p['id']}  {p['desc']}  ← {reason}")

    lines.extend(["", "## 未推荐（可手选）", ""])
    shown = 0
    for item in items:
        if item["id"] in pick_ids:
            continue
        lines.append(f"- [ ] {item['id']}  {item['desc']}")
        shown += 1
        if shown >= 40:
            lines.append(f"- … 其余 {len(items) - len(pick_ids) - shown} 条见索引全文")
            break

    lines.extend(
        [
            "",
            "请回复：采用推荐 / 编号列表 / 全选 / 跳过",
            "",
        ]
    )
    output = "\n".join(lines)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"[OK] 推荐已写入: {args.output}（{len(picks)} 条）")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
