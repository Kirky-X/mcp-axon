# MCP-Axon

需求链化管理系统 - 基于 MCP 协议的智能需求管理工具

## 项目简介

MCP-Axon 是一个基于 MCP（Model Context Protocol）协议的需求链化管理系统，通过 AI 交互式对话机制，帮助用户将复杂项目需求逐层分解，并自动构建可执行的需求链表。

### 核心特性

- 🎯 **智能需求分解**：自动评估需求复杂度，提供分解建议
- 🔗 **依赖关系管理**：自动处理需求依赖关系的传递
- 📊 **拓扑排序**：根据依赖关系生成最优执行顺序
- 🤖 **AI 驱动**：与 Claude AI 深度集成，提供交互式体验
- 🔒 **并发安全**：项目锁和乐观锁双重保护

## 技术栈

- **Python**: >= 3.10
- **MCP 协议**: mcp 1.25.0
- **数据库**: SQLite 3.35+ (使用 SQLAlchemy 2.0.23)
- **数据验证**: Pydantic 2.5.0
- **图算法**: NetworkX 3.2.1
- **测试框架**: pytest 7.4.3

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/your-repo/mcp-axon.git
cd mcp-axon

# 使用 uv 创建虚拟环境（推荐）
uv venv
source .venv/bin/activate

# 或使用传统方式
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安装依赖

```bash
uv pip install -r requirements.txt
```

### 3. 配置环境变量（可选）

```bash
export DB_PATH="requirements.db"
export LOG_LEVEL="INFO"
export LOCK_TIMEOUT_MINUTES=30
```

### 4. 初始化数据库

```bash
python -m src.init_db
```

### 5. 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行测试并生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### 6. 启动 MCP 服务器

```bash
python -m src.server
```

## Claude Desktop 配置

在 Claude Desktop 的配置文件中添加以下内容：

```json
{
  "mcpServers": {
    "requirement-chain": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/mcp-axon",
      "env": {
        "DB_PATH": "requirements.db",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## 项目结构

```
mcp-axon/
├── docs/                    # 文档目录
│   ├── prd.md              # 产品需求文档
│   ├── task.md             # 任务开发清单
│   ├── tdd.md              # 技术设计文档
│   ├── test.md             # 测试文档
│   └── uat.md              # 用户验收文档
├── src/                     # 源代码目录
│   ├── services/           # 服务层
│   ├── utils/              # 工具类
│   ├── models.py           # 数据模型
│   ├── schemas.py          # 数据校验
│   ├── sdk.py              # SDK 核心类
│   └── server.py           # MCP 服务器
├── tests/                   # 测试目录
├── migrations/              # 数据库迁移
├── requirements.txt         # 依赖清单
├── pyproject.toml          # 项目配置
└── README.md                # 项目说明
```

## 开发指南

### 代码规范

- 使用 Python 3.10+ 类型注解
- 遵循 PEP 8 代码规范
- 使用 Pydantic 进行数据校验
- 使用 SQLAlchemy ORM 操作数据库

### 测试规范

- 单元测试覆盖率目标: 80%
- 使用 pytest 作为测试框架
- 每个功能模块必须有对应测试

### 提交规范

遵循 Conventional Commits 规范：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 代码重构

## 性能目标

| 操作 | 目标 |
|------|------|
| create_project | < 10ms |
| add_requirement | < 30ms |
| get_next_requirement | < 50ms |
| 拓扑排序 (2000 节点) | < 1s |
| 全量链化 (2000 节点) | < 2s |

## 文档

- [产品需求文档 (PRD)](docs/prd.md)
- [任务开发清单](docs/task.md)
- [技术设计文档 (TDD)](docs/tdd.md)
- [测试文档](docs/test.md)
- [用户验收文档 (UAT)](docs/uat.md)

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 LICENSE 文件

## 联系方式

- 项目链接: [https://github.com/your-repo/mcp-axon](https://github.com/your-repo/mcp-axon)
- 问题反馈: [Issues](https://github.com/your-repo/mcp-axon/issues)

---

**文档版本**: v1.0
**最后更新**: 2025-12-31
**项目状态**: 开发中