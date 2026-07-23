#!/usr/bin/env python3
"""Detect generated project copies that drift from repository sources."""

import argparse
from dataclasses import dataclass
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


def scan_project_copies(repo_root: Path) -> list[Drift]:
    projects_root = repo_root / "projects"
    agent_source = repo_root / "dist" / ".agents"
    script_source = repo_root / "framework" / "scripts"
    if not agent_source.is_dir():
        raise FileNotFoundError("dist/.agents 不存在，请先运行 ./build.sh")

    drifts: list[Drift] = []
    if not projects_root.is_dir():
        return drifts

    for project in sorted(
        path
        for path in projects_root.iterdir()
        if path.is_dir() and path.name != "_template"
    ):
        drifts.extend(
            _compare_tree(project / ".agents", agent_source, "skills/")
        )
        drifts.extend(
            _compare_tree(
                project / ".testcase-assets" / "scripts",
                script_source,
                "framework/scripts/",
            )
        )
    return drifts


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
    args = parser.parse_args()
    repo_root = args.root.resolve()

    try:
        drifts = scan_project_copies(repo_root)
    except FileNotFoundError as error:
        print(f"[ERROR] {error}")
        return 2

    print_report(drifts, repo_root)
    return 1 if drifts and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
