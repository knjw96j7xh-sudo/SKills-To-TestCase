#!/usr/bin/env python3
"""检查本地 .testcase-assets 是否跟上当前框架版本。

用法:
    python3 check_framework_version.py
    python3 check_framework_version.py /path/to/project
    python3 check_framework_version.py --strict   # 落后时退出码 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from framework_versions import check_versions, find_version_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="项目路径或任意子路径（向上查找 FRAMEWORK_VERSION）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="版本落后或缺失时返回退出码 1",
    )
    args = parser.parse_args()
    start = Path(args.path).resolve()
    version_file = find_version_file(start)
    ok, messages = check_versions(version_file)
    for line in messages:
        print(line)
    if not ok and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
