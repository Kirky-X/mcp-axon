#!/bin/bash

# Python 项目智能修复脚本 - 自动修复常见问题
# 使用方法: ./fix-issues.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Python 命令
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🔧 自动修复常见问题 (Python)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

FIXED=0
FAILED=0

# 1. 修复代码格式
echo -e "${BLUE}[1/4]${NC} 修复代码格式..."
if command -v ruff &> /dev/null; then
    if ruff format .; then
        echo -e "${GREEN}  ✓ 代码格式已修复 (ruff)${NC}"
        FIXED=$((FIXED + 1))
    else
        echo -e "${RED}  ✗ 格式修复失败${NC}"
        FAILED=$((FAILED + 1))
    fi
elif command -v black &> /dev/null; then
    if black .; then
        echo -e "${GREEN}  ✓ 代码格式已修复 (black)${NC}"
        FIXED=$((FIXED + 1))
    else
        echo -e "${RED}  ✗ 格式修复失败${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}  ⚠ ruff 和 black 都未安装${NC}"
    echo -e "  安装命令: ${BLUE}pip install ruff${NC} 或 ${BLUE}pip install black${NC}"
fi
echo ""

# 2. 修复 import 排序
echo -e "${BLUE}[2/4]${NC} 修复 import 排序..."
if command -v ruff &> /dev/null; then
    if ruff check --select I --fix .; then
        echo -e "${GREEN}  ✓ Import 排序已修复 (ruff)${NC}"
        FIXED=$((FIXED + 1))
    else
        echo -e "${YELLOW}  ⚠ 部分 import 问题需要手动修复${NC}"
    fi
elif command -v isort &> /dev/null; then
    if isort .; then
        echo -e "${GREEN}  ✓ Import 排序已修复 (isort)${NC}"
        FIXED=$((FIXED + 1))
    else
        echo -e "${RED}  ✗ Import 排序修复失败${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}  ⚠ ruff 和 isort 都未安装${NC}"
    echo -e "  安装命令: ${BLUE}pip install ruff${NC} 或 ${BLUE}pip install isort${NC}"
fi
echo ""

# 3. 自动修复 lint 问题
echo -e "${BLUE}[3/4]${NC} 尝试修复 Lint 问题..."
if command -v ruff &> /dev/null; then
    # 使用 ruff 自动修复
    if ruff check --fix .; then
        echo -e "${GREEN}  ✓ Lint 问题已修复（如有）${NC}"
        FIXED=$((FIXED + 1))
    else
        echo -e "${YELLOW}  ⚠ 部分 Lint 问题需要手动修复${NC}"
    fi
elif command -v autopep8 &> /dev/null; then
    if autopep8 --in-place --recursive .; then
        echo -e "${GREEN}  ✓ PEP8 问题已修复 (autopep8)${NC}"
        FIXED=$((FIXED + 1))
    else
        echo -e "${RED}  ✗ 自动修复失败${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ ruff 和 autopep8 都未安装${NC}"
    echo -e "  安装命令: ${BLUE}pip install ruff${NC} 或 ${BLUE}pip install autopep8${NC}"
fi
echo ""

# 4. 检查依赖更新
echo -e "${BLUE}[4/4]${NC} 检查依赖更新..."
if command -v pip-review &> /dev/null; then
    echo "  可用的依赖更新："
    pip-review 2>/dev/null || true
    echo ""
    echo -e "${YELLOW}  提示: 运行 'pip-review --auto' 自动更新所有依赖${NC}"
elif command -v pip list &> /dev/null; then
    echo "  当前安装的包："
    pip list --outdated 2>/dev/null | head -10 || true
    echo ""
    echo -e "${YELLOW}  提示: 使用 'pip install --upgrade PACKAGE_NAME' 更新特定包${NC}"
    echo -e "  安装 pip-review: ${BLUE}pip install pip-review${NC}"
else
    echo -e "${YELLOW}  ⚠ pip 命令不可用${NC}"
fi
echo ""

# 总结
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✨ 修复完成！${NC}"
    echo ""
    echo -e "${BLUE}下一步：${NC}"
    echo "  1. 检查修改内容: git diff"
    echo "  2. 运行验证脚本: ./quick-check.sh"
    echo "  3. 提交更改: git add . && git commit -m \"fix: auto-fix issues\""
else
    echo -e "${YELLOW}⚠️  部分问题需要手动修复${NC}"
    echo ""
    echo -e "${BLUE}建议：${NC}"
    echo "  运行详细检查查看具体问题: ./pre-commit-check.sh"
fi
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
