#!/usr/bin/env bash
set -euo pipefail

# 强制 UTF-8，减少中文制度文件解析和日志输出乱码。
export PYTHONUTF8=1
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
export LANG="${LANG:-en_US.UTF-8}"

cd "$(dirname "$0")/../backend-python"
python3 app.py

