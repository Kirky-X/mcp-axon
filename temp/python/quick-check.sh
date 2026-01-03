#!/bin/bash

# Python 项目快速 CI 预检脚本
# 使用方法: ./quick-check.sh

set -e
set -o pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 图标
CHECK="✓"
CROSS="✗"
ARROW="→"

# Python 命令
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  ⚡ 快速 CI 预检 (Python)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. 格式检查
echo -e "${BLUE}[1/5]${NC} ${ARROW} 检查代码格式..."
echo -e "  ${YELLOW}运行命令: ruff format --check .${NC}"
echo ""

if command -v ruff &> /dev/null; then
    if ruff format --check . > /dev/null 2>&1; then
        echo -e "${GREEN}  ${CHECK} 代码格式检查通过${NC}"
        echo ""
    else
        echo -e "${RED}  ✗ 代码格式检查失败${NC}"
        echo ""
        echo -e "${BLUE}💡 修复命令:${NC}"
        echo -e "  ${YELLOW}ruff format .${NC}"
        echo ""
        exit 1
    fi
elif command -v black &> /dev/null; then
    if black --check . > /dev/null 2>&1; then
        echo -e "${GREEN}  ${CHECK} 代码格式检查通过 (black)${NC}"
        echo ""
    else
        echo -e "${RED}  ✗ 代码格式检查失败 (black)${NC}"
        echo ""
        echo -e "${BLUE}💡 修复命令:${NC}"
        echo -e "  ${YELLOW}black .${NC}"
        echo ""
        exit 1
    fi
else
    echo -e "${YELLOW}  ⚠ 未安装 ruff 或 black，跳过格式检查${NC}"
    echo ""
    echo -e "${BLUE}💡 安装命令:${NC}"
    echo -e "  ${YELLOW}pip install ruff${NC}"
    echo ""
fi

# 2. Import 排序
echo -e "${BLUE}[2/5]${NC} ${ARROW} 检查 import 排序..."
echo -e "  ${YELLOW}运行命令: ruff check --select I .${NC}"
echo ""

if command -v ruff &> /dev/null; then
    if ruff check --select I . > /dev/null 2>&1; then
        echo -e "${GREEN}  ${CHECK} Import 排序检查通过${NC}"
        echo ""
    else
        echo -e "${RED}  ✗ Import 排序检查失败${NC}"
        echo ""
        echo -e "${BLUE}💡 修复命令:${NC}"
        echo -e "  ${YELLOW}ruff check --select I --fix .${NC}"
        echo ""
        exit 1
    fi
elif command -v isort &> /dev/null; then
    if isort --check-only . > /dev/null 2>&1; then
        echo -e "${GREEN}  ${CHECK} Import 排序检查通过 (isort)${NC}"
        echo ""
    else
        echo -e "${RED}  ✗ Import 排序检查失败 (isort)${NC}"
        echo ""
        echo -e "${BLUE}💡 修复命令:${NC}"
        echo -e "  ${YELLOW}isort .${NC}"
        echo ""
        exit 1
    fi
else
    echo -e "${YELLOW}  ⚠ 未安装 ruff 或 isort，跳过 import 排序检查${NC}"
    echo ""
    echo -e "${BLUE}💡 安装命令:${NC}"
    echo -e "  ${YELLOW}pip install ruff${NC}"
    echo ""
fi

# 3. Lint 检查
echo -e "${BLUE}[3/5]${NC} ${ARROW} 运行 Lint 检查..."
echo -e "  ${YELLOW}运行命令: ruff check .${NC}"
echo ""

if command -v ruff &> /dev/null; then
    if ruff check . > /dev/null 2>&1; then
        echo -e "${GREEN}  ${CHECK} Ruff lint 检查通过${NC}"
        echo ""
    else
        echo -e "${RED}  ✗ Ruff lint 发现问题${NC}"
        echo ""
        echo -e "${BLUE}💡 详细命令:${NC}"
        echo -e "  ${YELLOW}ruff check .${NC}"
        echo ""
        exit 1
    fi
elif command -v flake8 &> /dev/null; then
    if flake8 . > /dev/null 2>&1; then
        echo -e "${GREEN}  ${CHECK} Flake8 检查通过${NC}"
        echo ""
    else
        echo -e "${RED}  ✗ Flake8 发现问题${NC}"
        echo ""
        echo -e "${BLUE}💡 详细命令:${NC}"
        echo -e "  ${YELLOW}flake8 .${NC}"
        echo ""
        exit 1
    fi
else
    echo -e "${YELLOW}  ⚠ 未安装 ruff 或 flake8，跳过 lint 检查${NC}"
    echo ""
    echo -e "${BLUE}💡 安装命令:${NC}"
    echo -e "  ${YELLOW}pip install ruff${NC}"
    echo ""
fi

# 4. 类型检查
echo -e "${BLUE}[4/5]${NC} ${ARROW} 运行类型检查..."
echo -e "  ${YELLOW}运行命令: mypy .${NC}"
echo ""

if command -v mypy &> /dev/null; then
    if mypy . > /dev/null 2>&1; then
        echo -e "${GREEN}  ${CHECK} MyPy 类型检查通过${NC}"
        echo ""
    else
        echo -e "${RED}  ✗ MyPy 发现类型问题${NC}"
        echo ""
        echo -e "${BLUE}💡 详细命令:${NC}"
        echo -e "  ${YELLOW}mypy .${NC}"
        echo ""
        exit 1
    fi
else
    echo -e "${YELLOW}  ⚠ 未安装 mypy，跳过类型检查${NC}"
    echo ""
    echo -e "${BLUE}💡 安装命令:${NC}"
    echo -e "  ${YELLOW}pip install mypy${NC}"
    echo ""
fi

# 5. 测试
echo -e "${BLUE}[5/5]${NC} ${ARROW} 运行测试..."
echo -e "  ${YELLOW}运行命令: pytest${NC}"
echo ""

if command -v pytest &> /dev/null; then
    if pytest > /dev/null 2>&1; then
        echo -e "${GREEN}  ${CHECK} 所有测试通过${NC}"
        echo ""
    else
        echo -e "${RED}  ✗ 部分测试失败${NC}"
        echo ""
        echo -e "${BLUE}💡 详细命令:${NC}"
        echo -e "  ${YELLOW}pytest -v${NC}"
        echo ""
        exit 1
    fi
else
    echo -e "${YELLOW}  ⚠ 未安装 pytest，跳过测试${NC}"
    echo ""
    echo -e "${BLUE}💡 安装命令:${NC}"
    echo -e "  ${YELLOW}pip install pytest${NC}"
    echo ""
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✨ 所有检查通过！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}推荐的提交流程：${NC}"
echo -e "  1. ${YELLOW}git add .${NC}"
echo -e "  2. ${YELLOW}git commit -m \"your message\"${NC}"
echo -e "  3. ${YELLOW}git push${NC}"
echo ""
