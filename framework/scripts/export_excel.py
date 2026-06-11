#!/usr/bin/env python3
"""
export_excel.py — 将测试用例 JSON 导出为带样式的 Excel (.xlsx)

用法：
    python3 export_excel.py <input_json> <output_xlsx>

JSON 格式（由 Claude Code 生成）：
{
  "meta": {
    "project": "项目名称",
    "module":  "模块名称",
    "generated_at": "2026-06-01"
  },
  "testcases": [
    {
      "id":           "TC-001",
      "test_point":   "测试点描述",
      "precondition": "前置条件",
      "steps":        "1. 步骤一\n2. 步骤二",
      "expected":     "预期结果",
      "checkpoint":   "XX-01",
      "type":         "正向"          // 正向 / 异常 / 边界 / 并发
    }
  ]
}
"""

import sys
import json
import re
import ast
from datetime import datetime
from collections import defaultdict


# --- 容错 JSON 加载 ----------------------------------------------------

def load_json_robust(filepath: str) -> dict:
    """加载 JSON 文件，兼容 LLM 常见格式错误。

    预处理：移除 BOM、注释（// 和 /* */）。
    解析策略（按优先级）：
      1. 严格 JSON
      2. 去除尾逗号 + JSON
      3. Python 字面量求值（处理单引号 / None / True / False）
      4. 激进单引号→双引号替换
    """
    with open(filepath, "r", encoding="utf-8") as fh:
        raw = fh.read()

    if not raw.strip():
        raise ValueError(f"文件为空: {filepath}")

    # 预处理：移除 BOM
    raw = raw.lstrip("﻿")
    # 预处理：移除行注释 //（不影响 https://）
    raw = re.sub(r'(?<!:)(?<!:/)//.*$', '', raw, flags=re.MULTILINE)
    # 预处理：移除块注释 /* ... */
    raw = re.sub(r'/\*.*?\*/', '', raw, flags=re.DOTALL)

    errors = []

    # 策略 1：严格 JSON
    try:
        data = json.loads(raw)
        if isinstance(data, (dict, list)):
            return data if isinstance(data, dict) else {"testcases": data}
    except json.JSONDecodeError as e:
        errors.append(f"[strict JSON] {e}")

    # 策略 2：去除尾逗号（LLM 常见错误：{"a": 1,} / [1,2,]）
    no_trailing = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        data = json.loads(no_trailing)
        if isinstance(data, (dict, list)):
            return data if isinstance(data, dict) else {"testcases": data}
    except json.JSONDecodeError as e:
        errors.append(f"[comma fix] {e}")

    # 策略 3：Python 字面量（处理单引号字典 / None / True / False）
    try:
        data = ast.literal_eval(raw)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"testcases": data}
    except (ValueError, SyntaxError) as e:
        errors.append(f"[Python literal] {e}")

    # 策略 4：激进单引号→双引号替换（最后手段，可能误伤内容中的引号）
    aggressive = re.sub(r"'([^']*)'", r'"\1"', no_trailing)
    try:
        data = json.loads(aggressive)
        if isinstance(data, (dict, list)):
            return data if isinstance(data, dict) else {"testcases": data}
    except json.JSONDecodeError as e:
        errors.append(f"[quote fix] {e}")

    raise ValueError(
        f"无法解析 JSON 文件 {filepath}，所有策略均失败：\n"
        + "\n".join(errors)
    )

try:
    from openpyxl import Workbook
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side,
    )
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, Reference
    from openpyxl.chart.label import DataLabelList
except ImportError:
    print("[ERROR] 缺少 openpyxl，请执行：pip3 install openpyxl")
    sys.exit(1)


# ─── 颜色 & 样式常量 ───────────────────────────────────────────────────────────

