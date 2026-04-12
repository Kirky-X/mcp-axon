# 🚀 MCP-Axon

<p>
  <img src="https://img.shields.io/badge/version-0.1.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <a href="#"><img src="https://img.shields.io/badge/build-passing-brightgreen.svg" alt="Build"></a>
</p>

<p align="center">
  <strong>基于 MCP 协议的智能需求链化管理系统</strong>
</p>

<p align="center">
  <a href="#-功能特性">功能特性</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-文档">文档</a> •
  <a href="#-贡献">贡献</a>
</p>

---

## ✨ 功能特性

| 核心功能 | 说明 |
|---------|------|
| **需求分解** | 智能分解复杂需求为可执行的子需求 |
| **依赖管理** | 自动检测和管理需求间的依赖关系 |
| **链化构建** | 基于依赖关系构建最优执行链 |
| **并行处理** | 识别并行需求，支持自定义执行顺序 |
| **状态追踪** | 实时追踪项目执行进度和状态 |
| **快照回滚** | 支持项目状态快照和回滚功能 |
| **并发控制** | 项目锁定机制防止并发冲突 |
| **验证管理** | 为叶子节点添加测试用例和验收标准 |

| 高级特性 | 说明 |
|---------|------|
| **MCP 协议** | 基于 Model Context Protocol 的标准化接口 |
| **数据持久化** | SQLite 数据库存储，支持数据完整性 |
| **跨平台** | Python 实现，支持多平台部署 |
| **易于集成** | 标准 MCP 工具接口，易于与 AI 系统集成 |

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Kirky-X/mcp-axon.git
cd mcp-axon

# 方式一: 使用安装脚本(推荐)
bash scripts/install.sh

# 方式二: 手动安装
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装项目
uv pip install -e .[dev]
```

### 基本使用

#### 命令行方式

```bash
# 运行演示
python scripts/main.py demo

# 启动 MCP 服务器
python scripts/main.py server

# 运行测试
python scripts/main.py test

# 运行预检查
bash scripts/pre-commit-check.sh
```

#### Python SDK 方式

```python
from src.core.sdk import RequirementSDK

# 初始化 SDK
sdk = RequirementSDK()

# 创建项目
project = sdk.create_project(
    name="我的项目",
    description="项目描述"
)
print(f"项目创建成功: {project['id']}")

# 添加根需求
root_req = sdk.add_requirement(
    project_id=project["id"],
    content="实现用户认证功能",
    parent_id=None
)

# 标记为叶子节点
sdk.mark_as_leaf(root_req["requirement_id"])

# 添加验证
sdk.add_validation(
    requirement_id=root_req["requirement_id"],
    test_cases=[{
        "name": "登录测试",
        "steps": ["输入用户名密码", "点击登录"],
        "expected_result": "登录成功"
    }],
    acceptance_criteria="用户能够成功登录系统"
)

# 触发链化
chain_result = sdk.trigger_chaining(project["id"])
print(f"链化结果: {chain_result}")

# 获取下一个需求
next_req = sdk.get_next_requirement(project["id"])
print(f"下一个需求: {next_req}")
```

---

### MCP 客户端配置

在 Claude Desktop 或其他 MCP 客户端中使用以下配置：

```json
{
  "mcpServers": {
    "mcp-axon": {
      "command": "uv",
      "args": [
        "run",
        "--isolated",
        "--with",
        "git+https://github.com/Kirky-X/mcp-axon.git",
        "mcp-axon"
      ]
    }
  }
}
```

---

## 📚 文档

| 文档 | 说明 |
|-----|------|
| [用户指南](docs/USER_GUIDE.md) | 完整使用指南 |
| [API 参考](docs/API_REFERENCE.md) | MCP 工具完整文档 |
| [架构设计](docs/ARCHITECTURE.md) | 系统架构设计 |
| [常见问题](docs/FAQ.md) | 常见问题解答 |
| [贡献指南](docs/CONTRIBUTING.md) | 贡献代码指南 |

---

## 🧪 测试

```bash
# 运行所有测试
uv run pytest tests/ -v --cov=src

# 或使用主脚本
python scripts/main.py test

# 运行性能测试
uv run pytest tests/performance/ -v

# 运行端到端测试
uv run pytest tests/test_e2e/ -v

# 运行预检查(包含测试)
bash scripts/pre-commit-check.sh
```

**测试结果**: 279 个测试全部通过 (100%)

---

## 📊 性能

| 操作 | 性能要求 | 实测结果 |
|-----|---------|---------|
| CRUD 操作 | < 50ms | 1.06ms ✅ |
| 拓扑排序 (2000 节点) | < 1000ms | 2.82ms ✅ |
| 全量链化 (2000 节点) | < 2000ms | 92.58ms ✅ |

---

## 🤝 贡献

欢迎贡献代码、文档或报告问题！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目基于 MIT 许可证开源。

---

## 🙏 致谢

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [NetworkX](https://networkx.org/)
- [Pydantic](https://docs.pydantic.dev/)
