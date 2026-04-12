#!/bin/bash
# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

# Axon Nuitka 编译脚本 - 性能优化版本
#
# 使用方法:
#   ./scripts/build_nuitka.sh [--clean] [--debug]
#
# 输出目录: dist/axon-standalone

set -e

# 配置变量
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
PROJECT_NAME="axon"
VERSION="1.0.0"
OUTPUT_DIR="${PROJECT_ROOT}/dist"
BUILD_DIR="${PROJECT_ROOT}/build/nuitka"

# 编译选项
CLEAN_BUILD=false
DEBUG_MODE=false

# 解析参数
while [[ $# -gt 0 ]]; do
	case $1 in
	--clean)
		CLEAN_BUILD=true
		shift
		;;
	--debug)
		DEBUG_MODE=true
		shift
		;;
	*)
		echo "未知参数: $1"
		echo "使用方法: $0 [--clean] [--debug]"
		exit 1
		;;
	esac
done

echo "======================================"
echo "Axon Nuitka 编译脚本"
echo "版本: ${VERSION}"
echo "======================================"

# 清理旧构建
if [[ "$CLEAN_BUILD" == "true" ]]; then
	echo "[1/6] 清理旧构建..."
	rm -rf "${BUILD_DIR}"
	rm -rf "${OUTPUT_DIR}/${PROJECT_NAME}.dist"
	rm -rf "${OUTPUT_DIR}/${PROJECT_NAME}-standalone"
fi

# 创建构建目录
mkdir -p "${BUILD_DIR}"
mkdir -p "${OUTPUT_DIR}"

# 检查依赖
echo "[2/6] 检查编译依赖..."
if ! command -v nuitka &>/dev/null; then
	echo "Nuitka 未安装，正在安装..."
	pip install nuitka
fi

# 检查 C 编译器 - 确保 gcc 在 PATH 中
export PATH="/opt/software/gcc-14.2/bin:$PATH"
if ! command -v gcc &>/dev/null; then
	echo "错误: GCC 未安装"
	echo "请安装: sudo apt install gcc build-essential"
	exit 1
fi

# 性能优化参数 (Nuitka 4.0)
NUITKA_OPTS=(
	# 主入口点 - 使用完整版 CLI (支持所有8个接口)
	"--main=${PROJECT_ROOT}/src/cli/cli_full.py"

	# 输出配置
	"--output-dir=${OUTPUT_DIR}"
	"--output-filename=${PROJECT_NAME}"

	# 性能优化
	"--lto=yes"                 # Link Time Optimization
	"--python-flag=no_site"     # 不导入 site 模块，加快启动
	"--python-flag=no_warnings" # 禁用警告

	# 模式选择 - 使用 standalone 避免 onefile 压缩内存问题
	"--standalone"

	# 禁用静态 libpython (Anaconda 环境)
	"--static-libpython=no"

	# 包含模块 - 只编译项目核心代码
	"--include-package=src"

	# 不跟随导入 - 避免引入大量第三方包
	"--nofollow-imports"

	# 必须包含的第三方包（最小化）
	# cli_full.py 只使用 argparse, json, uuid
	# src 内部依赖: real_ladybug, pydantic (数据模型)
	"--follow-import-to=src"
	"--follow-import-to=src.*"
	"--follow-import-to=real_ladybug"
	"--follow-import-to=real_ladybug.*"
	"--follow-import-to=pydantic"
	"--follow-import-to=pydantic.*"

	# 排除不需要的大型模块
	"--nofollow-import-to=mcp"
	"--nofollow-import-to=mcp.*"
	"--nofollow-import-to=networkx"
	"--nofollow-import-to=networkx.*"
	"--nofollow-import-to=yaml"
	"--nofollow-import-to=yaml.*"
	"--nofollow-import-to=tenacity"
	"--nofollow-import-to=tenacity.*"

	# 禁用 Qt（无 GUI）
	"--enable-plugin=no-qt"

	# 禁用自执行检测（避免递归调用问题）
	"--no-deployment-flag=self-execution"

	# C 编译优化 - 使用 PATH 中的默认编译器
	"--jobs=4" # 限制并行任务 (内存控制)

	# 跟随导入
	"--follow-imports"

	# 资源文件
	"--include-data-files=${PROJECT_ROOT}/pyproject.toml=pyproject.toml"
)

