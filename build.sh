#!/bin/bash
# build.sh - 从统一源生成三种平台格式的 skill 文件
# 用法: ./build.sh [--clean]
# 依赖: Python 3；Python 包版本由 requirements.lock 固定

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查 Python 是否可用
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] 未找到 python3，请先安装 Python 3"
    exit 1
fi

# 检查 PyYAML 是否安装
if ! python3 -c "import yaml; from importlib.metadata import version; assert version('PyYAML') == '6.0.3'" &> /dev/null; then
    echo "[WARN] PyYAML 缺失或版本不一致，正在安装锁定依赖..."
    python3 -m pip install -r "$SCRIPT_DIR/requirements.lock"
fi

# 调用 Python 构建脚本（构建完成后会检查项目副本漂移）
python3 "$SCRIPT_DIR/build.py" "$@"
