# 🐍 Python 项目 GitHub Actions 完整配置包

为 Python 项目定制的 GitHub Actions 工作流配置包，包含 CI/CD、发布管理和代码质量检查。

## 📦 包含内容

```
python-github-workflows/
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI 健康检查工作流
│       ├── release.yml         # 自动发布工作流
│       └── tag-deleted.yml     # Tag 删除清理工作流
├── pyproject.toml              # 项目配置文件模板
├── pre-commit-check.sh         # 完整本地 CI 检查
├── quick-check.sh              # 快速检查
├── fix-issues.sh               # 自动修复脚本
├── install-git-hook.sh         # Git Hook 安装
└── README.md                   # 本文档
```

## ✨ 核心功能

### 1. CI 健康检查 (ci.yml)
- ✅ **多版本测试**: Python 3.9, 3.10, 3.11, 3.12
- ✅ **多平台测试**: Linux, macOS, Windows
- ✅ **代码格式**: ruff format 或 black
- ✅ **Lint 检查**: ruff check 或 flake8
- ✅ **类型检查**: mypy
- ✅ **安全审计**: safety, bandit, pip-audit
- ✅ **代码覆盖率**: pytest-cov + codecov
- ✅ **文档生成**: Sphinx

### 2. 自动发布 (release.yml)
- 🏷️ **版本管理**: 自动从 git tag 更新版本号
- 📦 **构建分发包**: wheel 和 sdist
- 🔨 **二进制打包**: PyInstaller 构建可执行文件
- 🚀 **GitHub Release**: 自动创建并上传资源
- 📤 **PyPI 发布**: 使用 Trusted Publishing 自动发布
- 📝 **自动 Changelog**: 基于 git commit 历史

### 3. Tag 删除清理 (tag-deleted.yml)
- 🗑️ **自动删除 Release**: 删除 tag 时清理 GitHub Release
- ⚠️ **PyPI 提醒**: 提示 PyPI 无法删除版本

## 🚀 快速开始

### 1. 项目结构设置

推荐的项目结构：

```
your-project/
├── src/
│   └── your_package/
│       ├── __init__.py
│       └── main.py
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── docs/
│   ├── conf.py
│   └── index.rst
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── release.yml
│       └── tag-deleted.yml
├── pyproject.toml
├── README.md
└── LICENSE
```

### 2. 复制配置文件

```bash
# 复制工作流文件
cp -r .github/ your-project/

# 复制或合并 pyproject.toml（如果已有则合并配置）
cp pyproject.toml your-project/

# 复制本地检查脚本
cp *-check.sh fix-issues.sh install-git-hook.sh your-project/
chmod +x your-project/*.sh
```

### 3. 配置项目信息

编辑 `pyproject.toml`，替换以下占位符：

```toml
name = "YOUR_PACKAGE_NAME"          # 你的包名
authors = [{name = "Your Name", email = "your.email@example.com"}]
[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/YOUR_REPO"
Repository = "https://github.com/YOUR_USERNAME/YOUR_REPO"
```

### 4. 配置 GitHub Secrets

在 `Settings → Secrets and variables → Actions` 中添加：

| Secret 名称 | 用途 | 获取方式 |
|------------|------|---------|
| `CODECOV_TOKEN` | 代码覆盖率上传 | https://codecov.io/ |

**注意**: PyPI Trusted Publishing 不需要 API token，但需要在 PyPI 配置。

### 5. 配置 PyPI Trusted Publishing

1. 访问 https://pypi.org/manage/account/publishing/
2. 点击 "Add a new publisher"
3. 填写信息：
   - PyPI Project Name: `YOUR_PACKAGE_NAME`
   - Owner: `YOUR_USERNAME`
   - Repository name: `YOUR_REPO`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

## 🏷️ GitHub 徽章

### 复制粘贴模板（替换大写部分）

```markdown
<!-- CI 状态 -->
[![CI](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/ci.yml)

<!-- PyPI 版本 -->
[![PyPI](https://img.shields.io/pypi/v/YOUR_PACKAGE_NAME.svg)](https://pypi.org/project/YOUR_PACKAGE_NAME/)

<!-- Python 版本 -->
[![Python Versions](https://img.shields.io/pypi/pyversions/YOUR_PACKAGE_NAME.svg)](https://pypi.org/project/YOUR_PACKAGE_NAME/)

<!-- 下载量 -->
[![Downloads](https://pepy.tech/badge/YOUR_PACKAGE_NAME)](https://pepy.tech/project/YOUR_PACKAGE_NAME)

<!-- 代码覆盖率 -->
[![codecov](https://codecov.io/gh/YOUR_USERNAME/YOUR_REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/YOUR_REPO)

<!-- 许可证 -->
[![License](https://img.shields.io/pypi/l/YOUR_PACKAGE_NAME.svg)](https://github.com/YOUR_USERNAME/YOUR_REPO/blob/main/LICENSE)

<!-- 代码风格 -->
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
```

### 一行式（推荐）

```markdown
[![CI](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/ci.yml) [![PyPI](https://img.shields.io/pypi/v/YOUR_PACKAGE_NAME.svg)](https://pypi.org/project/YOUR_PACKAGE_NAME/) [![Python Versions](https://img.shields.io/pypi/pyversions/YOUR_PACKAGE_NAME.svg)](https://pypi.org/project/YOUR_PACKAGE_NAME/) [![codecov](https://codecov.io/gh/YOUR_USERNAME/YOUR_REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/YOUR_REPO) [![License](https://img.shields.io/pypi/l/YOUR_PACKAGE_NAME.svg)](LICENSE)
```

