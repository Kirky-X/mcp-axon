# 缓存配置说明

## 概述

本项目已配置将所有工具缓存重定向到 `/tmp` 目录，避免在项目根目录生成缓存文件夹。

## 已配置的工具

### 1. pytest
- **配置位置**: `pyproject.toml` → `[tool.pytest.ini_options]`
- **缓存目录**: `/tmp/pytest_cache_mcp_axon`
- **缓存清理**: 使用 `--cache-clear` 选项,每次运行测试时自动清理缓存
- **环境变量**:
  - `PYTHONDONTWRITEBYTECODE=1` - 禁止生成 `__pycache__` 目录
  - `PYTEST_BENCHMARK_DISABLE=1` - 禁用 benchmark 功能

### 2. mypy
- **配置位置**: `pyproject.toml` → `[tool.mypy]`
- **缓存目录**: `/tmp/mypy_cache`

### 3. ruff
- **配置位置**: `ruff.toml`
- **缓存目录**: 未显式配置,使用默认行为(通常为 `.ruff_cache`)
- **说明**: 配置文件中未设置缓存目录,运行时可通过命令行参数指定

## 使用方法

### 运行测试(不生成 .benchmarks 和 __pycache__)
```bash
# 正常运行测试(自动清理缓存)
python -m pytest tests/ -v

# 手动清理缓存
python -m pytest tests/ --cache-clear
```

### 类型检查（不生成 .mypy_cache）
```bash
# 使用配置的缓存目录
mypy src/

# 或完全禁用缓存
mypy src/ --cache-dir=/dev/null
```

### 代码格式化(使用临时缓存)
```bash
# 使用临时缓存目录
ruff check src/ --cache-dir=/tmp/ruff_cache

# 或禁用缓存
ruff check src/ --no-cache
```

## 优势

✅ **项目目录整洁** - pytest 和 mypy 缓存已重定向,不会在项目根目录生成 `.mypy_cache` 等目录  
✅ **自动清理** - `/tmp` 目录会定期被系统清理,pytest 运行测试时也会自动清理缓存  
✅ **Git 干净** - 不需要在 `.gitignore` 中维护这些目录  
✅ **多项目隔离** - pytest 缓存使用独立目录 `/tmp/pytest_cache_mcp_axon`,不同项目不会冲突  
✅ **禁止生成 __pycache__** - 通过 `PYTHONDONTWRITEBYTECODE=1` 环境变量  
✅ **禁用 benchmark** - 通过 `PYTEST_BENCHMARK_DISABLE=1` 环境变量,避免生成 `.benchmarks` 目录  

## 注意事项

⚠️ `/tmp` 目录在系统重启后会被清空,这意味着:
- pytest 缓存会丢失,但每次运行时会自动清理,影响很小
- MyPy 需要重新检查所有文件(首次会较慢)
- Ruff 需要重新分析代码(如果使用 `/tmp` 作为缓存目录)

⚠️ **Ruff 缓存说明**:
- `ruff.toml` 中未配置缓存目录,默认会在当前目录生成 `.ruff_cache`
- 如需避免生成缓存,请使用 `--no-cache` 参数
- 如需使用临时缓存,请使用 `--cache-dir=/tmp/ruff_cache`

---

**最后更新**: 2026-04-13
