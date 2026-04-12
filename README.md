# 🚀 MCP-Axon

<p>
  <img src="https://img.shields.io/badge/version-1.0.0-blue.svg" alt="Version">
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
| **MCP 协议** | 基于 Model Context Protocol 的标准化接口 (8个合并工具) |
| **图数据库** | real_ladybug 图数据库存储,支持复杂依赖关系 |
| **依赖注入** | dependency-injector 容器管理服务生命周期 |
| **速率限制** | 内置请求限流保护,防止滥用 |
| **CLI 工具** | 完整的命令行界面 (Typer) |
| **API 版本管理** | 版本查询和兼容性管理 |
| **跨平台** | Python 实现,支持多平台部署 |

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Kirky-X/axon.git
cd axon

# 方式一: 使用安装脚本(推荐)
bash scripts/install.sh

# 方式二: 手动安装
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装项目
uv pip install -e .[dev]
```

### 环境变量配置

```bash
# 设置数据库路径 (可选,默认为 mcp_axon.lbug)
export MCP_AXON_DB_PATH="my_custom_db.lbug"
```

### 基本使用

#### 命令行方式

```bash
# 使用 CLI 工具
axon project create --name "我的项目" --desc "项目描述"
axon requirement create --project <project_id> --content "实现用户认证"
axon execution next --project <project_id>

# 启动 MCP 服务器
axon-server

# 启动 HTTP 服务器
axon-server --mode http --http-port 8080

# 运行测试
uv run pytest tests/ -v --cov=src
```

---

### MCP 客户端配置

在 Claude Desktop 或其他 MCP 客户端中使用以下配置：

```json
{
  "mcpServers": {
    "axon": {
      "command": "uv",
      "args": [
        "run",
        "--isolated",
        "--with",
        "git+https://github.com/Kirky-X/axon.git",
        "axon"
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
| [API 参考](docs/API_REFERENCE.md) | MCP 工具完整文档 (8个合并工具) |
| [架构设计](docs/ARCHITECTURE.md) | 系统架构设计 |
| [常见问题](docs/FAQ.md) | 常见问题解答 |
| [贡献指南](docs/CONTRIBUTING.md) | 贡献代码指南 |
| [缓存配置](docs/CACHE_CONFIG.md) | 缓存配置说明 |

---

## 🧪 测试

```bash
# 运行所有测试
uv run pytest tests/ -v --cov=src

# 运行性能测试
uv run pytest tests/performance/ -v

# 运行端到端测试
uv run pytest tests/test_e2e/ -v

# 运行预检查(包含测试)
bash scripts/pre-commit-check.sh
```

**测试结果**: 所有测试通过 ✅

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