## 📖 使用示例

### 发布新版本

```bash
# 1. 确保代码已提交并通过测试
git add .
git commit -m "feat: add new feature"
git push

# 2. 创建版本 tag
git tag v1.0.0

# 3. 推送 tag（触发自动发布）
git push origin v1.0.0

# ✨ GitHub Actions 会自动：
#    - 更新 pyproject.toml 和 __init__.py 中的版本号
#    - 运行所有测试
#    - 构建 wheel 和 sdist
#    - 构建二进制文件（如配置）
#    - 创建 GitHub Release
#    - 发布到 PyPI
```

### 撤回错误的发布

```bash
# 1. 删除本地 tag
git tag -d v1.0.0

# 2. 删除远程 tag
git push origin :refs/tags/v1.0.0

# ✨ GitHub Actions 会自动：
#    - 删除对应的 GitHub Release

# ⚠️ PyPI 无法删除版本
# 需要手动 yank（在 PyPI 网站上操作）：
# https://pypi.org/project/YOUR_PACKAGE_NAME/
```

### 本地开发流程

```bash
# 1. 安装开发依赖
pip install -e ".[dev,test]"

# 2. 安装 Git hook（推荐）
./install-git-hook.sh

# 3. 日常开发
# 写代码...
./quick-check.sh  # 快速验证

# 4. 提交前完整检查
./pre-commit-check.sh

# 5. 发现问题？自动修复
./fix-issues.sh
```

## 🔧 本地检查脚本

### 1. quick-check.sh - 快速检查

```bash
./quick-check.sh

# 检查项目：
# [1/5] 格式检查 ✓
# [2/5] Import 排序 ✓
# [3/5] Lint 检查 ✓
# [4/5] 类型检查 ✓
# [5/5] 运行测试 ✓
```

### 2. pre-commit-check.sh - 完整检查

```bash
./pre-commit-check.sh

# 检查项目：
# [1/8] 检查并安装依赖
# [2/8] 检查代码格式 (ruff/black)
# [3/8] 检查 import 排序 (ruff/isort)
# [4/8] 运行 Lint 检查 (ruff/flake8)
# [5/8] 运行类型检查 (mypy)
# [6/8] 运行所有测试 (pytest)
# [7/8] 运行安全检查 (safety/bandit)
# [8/8] 计算代码覆盖率 (pytest-cov)
```

### 3. fix-issues.sh - 自动修复

```bash
./fix-issues.sh

# 修复项目：
# [1/4] 修复代码格式 (ruff format / black)
# [2/4] 修复 import 排序 (ruff / isort)
# [3/4] 尝试修复 Lint 问题 (ruff --fix)
# [4/4] 检查依赖更新 (pip-review)
```

### 4. install-git-hook.sh - 自动化

```bash
./install-git-hook.sh

# 安装后，每次 commit 自动检查
git commit -m "feat: add feature"  # 自动触发检查

# 跳过检查（不推荐）
git commit --no-verify -m "message"
```

## 🛠️ 工具安装

### 核心工具（推荐）

```bash
# 使用 ruff（推荐：快速、现代）
pip install ruff mypy pytest pytest-cov

# 或使用传统工具
pip install black isort flake8 mypy pytest pytest-cov
```

### 安全工具

```bash
pip install safety bandit pip-audit
```

### 文档工具

```bash
pip install sphinx sphinx-rtd-theme
```

### 一键安装所有开发工具

```bash
pip install -e ".[dev,test,docs,security]"
```

## 📋 配置文件说明

### pyproject.toml 关键配置

```toml
[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["-v", "--cov=src", "--cov-report=xml"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:"]
```

## ⚠️ 重要提醒

### 关于 PyPI

1. **版本无法删除**
   - 一旦发布到 PyPI，版本将永久存在
   - 只能 yank（标记为不推荐）

2. **Trusted Publishing 优势**
   - 无需管理 API token
   - 更安全
   - 自动轮换凭证

3. **发布前检查清单**
   - [ ] 所有测试通过
   - [ ] 文档已更新
   - [ ] CHANGELOG 已更新
   - [ ] 版本号正确
   - [ ] 许可证信息完整

### 二进制打包注意事项

在 `release.yml` 中：

1. 替换 `YOUR_APP_NAME` 为实际的应用名称
2. 替换 `YOUR_MAIN_SCRIPT.py` 为实际的入口文件
3. 如果不需要二进制打包，删除 `build-binaries` job

## 🐛 故障排查

### CI 失败

| 问题 | 解决方案 |
|------|---------|
| 格式检查失败 | 运行 `ruff format .` 或 `black .` |
| Lint 警告 | 运行 `ruff check --fix .` |
| 类型错误 | 检查 mypy 输出，添加类型注解 |
| 测试失败 | 运行 `pytest -v` 查看详情 |
| 覆盖率上传失败 | 检查 CODECOV_TOKEN |

### PyPI 发布失败

| 问题 | 解决方案 |
|------|---------|
| Trusted Publishing 未配置 | 在 PyPI 添加 publisher |
| 包名已存在 | 更改包名或联系 PyPI 支持 |
| 版本已存在 | 更改版本号 |
| 构建失败 | 检查 pyproject.toml 配置 |

### 本地检查问题

```bash
# 工具未安装
pip install ruff mypy pytest pytest-cov

# 虚拟环境问题
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 重新安装依赖
pip install -e ".[dev,test]"
```

## 📚 参考资源

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Python Packaging Guide](https://packaging.python.org/)

---

**祝你的 Python 项目发布顺利！** 🐍✨
