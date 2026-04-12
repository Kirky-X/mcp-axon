# 🤝 贡献指南

### MCP-Axon 项目贡献指南

---

## 欢迎贡献者！

感谢您对 MCP-Axon 项目的关注！我们欢迎所有形式的贡献，包括代码、文档、测试、错误报告和功能建议。

## 贡献方式

| 方式 | 说明 |
|-----|------|
| 💻 代码贡献 | 修复 bug、添加新功能、性能优化、编写测试 |
| 📝 文档改进 | 完善文档、改进指南、修正错误 |
| 🧪 测试 | 编写测试、发现 bug |
| 💬 社区支持 | 回答问题、帮助其他贡献者 |

---

## 📋 目录

- [行为准则](#行为准则)
- [开始贡献](#开始贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [提交更改](#提交更改)
- [Pull Request](#pull-request)

---

## 行为准则

### ✅ 应该做的

- 尊重和包容他人
- 欢迎新贡献者
- 接受建设性批评
- 专注于社区利益
- 对他人表示同理心

### ❌ 不应该做的

- 使用冒犯性语言
- 骚扰或侮辱他人
- 发布私人信息
- 进行人身攻击
- 打断讨论

---

## 开始贡献

### 前置条件

在开始之前，请确保您已安装：

- **Git** - 版本控制
- **Python** - 3.12+
- **uv** - 包管理器

### 环境设置

```bash
# 1. Fork 本仓库
# 点击 GitHub 上的 Fork 按钮

# 2. 克隆您的 fork
git clone https://github.com/YOUR_USERNAME/mcp-axon.git
cd mcp-axon

# 3. 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 4. 安装依赖
uv pip install -e ".[dev]"

# 5. 验证安装
uv run pytest tests/ -v --tb=short
```

### 添加上游仓库

```bash
# 添加上游仓库
git remote add upstream https://github.com/Kirky-X/mcp-axon.git

# 验证远程仓库
git remote -v
# origin    your-fork-URL
# upstream  original-repo-URL
```

---

## 开发流程

### 标准贡献流程

```
Fork 仓库 → 创建分支 → 编写代码 → 编写测试 → 运行测试 → 提交 → 推送 → 创建 PR
```

### 创建分支

```bash
# 更新主分支
git fetch upstream
git checkout main
git merge upstream/main

# 创建功能分支
git checkout -b feature/your-feature-name

# 或修复 bug
git checkout -b fix/issue-123
```

**分支命名规范：**
- `feature/` - 新功能
- `fix/` - Bug 修复
- `docs/` - 文档改进
- `test/` - 测试改进
- `refactor/` - 代码重构

### 编写代码

```python
# 添加您的实现
def new_feature() -> Dict[str, Any]:
    """功能描述

    Args:
        param_name: 参数描述

    Returns:
        返回值描述
    """
    # 实现代码
    return {"result": "value"}
```

### 编写测试

```python
# tests/test_services/test_example.py
import pytest
from src.core.sdk import RequirementSDK

class TestExample:
    """测试类"""

    @pytest.fixture
    def sdk(self):
        """测试 fixture"""
        return RequirementSDK()

    def test_new_feature(self, sdk):
        """测试新功能"""
        result = sdk.create_project(name="测试项目", description="测试")
        assert result["success"] is True
        assert "id" in result
```

### 运行测试

```bash
# 格式化代码
uv run ruff format .

# 检查代码
uv run ruff check .

# 类型检查
uv run mypy src/

# 运行所有测试
uv run pytest tests/ -v --cov=src

# 运行特定测试
uv run pytest tests/test_services/test_example.py -v

# 运行性能测试
uv run pytest tests/performance/ -v
```

---

## 代码规范

### Python 风格指南

遵循 PEP 8 和项目规范：

| 规范 | 说明 |
|-----|------|
| **命名** | 使用描述性名称，如 `project_id` 而不是 `pid` |
| **类型注解** | 所有函数必须添加类型注解 |
| **文档字符串** | 公开函数必须有 docstring |
| **行长度** | 最大 100 字符 |

### 好的示例

```python
def create_project(name: str, description: str = "") -> Dict[str, Any]:
    """创建新的需求链项目

    Args:
        name: 项目名称
        description: 项目描述（可选）

    Returns:
        包含项目 ID 和创建信息的字典
    """
    # 实现
    return {"id": "uuid", "name": name, "success": True}
```

### 避免的示例

```python
# ❌ 避免使用模糊名称
def do_stuff(d):
    pass

# ❌ 避免缺少类型注解
def process(data):
    pass

# ❌ 避免缺少文档
def helper():
    # 实现
    pass
```

### 代码组织

```
src/
├── __init__.py
├── core/
│   ├── sdk.py          # SDK 主入口
│   └── containers/     # 依赖注入容器
│       ├── __init__.py
│       ├── config.py   # 容器配置
│       └── database.py # 数据库初始化
├── api/
│   ├── __init__.py
│   ├── mcp_server.py   # MCP 服务器
│   ├── tools.py        # 工具定义 (8个)
│   ├── tool_router.py  # 工具路由器
│   └── http_server.py  # HTTP 服务器
├── db/
│   ├── __init__.py
│   ├── graph_models.py     # Pydantic 模型
│   ├── graph_queries.py    # Cypher 查询
│   └── schema.py
├── services/
│   ├── __init__.py
│   ├── project_manager.py
│   ├── requirement_manager.py
│   ├── dependency_service.py
│   ├── validation_service.py
│   ├── chain_builder.py
│   ├── chain_orchestrator.py
│   ├── complexity_evaluator.py
│   └── decomposition_advisor.py
├── cli/
│   ├── __init__.py
│   ├── cli.py          # Typer CLI
│   └── cli_full.py
└── utils/
    ├── __init__.py
    ├── cache.py
    ├── rate_limiter.py
    ├── lock_manager.py
    ├── snapshot_manager.py
    └── ...
```

---

## 测试指南

### 测试类别

| 类型 | 用途 | 位置 |
|-----|------|------|
| **单元测试** | 测试单个函数/类 | `tests/unit/` |
| **集成测试** | 测试服务集成 | `tests/test_integration/` |
| **端到端测试** | 测试完整流程 | `tests/test_e2e/` |
| **性能测试** | 性能基准测试 | `tests/performance/` |

### 测试覆盖率目标

- **总体覆盖率**: ≥ 80%
- **核心模块**: ≥ 90%

### 运行测试

```bash
# 运行所有测试
uv run pytest tests/ -v --cov=src

# 生成覆盖率报告
uv run pytest tests/ --cov=src --cov-report=html

# 查看报告
open htmlcov/index.html
```

---

## 提交更改

### 提交信息格式

```bash
# 格式: <类型>(<范围>): <描述>

git commit -m "feat(requirement): 添加需求复杂度评估"
git commit -m "fix(dependency): 修复循环依赖检测"
git commit -m "docs(readme): 更新安装说明"
git commit -m "test(service): 添加单元测试"
```

**提交类型：**
- `feat` - 新功能
- `fix` - Bug 修复
- `docs` - 文档
- `style` - 格式（不影响代码）
- `refactor` - 重构
- `test` - 测试
- `chore` - 维护

### 提交信息模板

```
<类型>(<范围>): 简短描述

详细描述（可选）

关闭问题: Closes #123
```

### 推送到分支

```bash
git push origin feature/your-feature-name
```

---

## Pull Request

### 创建 PR

1. 访问您的 fork仓库
2. 点击 "Compare & pull request"
3. 填写 PR 模板
4. 关联相关 issues
5. 提交！

### PR 模板

```markdown
## 描述
简要描述更改内容

## 更改类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档更新
- [ ] 性能改进
- [ ] 代码重构

## 更改内容
- 更改 1
- 更改 2
- 更改 3

## 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试完成

## 检查清单
- [ ] 代码符合规范
- [ ] 自检完成
- [ ] 复杂代码已添加注释
- [ ] 文档已更新
- [ ] 没有新警告
- [ ] 测试已添加/更新
```

### PR 最佳实践

| ✅ 推荐 | ❌ 避免 |
|---------|---------|
| 专注于单个问题 | 多个不相关的更改 |
| 小而可 review | 大型 diff（>500 行）|
| 清晰的描述 | 缺少上下文 |
| 包含测试 | 没有测试 |
| 文档已更新 | 未经文档化的更改 |

### 审核流程

**时间线：**
- 初始审核: 1-3 天
- 反馈轮次: 2-5 天
- 批准合并: 1-2 天

**审核标准：**
- ✅ 功能是否符合预期？
- ✅ 代码质量是否良好？
- ✅ 测试是否充分？
- ✅ 文档是否完善？
- ✅ 是否有性能影响？
- ✅ 是否有安全问题？

---

## 社区

### 联系方式

| 渠道 | 说明 |
|-----|------|
| [GitHub Issues](https://github.com/Kirky-X/mcp-axon/issues) | Bug 报告和功能请求 |
| [GitHub Discussions](https://github.com/Kirky-X/mcp-axon/discussions) | 问答和讨论 |

### 致谢

感谢所有贡献者！贡献者将：
- 列在 CONTRIBUTORS.md 中
- 显示在 README 贡献者部分
- 在发布说明中提及

---

## 🎉 感谢您！

您的贡献使这个项目变得更好。

**准备好贡献了吗？** [创建第一个 issue](https://github.com/Kirky-X/mcp-axon/issues/new) 或 [开始讨论](https://github.com/Kirky-X/mcp-axon/discussions/new)！

---

**[用户指南](USER_GUIDE.md)** • **[API 参考](API_REFERENCE.md)** • **[FAQ](FAQ.md)**