C = {
    # 主题色
    "brand":        "1E3A5F",   # 深海蓝
    "brand_mid":    "2C5F8A",   # 中蓝（摘要行）
    "brand_light":  "E8F1F8",   # 浅蓝（隔行）
    "white":        "FFFFFF",
    "text_dark":    "1A1A2E",
    "text_mid":     "4A4A6A",

    # 场景类型 — 行背景（淡）
    "正向_bg":      "EAF7EA",
    "异常_bg":      "FDECEA",
    "边界_bg":      "FFF8E1",
    "并发_bg":      "E3F2FD",

    # 场景类型 — 分组标题行（深）
    "正向_head":    "2E7D32",
    "异常_head":    "C62828",
    "边界_head":    "E65100",
    "并发_head":    "1565C0",

    # 场景类型 — 状态徽章
    "正向_badge":   "43A047",
    "异常_badge":   "E53935",
    "边界_badge":   "FB8C00",
    "并发_badge":   "1E88E5",

    # 优先级
    "P0_bg":        "FFCDD2",
    "P1_bg":        "FFE0B2",
    "P2_bg":        "FFF9C4",
    "P3_bg":        "E8F5E9",

    # 边框
    "border_light": "D0D8E4",
    "border_group": "B0BEC5",
}

# 优先级默认映射（场景类型 → 默认优先级）
TYPE_PRIORITY = {
    "正向": "P1",
    "异常": "P0",
    "边界": "P1",
    "并发": "P2",
}

TYPE_ORDER   = ["正向", "异常", "边界", "并发"]
STATUS_OPTS  = ["未执行", "通过", "失败", "阻塞", "跳过"]

# 列定义：(列头, 宽度, 列key或None)
#   key = None 表示留白由人工填写
COLUMNS = [
    ("用例ID",      11,  "id"),
    ("测试点",      30,  "test_point"),
    ("前置条件",    24,  "precondition"),
    ("操作步骤",    48,  "steps"),
    ("预期结果",    34,  "expected"),
    ("关联检查点",  12,  "checkpoint"),
    ("场景类型",    10,  "type"),
    ("优先级",       8,  "_priority"),   # 自动赋值
    ("执行状态",     9,  None),          # 留空
    ("编写人",       8,  None),          # 留空
    ("执行人",       8,  None),          # 留空
    ("备注",        18,  None),          # 留空
]

N_COLS = len(COLUMNS)


# ─── 样式工厂 ──────────────────────────────────────────────────────────────────

def fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)


def border(color: str = "D0D8E4", style: str = "thin") -> Border:
    s = Side(style=style, color=color)
    return Border(left=s, right=s, top=s, bottom=s)


def font(bold=False, color="1A1A2E", size=10, italic=False) -> Font:
    return Font(bold=bold, color=color, name="微软雅黑", size=size,
                italic=italic)


def align(h="left", v="top", wrap=True) -> Alignment:
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)


# ─── 摘要行（第 1 行，4 段合并+分隔线风格）─────────────────────────────────────

def write_summary_row(ws, project: str, module: str,
                      total: int, generated_at: str):
    """第1行：四格摘要 — 项目名 | 模块 | 用例总数 | 生成日期"""
    # 按列数均分为 4 段（每段约 N_COLS/4 列）
    seg = N_COLS // 4
    spans = [
        (1,         seg,          f"{project}"),
        (seg+1,     seg*2,        f"{module}"),
        (seg*2+1,   seg*3,        f"共 {total} 条用例"),
        (seg*3+1,   N_COLS,       f"{generated_at}"),
    ]
    for (c1, c2, text) in spans:
        ws.merge_cells(start_row=1, start_column=c1,
                       end_row=1,   end_column=c2)
        cell = ws.cell(row=1, column=c1, value=text)
        cell.font      = Font(bold=True, color=C["white"],
                              name="微软雅黑", size=10)
        cell.fill      = fill(C["brand_mid"])
        cell.alignment = Alignment(horizontal="center",
                                   vertical="center", wrap_text=False)
        cell.border    = Border(
            left=Side(style="medium", color=C["white"]),
            right=Side(style="medium", color=C["white"]),
            top=Side(style="thin", color=C["brand"]),
            bottom=Side(style="thin", color=C["brand"]),
        )
    ws.row_dimensions[1].height = 26


# ─── 列名行（第 2 行）──────────────────────────────────────────────────────────

