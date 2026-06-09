#!/bin/bash
# build.sh - 从统一源生成三种平台格式的 skill 文件
# 用法: ./build.sh [--clean]
# 依赖: Python 3, PyYAML (pip install pyyaml)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查 Python 是否可用
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] 未找到 python3，请先安装 Python 3"
    exit 1
fi

# 检查 PyYAML 是否安装
if ! python3 -c "import yaml" &> /dev/null; then
    echo "[WARN] 未找到 PyYAML，正在安装..."
    pip3 install pyyaml
fi

# 调用 Python 构建脚本
python3 "$SCRIPT_DIR/build.py" "$@"
