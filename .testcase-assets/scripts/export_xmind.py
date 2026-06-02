#!/usr/bin/env python3
"""
export_xmind.py — 将测试用例 JSON 导出为 XMind (.xmind) 文件

用法：
    python3 export_xmind.py <input_json> <output_xmind>

思维导图结构（四级）：
  [项目名称]
  ├── [检查点 XX-01]
  │   ├── 正向场景
  │   │   ├── TC-001  测试点描述
  │   │   │   ├── 前置条件
  │   │   │   ├── 1. 步骤一
  │   │   │   ├── 2. 步骤二
  │   │   │   └── 预期结果
  │   │   └── ...
  │   └── 异常场景
  │       └── ...
  └── ...

Sheet 2：统计总览
  [统计总览]
  ├── 正向场景 (N条)
  │   ├── XX-01 (N条)
  │   └── ...
  └── 异常场景 ...
"""

import sys
import json
import zipfile
import uuid
from datetime import datetime, timezone
from collections import defaultdict

# ─── 颜色常量 ──────────────────────────────────────────────────────────────────

ROOT_COLOR = "#1E3A5F"       # 根节点深蓝

# 检查点分支色（循环使用）
CHECKPOINT_COLORS = [
    "#1565C0", "#6A1B9A", "#00695C", "#BF360C",
    "#2E7D32", "#880E4F", "#4527A0", "#0277BD",
]

# 场景类型：深色背景（用于二级节点）
TYPE_BG = {
    "正向": "#2E7D32",
    "异常": "#C62828",
    "边界": "#E65100",
    "并发": "#1565C0",
}

# 前置条件/步骤/预期：柔和色
DETAIL_COLOR = {
    "precondition": "#37474F",  # 深灰蓝
    "step":         "#4E342E",  # 深棕（步骤节点）
    "expected":     "#1A237E",  # 深靛蓝
}

TYPE_ORDER = ["正向", "异常", "边界", "并发"]

# 优先级默认映射
TYPE_PRIORITY = {
    "正向": "P1",
    "异常": "P0",
    "边界": "P1",
    "并发": "P2",
}


# ─── 节点工厂 ──────────────────────────────────────────────────────────────────

def make_id() -> str:
    return uuid.uuid4().hex[:16]


def make_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def node(title: str,
         children: list = None,
         note: str = None,
         labels: list = None,
         bg: str = None,
         fg: str = "#FFFFFF",
         bold: bool = False) -> dict:
    """构造 XMind content.json 节点"""
    n = {
        "id":        make_id(),
        "class":     "topic",
        "title":     title,
        "timestamp": make_ts(),
    }
    if children:
        n["children"] = {"attached": children}
    if note:
        n["notes"] = {"plain": {"content": note}}
    if labels:
        n["labels"] = labels
    if bg:
        style: dict = {"properties": {"background-color": bg}}
        if fg:
            style["properties"]["color"] = fg
        if bold:
            style["properties"]["font-weight"] = "bold"
        n["style"] = style
    return n


# ─── 步骤拆分 ──────────────────────────────────────────────────────────────────

def parse_steps(raw: str) -> list:
    """
    将步骤文本拆成独立节点列表。
    支持 "1. xxx\n2. xxx" 或普通换行文本。
    每个步骤作为独立子节点，颜色统一。
    """
    if not raw or not raw.strip():
        return []
    lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
    step_nodes = []
    for line in lines:
        step_nodes.append(node(line, bg=DETAIL_COLOR["step"], fg="#FFFFFF"))
    return step_nodes


# ─── Sheet 1：用例树 ───────────────────────────────────────────────────────────

