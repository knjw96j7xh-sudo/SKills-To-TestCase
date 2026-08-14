#!/usr/bin/env python3
"""启动环境体检：能力矩阵 + 降级说明。

用法:
    python3 check_environment.py
    python3 check_environment.py /path/to/project
    python3 check_environment.py --strict   # 阻断项失败则退出码 1
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from framework_versions import check_versions, find_version_file


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _find_assets_root(start: Path) -> Path | None:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for parent in [cur, *cur.parents]:
        assets = parent / ".testcase-assets"
        if assets.is_dir():
            return assets
    return None


def run_checks(start: Path) -> tuple[bool, list[str], list[str]]:
    """
    返回 (blocking_ok, lines, warnings)。
    blocking_ok=False 表示有阻断项。
    """
    lines: list[str] = ["【环境能力体检】"]
    warnings: list[str] = []
    blocking_ok = True

    # Python
    ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info < (3, 9):
        lines.append(f"[FAIL] Python {ver}（需要 >= 3.9）")
        blocking_ok = False
    else:
        lines.append(f"[OK] Python {ver}")

    # 依赖
    for label, mod in (("openpyxl", "openpyxl"), ("json-repair", "json_repair")):
        if _has_module(mod):
            lines.append(f"[OK] 依赖 {label}")
        else:
            lines.append(f"[FAIL] 缺少依赖 {label}（导出/修复 JSON 需要）")
            blocking_ok = False

    # 框架版本
    version_file = find_version_file(start)
    ok_ver, ver_msgs = check_versions(version_file)
    if ok_ver:
        lines.append(ver_msgs[0] if ver_msgs else "[OK] 框架版本")
    else:
        lines.append("[FAIL] 框架版本落后或缺失")
        for msg in ver_msgs:
            if msg.startswith("["):
                lines.append(f"  {msg}")
            else:
                lines.append(f"  {msg}")
        blocking_ok = False

    # 资产目录可写
    assets = _find_assets_root(start)
    if assets is None:
        lines.append("[FAIL] 未找到 .testcase-assets/（请先 init）")
        blocking_ok = False
    else:
        try:
            probe = assets / ".env_check_write"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            lines.append(f"[OK] 资产目录可写：{assets}")
        except OSError as error:
            lines.append(f"[FAIL] 资产目录不可写：{assets}（{error}）")
            blocking_ok = False

        for name in ("checkpoints-index.md", "review-expectations-index.md"):
            path = assets / name
            if path.is_file():
                lines.append(f"[OK] 存在 {name}")
            else:
                lines.append(f"[FAIL] 缺少 {name}")
                blocking_ok = False

    # 可选工具
    if shutil.which("pdftotext"):
        lines.append("[OK] pdftotext（PDF 文字层）")
    else:
        msg = "未检测到 pdftotext → 设计稿 PDF 仅弱解析，建议导出图片或粘贴要点"
        lines.append(f"[WARN] {msg}")
        warnings.append(msg)

    if _has_module("docx"):
        lines.append("[OK] python-docx（DOCX）")
    else:
        msg = "未安装 python-docx → .docx 需本机 textutil 或其他方式"
        lines.append(f"[WARN] {msg}")
        warnings.append(msg)

    lines.append("")
    lines.append("【输入来源提示】")
    lines.append("  高可靠：粘贴文字、本地 .md / 图片")
    lines.append("  中可靠：本地 PDF/Excel（视本机工具）")
    lines.append("  低可靠：飞书/Jira/乐享链接（失败则待用户粘贴，禁止编造）")
    lines.append("")
    if blocking_ok:
        lines.append("[OK] 环境体检通过（可继续初始化后流程）")
    else:
        lines.append("[FAIL] 存在阻断项：请修复后再触发 /testcase-creator")

    return blocking_ok, lines, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="项目路径（向上查找 .testcase-assets）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="阻断项失败时返回退出码 1",
    )
    args = parser.parse_args()
    start = Path(args.path).resolve()
    ok, lines, _warnings = run_checks(start)
    for line in lines:
        print(line)
    if not ok and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