def write_header_row(ws):
    for col_idx, (name, _, _key) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=2, column=col_idx, value=name)
        cell.font      = font(bold=True, color=C["white"], size=10)
        cell.fill      = fill(C["brand"])
        cell.alignment = align(h="center", v="center")
        cell.border    = Border(
            left=Side(style="thin",   color=C["brand_mid"]),
            right=Side(style="thin",  color=C["brand_mid"]),
            top=Side(style="medium",  color=C["white"]),
            bottom=Side(style="medium", color=C["brand_light"]),
        )
    ws.row_dimensions[2].height = 24


# ─── 分组视觉分隔（不插行，在首行上边框加粗）──────────────────────────────────────

def apply_group_separator(ws, row_idx: int, tc_type: str):
    """在每组第一条用例的每个单元格顶部加粗边框，作为视觉分组分隔线，不破坏筛选"""
    sep_color = C.get(f"{tc_type}_head", C["brand"])
    for col_idx in range(1, N_COLS + 1):
        cell = ws.cell(row=row_idx, column=col_idx)
        existing = cell.border
        cell.border = Border(
            left=existing.left,
            right=existing.right,
            top=Side(style="medium", color=sep_color),
            bottom=existing.bottom,
        )


# ─── 用例数据行 ────────────────────────────────────────────────────────────────

