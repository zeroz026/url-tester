#!/usr/bin/env bash
set -e

# ============================================================
# 配置: 指向你 venv 里的 Python 解释器
# ============================================================
PYTHON_PATH="./venv/bin/python"
# PYTHON_PATH="/path/to/your/venv/bin/python"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "$PYTHON_PATH" ]; then
    echo "错误: 找不到 Python 解释器: $PYTHON_PATH"
    echo "请修改 run.sh 中的 PYTHON_PATH 指向正确的 venv Python 路径"
    exit 1
fi

echo "使用 Python: $PYTHON_PATH"
"$PYTHON_PATH" main.py
