# 🐍 Python CI 检查脚本 - 快速参考卡

## 📦 脚本总览

```
┌─────────────────────────────────────────────────────────────┐
│  Python 本地 CI 检查脚本                                     │
├─────────────────────────────────────────────────────────────┤
│  quick-check.sh          ⚡ 快速检查 (1-2 分钟)             │
│  pre-commit-check.sh     🔍 完整检查 (5-10 分钟)           │
│  fix-issues.sh           🔧 自动修复                        │
│  install-git-hook.sh     🪝 安装 Git Hook                   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速命令

### 首次使用
```bash
# 1. 设置权限
chmod +x *.sh

# 2. 安装依赖
pip install -e ".[dev,test]"

# 3. 安装 Git hook（推荐）
./install-git-hook.sh
```

### 日常使用
```bash
# 快速检查
./quick-check.sh

# 自动修复
./fix-issues.sh

# 提交前完整检查
./pre-commit-check.sh
```

## 📊 检查对比

| 特性 | quick-check | pre-commit-check | GitHub CI |
|------|-------------|------------------|-----------|
| 速度 | ⚡⚡⚡ | ⚡⚡ | ⚡ |
| 格式检查 | ✅ | ✅ | ✅ |
| Import 排序 | ✅ | ✅ | ✅ |
| Lint | ✅ | ✅ | ✅ |
| 类型检查 | ✅ | ✅ | ✅ |
| 测试 | ✅ | ✅ | ✅ |
| 安全审计 | ❌ | ✅ | ✅ |
| 覆盖率 | ❌ | ✅ | ✅ |
| 多版本 | ❌ | ❌ | ✅ |
| 多平台 | ❌ | ❌ | ✅ |

## 🎯 使用场景

### 场景 1: 日常开发
```bash
# 写代码 → 快速验证
./quick-check.sh
```

### 场景 2: 发现问题
```bash
# 自动修复 → 重新检查
./fix-issues.sh
./quick-check.sh
```

### 场景 3: 准备提交
```bash
# 完整检查 → 提交
./pre-commit-check.sh
git add .
git commit -m "feat: new feature"
```

### 场景 4: 自动化
```bash
# 安装 hook
./install-git-hook.sh

# 之后每次提交自动检查
git commit -m "message"
```

## 🔧 检查项目详情

### quick-check.sh
```
[1/5] 格式检查 ✓      (ruff format / black)
[2/5] Import 排序 ✓    (ruff / isort)
[3/5] Lint 检查 ✓      (ruff check / flake8)
[4/5] 类型检查 ✓       (mypy)
[5/5] 运行测试 ✓       (pytest)
```

### pre-commit-check.sh
```
[1/8] 检查并安装依赖
[2/8] 代码格式 (ruff format / black)
[3/8] Import 排序 (ruff / isort)
[4/8] Lint 检查 (ruff check / flake8)
[5/8] 类型检查 (mypy)
[6/8] 运行测试 (pytest)
[7/8] 安全检查 (safety / bandit / pip-audit)
[8/8] 代码覆盖率 (pytest-cov)
```

### fix-issues.sh
```
[1/4] 修复代码格式 (ruff format / black)
[2/4] 修复 Import 排序 (ruff / isort)
[3/4] 修复 Lint 问题 (ruff --fix)
[4/4] 检查依赖更新 (pip-review)
```

## ⚙️ 工具安装

### 方法 1: 使用 pyproject.toml（推荐）
```bash
pip install -e ".[dev,test]"
```

### 方法 2: 手动安装
```bash
# 核心工具（ruff 推荐，速度快）
pip install ruff mypy pytest pytest-cov

# 或使用传统工具
pip install black isort flake8 mypy pytest pytest-cov

# 安全工具
pip install safety bandit pip-audit

# 依赖管理
pip install pip-review
```

## 💡 常用命令

### 手动运行检查
```bash
# 格式化
ruff format .        # 或 black .

# 排序 import
ruff check --select I --fix .  # 或 isort .

# Lint
ruff check .         # 或 flake8 .

# 类型检查
mypy .

# 测试
pytest

# 覆盖率
pytest --cov=.
```

### 查看详细输出
```bash
# 详细 lint 信息
ruff check . --verbose

# 详细测试信息
pytest -vv

# 查看覆盖率报告
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## 🐛 故障排查

### 工具未安装
```bash
# 检查工具是否安装
which ruff mypy pytest

# 安装缺失工具
pip install ruff mypy pytest pytest-cov
```

### 虚拟环境问题
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# 安装依赖
pip install -e ".[dev,test]"
```

### 检查通过但 CI 失败
```bash
# 确保使用相同 Python 版本
python --version

# 清理缓存
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# 重新安装
pip install -e ".[dev,test]" --force-reinstall
```

## 📝 配置文件

### pyproject.toml 关键位置
```toml
# 格式化配置
[tool.ruff]
line-length = 100

# Lint 配置
[tool.ruff.lint]
select = ["E", "W", "F", "I", "B"]

# 类型检查配置
[tool.mypy]
disallow_untyped_defs = true

# 测试配置
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--cov=src"]
```

## 🎓 最佳实践

1. **日常开发**: 使用 `quick-check.sh`
2. **提交前**: 运行 `pre-commit-check.sh`
3. **自动化**: 安装 Git hook
4. **持续集成**: 本地检查通过 = CI 通过
5. **代码质量**: 保持 100% 类型覆盖

## 🔗 工具文档

- [Ruff](https://docs.astral.sh/ruff/) - 快速的 Python linter
- [MyPy](https://mypy.readthedocs.io/) - 静态类型检查
- [Pytest](https://docs.pytest.org/) - 测试框架
- [Black](https://black.readthedocs.io/) - 代码格式化（替代方案）
- [isort](https://pycqa.github.io/isort/) - Import 排序（替代方案）

## 📊 徽章快速参考

```markdown
[![CI](https://github.com/USER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/PACKAGE.svg)](https://pypi.org/project/PACKAGE/)
[![Python](https://img.shields.io/pypi/pyversions/PACKAGE.svg)](https://pypi.org/project/PACKAGE/)
[![codecov](https://codecov.io/gh/USER/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USER/REPO)
```

---

**记住：本地检查通过 = CI 流水线通过** ✅🐍