def write_testcase_row(ws, row_idx: int, tc: dict, row_in_group: int):
    tc_type  = tc.get("type", "正向")
    # 奇偶行微差：奇数行用场景色，偶数行略白
    if row_in_group % 2 == 1:
        bg = C.get(f"{tc_type}_bg", "F9F9F9")
    else:
        bg = "FFFFFF"

    priority = tc.get("priority") or TYPE_PRIORITY.get(tc_type, "P2")
    p_bg     = C.get(f"{priority}_bg", "FFFFFF")

    raw_steps     = tc.get("steps", "")
    steps_display = raw_steps   # 保持原始换行，不插额外空行

    # 关联检查点：支持字符串（UC-01,RISK-02）或数组（["UC-01","RISK-02"]）
    raw_cp = tc.get("checkpoint", "")
    if isinstance(raw_cp, list):
        checkpoint_str = ", ".join(raw_cp)
    else:
        checkpoint_str = str(raw_cp)

    values = {
        "id":           tc.get("id", ""),
        "test_point":   tc.get("test_point", ""),
        "precondition": tc.get("precondition", ""),
        "steps":        steps_display,
        "expected":     tc.get("expected", ""),
        "checkpoint":   checkpoint_str,
        "type":         tc_type,
        "_priority":    priority,
        None:           "",   # 留空列
    }

    for col_idx, (_, _, key) in enumerate(COLUMNS, start=1):
        val  = values.get(key, "")
        cell = ws.cell(row=row_idx, column=col_idx, value=val)

        # 优先级列独立背景色
        if key == "_priority":
            cell.fill = fill(p_bg)
            cell.font = font(bold=True, size=9, color=C["text_dark"])
        # 场景类型列：深色徽章
        elif key == "type":
            badge_bg = C.get(f"{tc_type}_badge", C["brand"])
            cell.fill = fill(badge_bg)
            cell.font = Font(bold=True, color=C["white"],
                             name="微软雅黑", size=9)
        else:
            cell.fill = fill(bg)
            cell.font = font(size=10, color=C["text_dark"])

        # 水平对齐
        if key in ("id", "checkpoint", "type", "_priority", None):
            h_align = "center"
        else:
            h_align = "left"

        cell.alignment = Alignment(horizontal=h_align, vertical="top",
                                   wrap_text=True)
        cell.border = border(C["border_light"])

    # 根据步骤行数和最长步骤文字长度估算行高
    step_lines = raw_steps.split("\n") if raw_steps else []
    n_lines    = len(step_lines)
    # 操作步骤列宽度（COLUMNS[3]）为 48，每个中文字符约占 2 个单位宽
    step_col_width = 48
    char_per_line  = step_col_width // 2
    # 计算实际展示行数（文字折行得多占行）
    display_lines = sum(
        max(1, (len(s.replace(' ', '')) * 2 + len(s) - len(s.replace(' ', ''))) // char_per_line + 1)
        for s in step_lines
    ) if step_lines else 1
    row_height = max(18, display_lines * 14 + 4)
    ws.row_dimensions[row_idx].height = row_height


# ─── 列宽 ──────────────────────────────────────────────────────────────────────

def set_column_widths(ws):
    for col_idx, (_, width, _) in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width


# ─── 统计 Sheet（含柱状图）───────────────────────────────────────────────────────

def write_stat_sheet(wb, testcases: list):
    ws = wb.create_sheet("统计")

    # ── 标题 ──
    ws.merge_cells("A1:D1")
    title_cell = ws["A1"]
    title_cell.value     = "用例场景分布统计"
    title_cell.font      = Font(bold=True, color=C["white"],
                                name="微软雅黑", size=12)
    title_cell.fill      = fill(C["brand"])
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # ── 表头 ──
    headers = ["场景类型", "用例数量", "占比"]
    for i, h in enumerate(headers, start=1):
        cell = ws.cell(row=2, column=i, value=h)
        cell.font      = font(bold=True, color=C["white"])
        cell.fill      = fill(C["brand_mid"])
        cell.alignment = align(h="center", v="center")
        cell.border    = border()
    ws.row_dimensions[2].height = 20

    # ── 数据 ──
    type_counts = defaultdict(int)
    for tc in testcases:
        type_counts[tc.get("type", "正向")] += 1
    total = len(testcases)

    for row_i, t in enumerate(TYPE_ORDER, start=3):
        cnt   = type_counts.get(t, 0)
        ratio = f"{cnt/total*100:.1f}%" if total else "0%"
        bg    = C.get(f"{t}_bg", "F9F9F9")
        badge = C.get(f"{t}_badge", C["brand"])

        # 场景类型
        c1 = ws.cell(row=row_i, column=1, value=t)
        c1.font = Font(bold=True, color=C["white"], name="微软雅黑", size=10)
        c1.fill = fill(badge)
        c1.alignment = align(h="center", v="center", wrap=False)
        c1.border    = border()

        # 数量
        c2 = ws.cell(row=row_i, column=2, value=cnt)
        c2.font      = font(bold=True, size=11)
        c2.fill      = fill(bg)
        c2.alignment = align(h="center", v="center", wrap=False)
        c2.border    = border()

        # 占比
        c3 = ws.cell(row=row_i, column=3, value=ratio)
        c3.font      = font(color=C["text_mid"], size=10)
        c3.fill      = fill(bg)
        c3.alignment = align(h="center", v="center", wrap=False)
        c3.border    = border()

        ws.row_dimensions[row_i].height = 22

    # 合计行
    total_row = 3 + len(TYPE_ORDER)
    ws.cell(row=total_row, column=1, value="合计").font = font(bold=True)
    ws.cell(row=total_row, column=2, value=total).font  = font(bold=True)
    ws.cell(row=total_row, column=3, value="100%").font = font(bold=True)
    for col in (1, 2, 3):
        cell = ws.cell(row=total_row, column=col)
        cell.fill      = fill(C["brand_light"])
        cell.border    = border(C["border_group"], "medium")
        cell.alignment = align(h="center", v="center", wrap=False)
    ws.row_dimensions[total_row].height = 20

    # ── 柱状图 ──
    chart = BarChart()
    chart.type           = "col"
    chart.grouping       = "clustered"
    chart.title          = "用例场景分布"
    chart.y_axis.title   = "用例数量"
    chart.x_axis.title   = "场景类型"
    chart.style          = 10
    chart.width          = 18
    chart.height         = 12

    data_ref = Reference(ws,
                         min_col=2, max_col=2,
                         min_row=2, max_row=2 + len(TYPE_ORDER))
    cats_ref = Reference(ws,
                         min_col=1,
                         min_row=3, max_row=2 + len(TYPE_ORDER))
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.series[0].graphicalProperties.solidFill    = "1E3A5F"
    chart.series[0].graphicalProperties.line.solidFill = "1E3A5F"

    ws.add_chart(chart, "E2")

    # 列宽
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 10


# ─── 打印设置 ──────────────────────────────────────────────────────────────────

def apply_print_settings(ws, total_rows: int):
    from openpyxl.worksheet.page import PageMargins, PrintPageSetup
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize   = ws.PAPERSIZE_A4
    ws.page_setup.fitToPage   = True
    ws.page_setup.fitToWidth  = 1
    ws.page_setup.fitToHeight = 0          # 不限高度
    ws.print_title_rows       = "1:2"      # 每页重复打印前两行
    ws.page_margins = PageMargins(
        left=0.5, right=0.5, top=0.75, bottom=0.75,
        header=0.3, footer=0.3
    )
    # 页眉页脚
    ws.oddHeader.center.text = "&B测试用例清单"
    ws.oddFooter.right.text  = "第 &P 页 / 共 &N 页"


# ─── 主函数 ────────────────────────────────────────────────────────────────────

def export_excel(input_json: str, output_xlsx: str):
    import os

    # 验证输入文件
    if not os.path.exists(input_json):
        print(f"[FAIL] 输入文件不存在: {input_json}")
        sys.exit(1)

    # 确保输出目录存在
    output_dir = os.path.dirname(output_xlsx)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except Exception as e:
            print(f"[FAIL] 无法创建输出目录: {e}")
            sys.exit(1)

    try:
        data = load_json_robust(input_json)
    except ValueError as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"[FAIL] 文件编码错误，请确保为 UTF-8: {input_json}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] 读取文件失败: {e}")
        sys.exit(1)

    # 自动修复：将解析成功的数据写回文件，确保磁盘上的 JSON 始终符合严格规范
    try:
        with open(input_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (OSError, IOError):
        pass  # 非致命：修复失败不影响本次导出

    meta         = data.get("meta", {})
    project      = meta.get("project", "测试用例")
    module       = meta.get("module", "")
    generated_at = meta.get("generated_at", datetime.now().strftime("%Y-%m-%d"))
    testcases    = data.get("testcases", [])

    if not isinstance(testcases, list):
        print(f"[FAIL] JSON 中 testcases 字段必须是数组，当前类型: {type(testcases).__name__}")
        sys.exit(1)

    if not testcases:
        print("[WARN] testcases 为空，将生成仅含标题的 Excel 文件")

    wb = Workbook()

    # ── 主表 Sheet ─────────────────────────────────────────────────────────────
    ws       = wb.active
    ws.title = "测试用例"

    # 第1行：摘要
    write_summary_row(ws, project, module, len(testcases), generated_at)
    # 第2行：列名
    write_header_row(ws)

    # 按场景类型分组排序
    groups = defaultdict(list)
    for tc in testcases:
        groups[tc.get("type", "正向")].append(tc)

    current_row = 3
    for tc_type in TYPE_ORDER:
        cases = groups.get(tc_type, [])
        if not cases:
            continue
        # 用例行（不插额外标题行，筛选区域保持连续）
        for idx, tc in enumerate(cases, start=1):
            write_testcase_row(ws, current_row, tc, idx)
            # 每组第一行加粗上边框作为视觉分隔
            if idx == 1:
                apply_group_separator(ws, current_row, tc_type)
            current_row += 1

    last_data_row = current_row - 1

    # 冻结前两行
    ws.freeze_panes = "A3"
    # 筛选器：覆盖完整数据区域（第2行列名 → 最后数据行）
    if last_data_row >= 2:
        ws.auto_filter.ref = f"A2:{get_column_letter(N_COLS)}{last_data_row}"
    set_column_widths(ws)
    apply_print_settings(ws, current_row)

    # ── 统计 Sheet ────────────────────────────────────────────────────────────
    write_stat_sheet(wb, testcases)

    try:
        wb.save(output_xlsx)
    except PermissionError:
        print(f"[FAIL] 无写入权限: {output_xlsx}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] 写入 Excel 失败: {e}")
        sys.exit(1)

    print(f"[OK] Excel 已生成：{output_xlsx}（共 {len(testcases)} 条用例）")
    print(f"     包含列：用例ID / 测试点 / 前置条件 / 操作步骤 / 预期结果")
    print(f"           关联检查点 / 场景类型 / 优先级 / 执行状态 / 编写人 / 执行人 / 备注")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法：python3 export_excel.py <input.json> <output.xlsx>")
        sys.exit(1)
    export_excel(sys.argv[1], sys.argv[2])
