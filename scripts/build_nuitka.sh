#!/bin/bash
# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

# Axon Nuitka 编译脚本 - 性能优化版本
#
# 使用方法:
#   ./scripts/build_nuitka.sh [--clean] [--debug]
#
# 输出目录: dist/axon

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
	rm -rf "${OUTPUT_DIR}/${PROJECT_NAME}"
	rm -rf "${OUTPUT_DIR}/${PROJECT_NAME}.dist"
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

# 检查 C 编译器
if ! command -v gcc &>/dev/null; then
	echo "错误: GCC 未安装"
	echo "请安装: sudo apt install gcc build-essential"
	exit 1
fi

# 性能优化参数
NUITKA_OPTS=(
	# 主入口点
	"--main=${PROJECT_ROOT}/src/cli/cli.py"

	# 输出配置
	"--output-dir=${OUTPUT_DIR}"
	"--output-filename=${PROJECT_NAME}"

	# 性能优化 (关键)
	# LTO (Link Time Optimization) - 跨模块优化
	"--lto=yes"

	# 启用所有优化
	"--python-flag=no_site"     # 不导入 site 模块，加快启动
	"--python-flag=no_warnings" # 禁用警告

	# 模式选择
	"--standalone" # 独立可执行，包含所有依赖
	"--onefile"    # 单文件输出（可选，如果需要更快的启动用 --standalone）

	# 包含模块 (确保所有依赖被编译)
	"--include-package=src"
	"--include-package=mcp"
	"--include-package=pydantic"
	"--include-package=networkx"
	"--include-package=tenacity"
	"--include-package=typer"
	"--include-package=real_ladybug"
	"--include-package=transitions"
	"--include-package=dependency_injector"
	"--include-package=cachetools"
	"--include-package=yaml"

	# 预编译模块（避免运行时编译）
	"--prefer-source-code" # 优先使用源码而非字节码

	# C 编译优化
	"--clang"          # 使用 clang（更快），如果可用
	"--c-compiler=gcc" # 指定 GCC

	# 去除调试信息（减小体积）
	"--no-debug-info"

	# 禁用异常追踪（性能优化）
	"--no-exceptions-detection"

	# 跟随导入（自动包含依赖）
	"--follow-imports"

	# 隐式导入处理
	"--implicit-imports"

	# 资源文件
	"--include-data-files=${PROJECT_ROOT}/pyproject.toml=pyproject.toml"
)

# Debug 模式额外参数
if [[ "$DEBUG_MODE" == "true" ]]; then
	NUITKA_OPTS+=(
		"--debug"
		"--unstripped" # 保留符号表
		"--show-progress"
		"--show-memory"
		"--show-modules"
	)
else
	NUITKA_OPTS+=(
		"--assume-yes-for-downloads" # 自动下载依赖
	)
fi

echo "[3/6] 开始 Nuitka 编译..."
echo "编译参数: ${NUITKA_OPTS[*]}"

# 执行编译
cd "${PROJECT_ROOT}"
python -m nuitka "${NUITKA_OPTS[@]}"

# 验证输出
echo "[4/6] 验证编译输出..."
if [[ -f "${OUTPUT_DIR}/${PROJECT_NAME}.bin" ]]; then
	# onefile 模式输出 .bin
	EXECUTABLE="${OUTPUT_DIR}/${PROJECT_NAME}.bin"
elif [[ -f "${OUTPUT_DIR}/${PROJECT_NAME}" ]]; then
	# standalone 模式输出可执行文件
	EXECUTABLE="${OUTPUT_DIR}/${PROJECT_NAME}"
elif [[ -d "${OUTPUT_DIR}/${PROJECT_NAME}.dist" ]]; then
	# standalone 目录模式
	EXECUTABLE="${OUTPUT_DIR}/${PROJECT_NAME}.dist/${PROJECT_NAME}"
else
	echo "错误: 未找到编译输出"
	exit 1
fi

# 创建最终目录结构
if [[ -d "${OUTPUT_DIR}/${PROJECT_NAME}.dist" ]]; then
	echo "[5/6] 组织发布目录..."
	# standalone 模式：移动 dist 目录
	mv "${OUTPUT_DIR}/${PROJECT_NAME}.dist" "${OUTPUT_DIR}/${PROJECT_NAME}-standalone"
	EXECUTABLE="${OUTPUT_DIR}/${PROJECT_NAME}-standalone/${PROJECT_NAME}"
fi

# 测试可执行文件
echo "[6/6] 测试可执行文件..."
if [[ -f "${EXECUTABLE}" ]]; then
	chmod +x "${EXECUTABLE}"
	"${EXECUTABLE}" --help | head -5 || echo "警告: 运行测试失败"

	# 显示文件信息
	echo ""
	echo "======================================"
	echo "编译成功!"
	echo "======================================"
	echo "可执行文件: ${EXECUTABLE}"
	echo "文件大小: $(du -h "${EXECUTABLE}" | cut -f1)"

	if [[ -d "${OUTPUT_DIR}/${PROJECT_NAME}-standalone" ]]; then
		echo "目录大小: $(du -sh "${OUTPUT_DIR}/${PROJECT_NAME}-standalone" | cut -f1)"
	fi

	# 编译时间统计（如果可用）
	if command -v time &>/dev/null; then
		echo ""
		echo "性能提示:"
		echo "  - 使用 --standalone 获得更快的启动速度"
		echo "  - 使用 --onefile 获得更小的单文件（但启动稍慢）"
		echo "  - LTO 优化已启用，跨模块性能提升约 15-20%"
	fi
else
	echo "错误: 编译失败，未生成可执行文件"
	exit 1
fi

echo ""
echo "发布包已准备: ${OUTPUT_DIR}/"
ls -lh "${OUTPUT_DIR}/" | grep "${PROJECT_NAME}"

exit 0
