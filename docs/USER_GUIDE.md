# 📖 用户指南

### Axon 需求链化系统完整使用指南

---

## 📋 目录

- [简介](#简介)
- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [基本使用](#基本使用)
- [高级使用](#高级使用)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

---

## 简介

**Axon** 是一个基于 Model Context Protocol (MCP) 的智能需求链化管理系统，专门用于将复杂的需求分解为可执行的链式结构。

### 核心功能

| 功能     | 说明                             |
| -------- | -------------------------------- |
| 需求分解 | 智能分解复杂需求为可执行的子需求 |
| 依赖管理 | 自动检测和管理需求间的依赖关系   |
| 链化构建 | 基于依赖关系构建最优执行链       |
| 并行处理 | 识别并行需求，支持自定义执行顺序 |
| 快照回滚 | 支持项目状态快照和回滚功能       |

---

## 快速开始

### 系统要求

- **Python**: 3.12+
- **Git**: 2.x+

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/Kirky-X/axon.git
cd axon

# 使用 uv 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装项目
uv pip install -e .
```

### 环境变量配置

```bash
# 设置数据库路径 (可选,默认为 mcp_axon.lbug)
export MCP_AXON_DB_PATH="my_requirements.lbug"
```

> **注意**: 默认数据库路径为 `axon.db`,可以通过环境变量 `MCP_AXON_DB_PATH` 自定义。
> 可通过环境变量 `MCP_AXON_DB_PATH` 统一覆盖。

### 验证安装

使用 CLI 验证安装:

```bash
# 显示版本信息
axon version

# 创建测试项目
axon project create --name "测试项目" --desc "验证安装是否成功"
```

---

## 核心概念

### 需求链化

将复杂需求按照依赖关系分解为可执行的线性链式结构。

**CLI 方式:**

```bash
# 添加需求
axon requirement create --project <project_id> --content "用户认证"
axon requirement create --project <project_id> --content "数据库设计"
axon requirement create --project <project_id> --content "界面设计"

# 添加依赖关系
axon dependency add <ui_req_id> <auth_req_id>
axon dependency add <ui_req_id> <db_req_id>

# 注意: CLI 没有 trigger 子命令,链化触发需通过 MCP 工具或 SDK
# 使用 MCP 工具: manage_execution(action="trigger")
# 或使用 SDK: sdk.trigger_chaining(project_id, session_id)
```

**MCP 方式:**

通过 MCP 工具 `manage_requirement` 和 `manage_dependency` 实现相同功能。

### 叶子节点

不需要进一步分解的终端需求节点，可以直接添加验证和执行。

**CLI 方式:**

```bash
# 创建需求
req_id=$(axon requirement create --project <project_id> --content "实现登录功能")

# 标记为叶子节点
axon requirement mark-leaf <req_id>

# 添加验证
axon validation add <req_id> --tests '[{"name": "登录测试", "steps": ["输入用户名密码", "点击登录"], "expected_result": "登录成功"}]'
```

**MCP 方式:**

通过 `manage_requirement` (mark_leaf) 和 `manage_validation` 工具实现。

### 并行处理

系统自动识别可以并行执行的需求节点。

**CLI 方式:**

```bash
# 链化触发后查看可执行需求 (使用 MCP 工具或 SDK 触发链化)
axon execution next --project <project_id>
```

**MCP 方式:**

通过 `manage_execution` 工具的 `next` 动作获取下一个需求。

**SDK 方式:**

```python
from src.core.sdk import RequirementSDK

sdk = RequirementSDK()
# 触发链化
result = sdk.trigger_chaining(project_id, session_id)
# 获取下一个需求
next_req = sdk.get_next_requirement(project_id, session_id)
```

---

## 基本使用

### 初始化

配置数据库路径 (可选):

```bash
# 通过环境变量设置
export MCP_AXON_DB_PATH="my_requirements.lbug"
```

### CRUD 操作

#### CLI 方式

| 操作     | 命令                                                          |
| -------- | ------------------------------------------------------------- |
| 创建项目 | `axon project create --name "项目名" --desc "描述"`           |
| 查询项目 | `axon project get <project_id>`                               |
| 更新项目 | `axon project update <project_id> --name "新名称"`            |
| 创建需求 | `axon requirement create --project <id> --content "内容"`     |
| 查询需求 | `axon requirement get <requirement_id>`                       |
| 更新需求 | `axon requirement update <requirement_id> --content "新内容"` |
| 删除需求 | `axon requirement delete <requirement_id>`                    |
| 标记叶子 | `axon requirement mark-leaf <requirement_id>`                 |
| 列出需求 | `axon requirement list --project <project_id>`                |
| 添加依赖 | `axon dependency add <requirement_id> <dependency_id>`        |
| 传递依赖 | `axon dependency transfer <parent_id> --mapping 'JSON'`       |
| 添加验证 | `axon validation add <requirement_id> --tests 'JSON'`         |
| 运行验证 | `axon validation run <requirement_id>`                        |
| 下一步   | `axon execution next --project <project_id>`                  |
| 标记完成 | `axon execution complete <requirement_id> --project <id>`     |
| 执行状态 | `axon execution state --project <project_id>`                 |
| 创建快照 | `axon snapshot create --project <project_id>`                 |
| 列出快照 | `axon snapshot list --project <project_id>`                   |
| 恢复快照 | `axon snapshot restore <snapshot_id>`                         |
| 获取锁   | `axon lock acquire --project <project_id> --session <id>`     |
| 释放锁   | `axon lock release --project <project_id> --session <id>`     |
| 检查锁   | `axon lock check --project <project_id>`                      |
| 查看版本 | `axon version`                                                |

#### MCP 方式

| 操作     | 工具                                                                   |
| -------- | ---------------------------------------------------------------------- |
| 项目管理 | `manage_project` (action: create/get/update)                           |
| 需求管理 | `manage_requirement` (action: create/get/update/delete/mark_leaf/list) |
| 依赖管理 | `manage_dependency`                                                    |
| 验证管理 | `manage_validation`                                                    |
| 执行流程 | `manage_execution` (action: next/complete/state/trigger)               |
| 快照管理 | `manage_snapshot` (action: create/restore/list)                        |
| 锁管理   | `manage_lock` (action: acquire/release/check/info)                     |

### 完整示例

#### CLI 完整流程

```bash
# 1. 创建项目
axon project create --name "电商平台" --desc "电商系统的需求管理"
# 记录返回的 project_id

# 2. 添加根需求
axon requirement create --project <project_id> --content "用户管理模块"
# 记录返回的 requirement_id

# 3. 添加子需求
axon requirement create --project <project_id> --content "用户认证功能" --parent <user_mgmt_id>
axon requirement create --project <project_id> --content "用户资料管理" --parent <user_mgmt_id>

# 4. 标记为叶子节点
axon requirement mark-leaf <auth_id>
axon requirement mark-leaf <profile_id>

# 5. 添加验证
axon validation add <auth_id> --tests '[{"name": "登录测试", "steps": ["输入用户名密码", "点击登录"], "expected_result": "登录成功"}]'

# 6. 触发链化 (通过 MCP 工具或 SDK,CLI 无此命令)
# MCP 方式: 调用 manage_execution 工具,action="trigger"
# SDK 方式: sdk.trigger_chaining(project_id, session_id)

# 7. 获取下一个需求
axon execution next --project <project_id>
```

#### MCP 完整流程

通过 MCP 客户端调用相应的工具，参考 [API 参考](API_REFERENCE.md)。

---

## 高级使用

### 依赖传递

当子需求需要继承父需求的依赖时使用。

**CLI 方式:**

```bash
axon dependency transfer <parent_id> --mapping '{"child1": ["dep1"], "child2": ["dep2"]}'
```

**MCP 方式:**

使用 `manage_dependency` 工具，传入 `parent_id` 和 `dependency_mapping` 参数。

### 并行排序

指定并行节点的执行顺序。

```python
sdk.resolve_parallel_order(
    project_id=project_id,
    parallel_nodes=["req_id_1", "req_id_2", "req_id_3"],
    sorted_order=["req_id_1", "req_id_2", "req_id_3"]
)
```

### 快照管理

**CLI 方式:**

```bash
# 创建快照
axon snapshot create --project <project_id>

# 列出快照
axon snapshot list --project <project_id>

# 恢复快照
axon snapshot restore <snapshot_id>
```

**MCP 方式:**

使用 `manage_snapshot` 工具 (action: create/list/restore)。

### 并发控制

**CLI 方式:**

```bash
# 获取锁
axon lock acquire --project <project_id> --session <session_id>

# 检查锁状态
axon lock check --project <project_id>

# 查询锁信息
axon lock info --project <project_id>

# 释放锁
axon lock release --project <project_id> --session <session_id>
```

**MCP 方式:**

使用 `manage_lock` 工具 (action: acquire/release/check/info)。

---

## 最佳实践

### ✅ 推荐做法

#### CLI 最佳实践

```bash
# 1. 使用环境变量配置数据库
export MCP_AXON_DB_PATH="/path/to/your/db.lbug"

# 2. 使用会话 ID 进行并发控制
axon lock acquire --project <project_id> --session <session_id>
try
    # 执行操作
    axon requirement create --project <project_id> --content "新需求"
finally
    axon lock release --project <project_id> --session <session_id>

# 3. 定期创建快照
axon snapshot create --project <project_id>
```

#### MCP 最佳实践

```json
// 1. 使用 MCP 客户端的会话管理
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

// 2. 批量操作减少调用次数
// 3. 定期检查项目状态
```

#### HTTP 最佳实践

```bash
# 1. 启动 HTTP 服务器
axon-server --mode http --http-port 8080

# 2. 使用健康检查
curl http://localhost:8080/health

# 3. 查看服务信息
curl http://localhost:8080/

# 4. 查看性能指标
curl http://localhost:8080/metrics

# 5. 查看 API 版本
curl http://localhost:8080/api_version
```

> **可用端点**: `/`, `/health`, `/metrics`, `/api_version`

### ❌ 避免做法

```bash
# ❌ 避免不使用锁直接修改
axon requirement create --project <project_id> --content "需求"  # 应该先获取锁

# ❌ 避免并发操作不加锁
# 应该先 axon lock acquire

# ❌ 避免忘记释放锁
# 应该在 finally 块中释放
```

---

## 故障排除

### 常见问题

| 问题       | 解决方案                                    |
| ---------- | ------------------------------------------- |
| 数据库锁定 | 确保在使用后释放锁: `axon lock release`     |
| 依赖循环   | 检查需求间的依赖关系,避免循环依赖           |
| 性能问题   | 使用批量操作,减少数据库查询                 |
| 请求限流   | 等待一段时间后重试,或调整限流配置           |

### CLI 常见问题

```bash
# Q: 如何查看可用命令?
axon --help
axon project --help

# Q: 如何查看版本?
axon version

# Q: 数据库文件在哪里?
# CLI 默认: axon.db
# 默认: axon.db
# 可通过环境变量 MCP_AXON_DB_PATH 覆盖
```

### MCP 常见问题

- **工具调用失败**: 检查参数是否完整，参考 [API 参考](API_REFERENCE.md)
- **限流错误**: 等待 `RateLimitExceeded` 错误中提示的时间后重试
- **会话过期**: 重新连接 MCP 客户端

### HTTP 常见问题

```bash
# Q: 如何启动 HTTP 服务器?
axon-server --mode http --http-port 8080

# Q: 如何检查服务状态?
curl http://localhost:8080/health

# Q: 如何查看服务信息?
curl http://localhost:8080/

# Q: 如何查看性能指标?
curl http://localhost:8080/metrics

# Q: 可用端点有哪些?
# /, /health, /metrics, /api_version
```

### 获取帮助

- [查看 FAQ](FAQ.md)
- [创建 Issue](https://github.com/Kirky-X/axon/issues)
- [API 参考](API_REFERENCE.md)

---

**[API 参考](API_REFERENCE.md)** • **[FAQ](FAQ.md)** • **[架构设计](ARCHITECTURE.md)**