def build_testcase_sheet(data: dict) -> dict:
    meta         = data.get("meta", {})
    project      = meta.get("project", "测试用例")
    module       = meta.get("module", "")
    generated_at = meta.get("generated_at", datetime.now().strftime("%Y-%m-%d"))
    testcases    = data.get("testcases", [])

    # 第一层：按检查点分组
    cp_groups: dict[str, list] = defaultdict(list)
    for tc in testcases:
        cp = tc.get("checkpoint", "").strip() or "未关联检查点"
        cp_groups[cp].append(tc)

    checkpoint_nodes = []
    for cp_i, checkpoint in enumerate(sorted(cp_groups.keys())):
        cases = cp_groups[checkpoint]
        cp_color = CHECKPOINT_COLORS[cp_i % len(CHECKPOINT_COLORS)]

        # 第二层：按场景类型子分组
        type_groups: dict[str, list] = defaultdict(list)
        for tc in cases:
            type_groups[tc.get("type", "正向")].append(tc)

        type_nodes = []
        for tc_type in TYPE_ORDER:
            tc_list = type_groups.get(tc_type, [])
            if not tc_list:
                continue
            type_bg = TYPE_BG.get(tc_type, "#607D8B")

            # 第三层：用例节点
            case_nodes = []
            for tc in tc_list:
                tc_id    = tc.get("id", "TC-?")
                tc_point = tc.get("test_point", "")
                priority = TYPE_PRIORITY.get(tc_type, "P2")

                # 第四层：细节节点
                detail_children = []

                # 前置条件
                precond = tc.get("precondition", "").strip()
                if precond:
                    detail_children.append(
                        node(f"前置条件：{precond}",
                             bg=DETAIL_COLOR["precondition"], fg="#FFFFFF")
                    )

                # 操作步骤 — 每步独立节点
                step_nodes = parse_steps(tc.get("steps", ""))
                if step_nodes:
                    # 步骤父节点
                    steps_parent = node("操作步骤",
                                        children=step_nodes,
                                        bg=DETAIL_COLOR["step"], fg="#FFFFFF",
                                        bold=True)
                    detail_children.append(steps_parent)

                # 预期结果
                expected = tc.get("expected", "").strip()
                if expected:
                    detail_children.append(
                        node(f"预期结果：{expected}",
                             bg=DETAIL_COLOR["expected"], fg="#FFFFFF")
                    )

                case_title = f"{tc_id}  {tc_point}"
                case_node  = node(
                    title    = case_title,
                    children = detail_children if detail_children else None,
                    labels   = [priority],
                    bg       = type_bg,
                    fg       = "#FFFFFF",
                )
                case_nodes.append(case_node)

            # 场景类型节点（第二层）
            type_node = node(
                title    = f"{tc_type}场景  ({len(tc_list)} 条)",
                children = case_nodes,
                bg       = type_bg,
                fg       = "#FFFFFF",
                bold     = True,
            )
            type_nodes.append(type_node)

        # 检查点节点（第一层）
        cp_node = node(
            title    = f"{checkpoint}  ({len(cases)} 条)",
            children = type_nodes,
            bg       = cp_color,
            fg       = "#FFFFFF",
            bold     = True,
        )
        checkpoint_nodes.append(cp_node)

    # 统计摘要写入根节点备注
    type_counts: dict[str, int] = defaultdict(int)
    for tc in testcases:
        type_counts[tc.get("type", "正向")] += 1
    note_lines = [
        f"项目：{project}",
        f"模块：{module}" if module else "",
        f"生成日期：{generated_at}",
        f"用例总数：{len(testcases)} 条",
        "---",
    ] + [f"  {t}：{type_counts.get(t, 0)} 条" for t in TYPE_ORDER]
    note = "\n".join(l for l in note_lines if l != "")

    root = node(
        title    = f"{project}  —  测试用例",
        children = checkpoint_nodes,
        note     = note,
        bg       = ROOT_COLOR,
        fg       = "#FFFFFF",
        bold     = True,
    )

    return {
        "id":        make_id(),
        "class":     "sheet",
        "title":     "测试用例",
        "timestamp": make_ts(),
        "rootTopic": root,
    }


# ─── Sheet 2：统计总览 ──────────────────────────────────────────────────────────

def build_stat_sheet(data: dict) -> dict:
    """
    按场景类型汇总各检查点覆盖情况：
    [统计总览]
    ├── 正向场景 (N条)
    │   ├── XX-01 (N条)
    │   └── ...
    └── 异常场景 ...
    """
    meta      = data.get("meta", {})
    project   = meta.get("project", "测试用例")
    testcases = data.get("testcases", [])

    # type → checkpoint → count
    stat: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for tc in testcases:
        t  = tc.get("type", "正向")
        cp = tc.get("checkpoint", "").strip() or "未关联检查点"
        stat[t][cp] += 1

    type_nodes = []
    for tc_type in TYPE_ORDER:
        cp_map = stat.get(tc_type, {})
        if not cp_map:
            continue
        type_bg    = TYPE_BG.get(tc_type, "#607D8B")
        total_type = sum(cp_map.values())

        cp_nodes = []
        for cp, cnt in sorted(cp_map.items()):
            cp_nodes.append(node(
                f"{cp}  ({cnt} 条)",
                bg=CHECKPOINT_COLORS[
                    sorted(cp_map.keys()).index(cp) % len(CHECKPOINT_COLORS)
                ],
                fg="#FFFFFF",
            ))

        type_node = node(
            title    = f"{tc_type}场景  共 {total_type} 条",
            children = cp_nodes,
            bg       = type_bg,
            fg       = "#FFFFFF",
            bold     = True,
        )
        type_nodes.append(type_node)

    stat_root = node(
        title    = f"统计总览  —  {project}",
        children = type_nodes,
        bg       = ROOT_COLOR,
        fg       = "#FFFFFF",
        bold     = True,
    )

    return {
        "id":        make_id(),
        "class":     "sheet",
        "title":     "统计总览",
        "timestamp": make_ts(),
        "rootTopic": stat_root,
    }


# ─── 主导出函数 ────────────────────────────────────────────────────────────────

def export_xmind(input_json: str, output_xmind: str):
    with open(input_json, encoding="utf-8") as f:
        data = json.load(f)

    testcases = data.get("testcases", [])

    content = [
        build_testcase_sheet(data),
        build_stat_sheet(data),
    ]

    metadata = {
        "creator": {"name": "testcase-creator", "version": "2.0.0"},
        "created":  datetime.now(timezone.utc).isoformat(),
        "modified": datetime.now(timezone.utc).isoformat(),
    }

    manifest = {
        "file-entries": {
            "content.json":  {"media-type": "application/json"},
            "metadata.json": {"media-type": "application/json"},
        }
    }

    with zipfile.ZipFile(output_xmind, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.json",
                    json.dumps(content, ensure_ascii=False, indent=2))
        zf.writestr("metadata.json",
                    json.dumps(metadata, ensure_ascii=False, indent=2))
        zf.writestr("manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2))

    print(f"[OK] XMind 已生成：{output_xmind}（共 {len(testcases)} 条用例，2 个 Sheet）")
    print(f"     Sheet 1：测试用例（检查点 → 场景类型 → 用例 → 步骤）")
    print(f"     Sheet 2：统计总览（场景类型 → 检查点覆盖情况）")
    print(f"     提示：用 XMind 8 或更高版本打开")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法：python3 export_xmind.py <input.json> <output.xmind>")
        sys.exit(1)
    export_xmind(sys.argv[1], sys.argv[2])
