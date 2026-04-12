# 缓存配置说明

## 概述

本项目已配置将所有工具缓存重定向到 `/tmp` 目录，避免在项目根目录生成缓存文件夹。

## 已配置的工具

### 1. pytest
- **配置位置**: `pyproject.toml` → `[tool.pytest.ini_options]`
- **缓存目录**: `/tmp/pytest_cache`

### 2. mypy
- **配置位置**: `pyproject.toml` → `[tool.mypy]`
- **缓存目录**: `/tmp/mypy_cache`

### 3. ruff
- **配置位置**: `ruff.toml`
- **缓存目录**: 使用 `--cache-dir` 参数指定

## 使用方法

### 运行测试（不生成 .benchmarks）
```bash
# 正常运行测试
python -m pytest tests/ -v
```

### 类型检查（不生成 .mypy_cache）
```bash
# 使用配置的缓存目录
mypy src/

# 或完全禁用缓存
mypy src/ --cache-dir=/dev/null
```

### 代码格式化（不生成 .ruff_cache）
```bash
# 使用临时缓存
ruff check src/ --cache-dir=/tmp/ruff_cache

# 或禁用缓存
ruff check src/ --no-cache
```

## 优势

✅ **项目目录整洁** - 不会生成 `.ruff_cache`、`.mypy_cache`、`.benchmarks` 等目录  
✅ **自动清理** - `/tmp` 目录会定期被系统清理  
✅ **Git 干净** - 不需要在 `.gitignore` 中维护这些目录  
✅ **多项目隔离** - 不同项目的缓存不会冲突  

## 注意事项

⚠️ `/tmp` 目录在系统重启后会被清空，这意味着：
- MyPy 需要重新检查所有文件（首次会较慢）
- pytest 缓存会丢失（影响很小）
- Ruff 需要重新分析代码

---

**最后更新**: 2026-04-12
