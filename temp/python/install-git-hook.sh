#!/bin/bash

# Git pre-commit hook 安装脚本 (Python)
# 自动在 git commit 前运行检查
# 使用方法: ./install-git-hook.sh

set -e

HOOK_FILE=".git/hooks/pre-commit"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🔧 安装 Git Pre-commit Hook (Python)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查是否在 git 仓库中
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  当前目录不是 git 仓库根目录${NC}"
    exit 1
fi

# 检查 hook 文件是否已存在
if [ -f "$HOOK_FILE" ]; then
    echo -e "${YELLOW}⚠️  pre-commit hook 已存在${NC}"
    echo -n "是否覆盖？(y/N): "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 0
    fi
    # 备份现有的 hook
    cp "$HOOK_FILE" "$HOOK_FILE.backup"
    echo -e "${GREEN}✓${NC} 已备份现有 hook 到 $HOOK_FILE.backup"
fi

# 创建 pre-commit hook
cat > "$HOOK_FILE" << 'EOF'
#!/bin/bash

# Git pre-commit hook - 自动运行 CI 检查 (Python)
# 由 install-git-hook.sh 自动生成

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

echo ""
echo -e "${BLUE}🔍 运行 pre-commit 检查 (Python)...${NC}"
echo ""

FAILED=0

# 1. 格式检查
echo -ne "  [1/5] 格式检查... "
if command -v ruff &> /dev/null; then
    if ruff format --check . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${YELLOW}      运行 'ruff format .' 修复格式问题${NC}"
        FAILED=$((FAILED + 1))
    fi
elif command -v black &> /dev/null; then
    if black --check . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${YELLOW}      运行 'black .' 修复格式问题${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC}"
fi

# 2. Import 排序
echo -ne "  [2/5] Import 排序... "
if command -v ruff &> /dev/null; then
    if ruff check --select I . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${YELLOW}      运行 'ruff check --select I --fix .' 修复${NC}"
        FAILED=$((FAILED + 1))
    fi
elif command -v isort &> /dev/null; then
    if isort --check-only . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${YELLOW}      运行 'isort .' 修复${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC}"
fi

# 3. Lint
echo -ne "  [3/5] Lint... "
if command -v ruff &> /dev/null; then
    if ruff check . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${YELLOW}      运行 'ruff check .' 查看详情${NC}"
        FAILED=$((FAILED + 1))
    fi
elif command -v flake8 &> /dev/null; then
    if flake8 . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC}"
fi

# 4. 类型检查
echo -ne "  [4/5] 类型检查... "
if command -v mypy &> /dev/null; then
    if mypy . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${YELLOW}      运行 'mypy .' 查看详情${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC}"
fi

# 5. 测试
echo -ne "  [5/5] 测试... "
if command -v pytest &> /dev/null; then
    if pytest > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC}"
fi

echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✨ 所有检查通过，提交继续${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  ${FAILED} 项检查失败${NC}"
    echo ""
    echo -e "${YELLOW}选项：${NC}"
    echo -e "  1. 修复问题后重新提交"
    echo -e "  2. 运行 ${YELLOW}./fix-issues.sh${NC} 自动修复"
    echo -e "  3. 使用 ${YELLOW}git commit --no-verify${NC} 跳过检查（不推荐）"
    echo ""
    exit 1
fi
EOF

# 设置执行权限
chmod +x "$HOOK_FILE"

echo -e "${GREEN}✓${NC} pre-commit hook 已安装到 $HOOK_FILE"
echo ""
echo -e "${BLUE}说明：${NC}"
echo "  • 每次 git commit 时会自动运行检查"
echo "  • 检查包括：格式、import、lint、类型、测试"
echo "  • 如需跳过检查，使用: git commit --no-verify"
echo ""
echo -e "${BLUE}测试 hook：${NC}"
echo -e "  ${YELLOW}git commit --allow-empty -m \"test hook\"${NC}"
echo ""
echo -e "${GREEN}✨ 安装完成！${NC}"
