#!/bin/bash
# Axon 快速安装脚本
#
# 注意: 此脚本是 `uv pip install -e .[dev]` 的便捷封装
# 你也可以手动执行以下命令:
#   uv venv && source .venv/bin/activate && uv pip install -e .[dev]

set -e

# 获取脚本所在目录的父目录(项目根目录)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"

echo "========================================="
echo "Axon 安装脚本"
echo "========================================="
echo "项目目录: $PROJECT_ROOT"
echo ""

# 检查 Python 版本
echo "检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.12.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "错误: 需要 Python 3.12 或更高版本"
    echo "当前版本: $python_version"
    exit 1
fi

echo "Python 版本: $python_version ✓"

# 检查 uv 是否安装
if command -v uv &> /dev/null; then
    echo "检测到 uv，使用 uv 进行安装..."

    # 创建虚拟环境
    if [ ! -d ".venv" ]; then
        echo "创建虚拟环境..."
        uv venv
    fi

    # 激活虚拟环境
    source .venv/bin/activate

    # 安装依赖（使用 pyproject.toml）
    echo "安装依赖..."
    uv pip install -e .[dev]

else
    echo "未检测到 uv，使用 pip 进行安装..."

    # 检查 venv 是否存在
    if [ ! -d ".venv" ]; then
        echo "创建虚拟环境..."
        python3 -m venv .venv
    fi

    # 激活虚拟环境
    source .venv/bin/activate

    # 升级 pip
    echo "升级 pip..."
    pip install --upgrade pip

    # 安装依赖（使用 pyproject.toml）
    echo "安装依赖..."
    pip install -e .[dev]
fi

# 显示使用说明
echo ""
echo "========================================="
echo "安装完成！"
echo "========================================="
echo ""
echo "使用方法:"
echo "  1. 激活虚拟环境: source .venv/bin/activate"
echo "  2. 创建项目: axon project create --name \"我的项目\""
echo "  3. 启动 MCP 服务器: axon-server"
echo "  4. 运行测试: uv run pytest tests/ -v"
echo "  5. 运行预检查: bash scripts/pre-commit-check.sh"
echo ""
echo "Claude Desktop 配置:"
echo '  在 Claude Desktop 的配置文件中添加:'
echo '  {'
echo '    "mcpServers": {'
echo '      "axon": {'
echo '        "command": "python",'
echo '        "args": ["-m", "src.api.mcp_server"],'
echo '        "cwd": "<项目根目录路径>"'
echo '      }'
echo '    }'
echo '  }'
echo ""