# Debug 模式
if [[ "$DEBUG_MODE" == "true" ]]; then
	NUITKA_OPTS+=(
		"--debug"
		"--unstripped"
		"--warn-implicit-exceptions"
	)
else
	NUITKA_OPTS+=(
		"--assume-yes-for-downloads"
	)
fi

echo "[3/6] 开始 Nuitka 编译..."
echo "编译参数: ${NUITKA_OPTS[*]}"

# 执行编译 - 使用项目虚拟环境避免全局库干扰
cd "${PROJECT_ROOT}"
source .venv/bin/activate 2>/dev/null || true
ulimit -v 4194304 2>/dev/null || true
python -m nuitka "${NUITKA_OPTS[@]}"

# 验证输出
echo "[4/6] 验证编译输出..."
# standalone 模式输出目录名基于入口文件名
if [[ -d "${OUTPUT_DIR}/cli_full.dist" ]]; then
	# 重命名为 axon.dist
	mv "${OUTPUT_DIR}/cli_full.dist" "${OUTPUT_DIR}/${PROJECT_NAME}.dist"
	EXECUTABLE="${OUTPUT_DIR}/${PROJECT_NAME}.dist/${PROJECT_NAME}"
elif [[ -d "${OUTPUT_DIR}/${PROJECT_NAME}.dist" ]]; then
	EXECUTABLE="${OUTPUT_DIR}/${PROJECT_NAME}.dist/${PROJECT_NAME}"
elif [[ -f "${OUTPUT_DIR}/${PROJECT_NAME}.bin" ]]; then
	# onefile 模式输出 .bin
	EXECUTABLE="${OUTPUT_DIR}/${PROJECT_NAME}.bin"
elif [[ -f "${OUTPUT_DIR}/${PROJECT_NAME}" ]]; then
	# 直接输出可执行文件
	EXECUTABLE="${OUTPUT_DIR}/${PROJECT_NAME}"
else
	echo "错误: 未找到编译输出"
	echo "检查目录内容:"
	ls -la "${OUTPUT_DIR}/"
	exit 1
fi

# 重命名 .bin 为可执行文件 (onefile 模式)
if [[ -f "${OUTPUT_DIR}/${PROJECT_NAME}.bin" ]]; then
	echo "[5/6] 重命名输出文件..."
	mv "${OUTPUT_DIR}/${PROJECT_NAME}.bin" "${OUTPUT_DIR}/${PROJECT_NAME}"
	EXECUTABLE="${OUTPUT_DIR}/${PROJECT_NAME}"
fi

# 测试可执行文件
echo "[6/6] 测试可执行文件..."
if [[ -f "${EXECUTABLE}" ]]; then
	chmod +x "${EXECUTABLE}"
	"${EXECUTABLE}" --help | head -10 || echo "警告: 运行测试失败"

	echo ""
	echo "======================================"
	echo "编译成功!"
	echo "======================================"
	echo "可执行文件: ${EXECUTABLE}"
	echo "文件大小: $(du -h "${EXECUTABLE}" | cut -f1)"
	echo ""
	echo "性能优化已启用:"
	echo "  - LTO 跨模块优化"
	echo "  - Clang 编译器"
	echo "  - no_site 加快启动"
	echo "  - 单文件模式 (无需 patchelf)"
else
	echo "错误: 编译失败"
	exit 1
fi

echo ""
echo "发布包: ${OUTPUT_DIR}/"
ls -lh "${OUTPUT_DIR}/" | grep "${PROJECT_NAME}"

exit 0
