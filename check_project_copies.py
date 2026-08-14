#!/usr/bin/env python3
"""Detect generated project copies that drift from repository sources.

用法:
    python3 check_project_copies.py
    python3 check_project_copies.py --strict
    python3 check_project_copies.py --fix          # 对齐 projects/* 的 Skill/脚本
    python3 check_project_copies.py --fix --build  # 先 build 再 fix
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

IGNORED_NAMES = {".DS_Store", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class Drift:
    project_path: Path
    source_path: Path | None
    kind: str
    source_name: str


def _files(root: Path) -> dict[Path, Path]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root): path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part in IGNORED_NAMES for part in path.parts)
        and path.suffix not in IGNORED_SUFFIXES
    }


def _compare_tree(
    project_root: Path,
    source_root: Path,
    source_name: str,
) -> list[Drift]:
    if not project_root.is_dir():
        return []
    project_files = _files(project_root)
    source_files = _files(source_root)
    drifts: list[Drift] = []
    for relative_path in sorted(project_files.keys() | source_files.keys()):
        project_path = project_files.get(relative_path)
        source_path = source_files.get(relative_path)
        if project_path is None:
            drifts.append(
                Drift(project_root / relative_path, source_path, "missing", source_name)
            )
        elif source_path is None:
            drifts.append(Drift(project_path, None, "extra", source_name))
        elif project_path.read_bytes() != source_path.read_bytes():
            drifts.append(Drift(project_path, source_path, "modified", source_name))
    return drifts


def installed_projects(repo_root: Path) -> list[Path]:
    projects_root = repo_root / "projects"
    if not projects_root.is_dir():
        return []
    return sorted(
        path
        for path in projects_root.iterdir()
        if path.is_dir() and path.name != "_template"
    )


def scan_project_copies(repo_root: Path) -> list[Drift]:
    agent_source = repo_root / "dist" / ".agents"
    script_source = repo_root / "framework" / "scripts"
    if not agent_source.is_dir():
        raise FileNotFoundError("dist/.agents 不存在，请先运行 ./build.sh")

    drifts: list[Drift] = []
    for project in installed_projects(repo_root):
        drifts.extend(_compare_tree(project / ".agents", agent_source, "skills/"))
        drifts.extend(
            _compare_tree(
                project / ".testcase-assets" / "scripts",
                script_source,
                "framework/scripts/",
            )
        )
    return drifts


def _copy_tree_files(source_root: Path, dest_root: Path) -> int:
    """复制源树全部文件到目标，返回复制文件数。忽略缓存。"""
    if not source_root.is_dir():
        return 0
    count = 0
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_NAMES for part in path.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        rel = path.relative_to(source_root)
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        count += 1
    return count


def fix_project_copies(repo_root: Path) -> list[str]:
    """将 projects/* 的 .agents 与 scripts 对齐统一源；写 FRAMEWORK_VERSION。"""
    agent_source = repo_root / "dist" / ".agents"
    cursor_source = repo_root / "dist" / ".cursor"
    claude_source = repo_root / "dist" / ".claude"
    script_source = repo_root / "framework" / "scripts"
    template_source = repo_root / "framework" / "templates"
    guide_source = repo_root / "TESTCASE_GUIDE.md"

    if not agent_source.is_dir():
        raise FileNotFoundError("dist/.agents 不存在，请先运行 ./build.sh")

    # 延迟 import，避免循环
    sys.path.insert(0, str(script_source))
    from framework_versions import write_version_file  # type: ignore

    messages: list[str] = []
    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for project in installed_projects(repo_root):
        n_agents = _copy_tree_files(agent_source, project / ".agents")
        n_scripts = _copy_tree_files(
            script_source, project / ".testcase-assets" / "scripts"
        )
        n_templates = _copy_tree_files(
            template_source, project / ".testcase-assets" / "templates"
        )
        if cursor_source.is_dir():
            _copy_tree_files(cursor_source, project / ".cursor")
        if claude_source.is_dir():
            # 不覆盖 settings.local.json
            for path in claude_source.rglob("*"):
                if not path.is_file():
                    continue
                if path.name == "settings.local.json":
                    continue
                rel = path.relative_to(claude_source)
                dest = project / ".claude" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
        if guide_source.is_file():
            shutil.copy2(guide_source, project / "TESTCASE_GUIDE.md")
        write_version_file(project / ".testcase-assets", synced_at=stamp)
        messages.append(
            f"[FIX] {project.name}: agents={n_agents} scripts={n_scripts} templates={n_templates}"
        )
    if not messages:
        messages.append("[OK] 无 projects/* 已安装副本需要修复")
    return messages


def _relative(path: Path | None, repo_root: Path) -> str:
    if path is None:
        return "-"
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def print_report(drifts: list[Drift], repo_root: Path) -> None:
    if not drifts:
        print("[OK] projects/* 中的 Skill 和脚本副本与统一源一致")
        return

    labels = {"modified": "内容不同", "missing": "项目缺失", "extra": "项目多出"}
    print(f"[WARN] 检测到 {len(drifts)} 项项目副本漂移：")
    for drift in drifts:
        print(f"  - [{labels[drift.kind]}] {_relative(drift.project_path, repo_root)}")
        print(f"    统一修改源：{drift.source_name}")
        if drift.source_path is not None:
            print(f"    对应源文件：{_relative(drift.source_path, repo_root)}")

    print("[ACTION] 不要直接修改 projects/* 下的生成副本：")
    print("  - Skill 内容请修改 skills/*/prompt.md 或 meta.yaml，再运行 ./build.sh")
    print("  - 导出脚本请修改 framework/scripts/，再重新初始化目标项目")
    print("  - 一键修复：python3 check_project_copies.py --fix")
    print("  - 或：python3 check_project_copies.py --fix --build")
    print("  - CI 可运行 python3 check_project_copies.py --strict 阻断漂移")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="仓库根目录，默认使用脚本所在目录",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="发现漂移时返回退出码 1，适用于 CI",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="将 projects/* 的 Skill/脚本对齐到 dist 与 framework/scripts",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="fix 前先执行 build.py --clean",
    )
    args = parser.parse_args()
    repo_root = args.root.resolve()

    if args.build:
        build_py = repo_root / "build.py"
        print("[BUILD] 正在构建 dist/ ...")
        result = subprocess.run(
            [sys.executable, str(build_py), "--clean"],
            cwd=str(repo_root),
            check=False,
        )
        if result.returncode != 0:
            print("[ERROR] build 失败")
            return result.returncode

    if args.fix:
        try:
            for line in fix_project_copies(repo_root):
                print(line)
        except FileNotFoundError as error:
            print(f"[ERROR] {error}")
            return 2

    try:
        drifts = scan_project_copies(repo_root)
    except FileNotFoundError as error:
        print(f"[ERROR] {error}")
        return 2

    print_report(drifts, repo_root)
    if args.fix and not drifts:
        print("[OK] --fix 完成，副本已与统一源一致")
    return 1 if drifts and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
