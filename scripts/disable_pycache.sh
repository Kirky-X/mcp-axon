#!/bin/bash
# 禁止 Python 生成 __pycache__ 和 .pyc 文件
# 使用方法: source scripts/disable_pycache.sh

export PYTHONDONTWRITEBYTECODE=1

echo "✓ 已禁止 Python 生成 __pycache__ 和 .pyc 文件"
echo "  环境变量: PYTHONDONTWRITEBYTECODE=1"
echo ""
echo "提示: 此设置仅在当前终端会话中有效"
echo "如需永久生效，请添加到 ~/.bashrc 或 ~/.zshrc:"
echo "  export PYTHONDONTWRITEBYTECODE=1"
