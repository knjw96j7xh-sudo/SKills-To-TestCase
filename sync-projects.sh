#!/bin/bash
# 一键对齐本仓库 projects/* 的 Skill / 脚本副本
# 用法：./sync-projects.sh          # build + fix
#       ./sync-projects.sh --no-build

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NO_BUILD=false
for arg in "$@"; do
  if [ "$arg" = "--no-build" ]; then
    NO_BUILD=true
  fi
done

if [ "$NO_BUILD" = true ]; then
  python3 check_project_copies.py --fix
else
  python3 check_project_copies.py --fix --build
fi
