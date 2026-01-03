# 📘 API 参考

### MCP-Axon 需求链化系统完整 API 文档

---

## 📋 MCP 工具列表

MCP-Axon 提供了 22 个 MCP 工具来管理需求链化系统。

### 🏗️ 项目管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `create_project` | 创建新的需求链项目 | 初始化项目 |
| `update_project` | 更新项目信息 | 修改项目名称或描述 |
| `get_project` | 获取项目详细信息 | 查询项目状态 |

### 📝 需求管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `add_requirement` | 添加需求节点 | 创建新需求 |
| `update_requirement` | 更新需求内容或状态 | 修改现有需求 |
| `mark_as_leaf` | 标记需求为叶子节点 | 表示需求无需进一步分解 |
| `delete_requirement` | 删除需求节点 | 移除需求及其子节点 |
| `get_next_requirement` | 获取下一个待执行需求 | 链式执行导航 |
| `mark_requirement_completed` | 标记需求为已完成 | 推进执行进度 |

### 🔗 依赖管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `add_dependency` | 添加依赖关系 | 建立需求间依赖 |
| `transfer_dependencies` | 应用依赖传递映射 | 处理复杂依赖关系 |

### ✅ 验证管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `add_validation` | 为叶子节点添加验证 | 设置测试用例和验收标准 |

### ⛓️ 链化工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `trigger_chaining` | 手动触发链化 | 启动需求链化过程 |
| `resolve_parallel_order` | 指定并行节点执行顺序 | 处理并行需求执行 |
| `get_project_state` | 查询项目当前状态 | 获取进度和统计信息 |

### 💾 状态管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `create_snapshot` | 创建项目状态快照 | 保存当前状态 |
| `restore_snapshot` | 从快照恢复项目状态 | 回滚到之前状态 |
| `list_snapshots` | 列出项目的所有快照 | 查看快照历史 |

### 🔒 并发控制工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `acquire_lock` | 获取项目锁 | 防止并发修改 |
| `release_lock` | 释放项目锁 | 解除锁定 |
| `is_locked` | 检查项目是否被锁定 | 查询锁定状态 |
| `get_lock_info` | 获取项目锁的详细信息 | 查看锁的详细信息 |

---

## 🏗️ 项目管理 API

### create_project

创建一个新的需求链项目。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `name` | string | 是 | 项目名称 |
| `description` | string | 否 | 项目描述 |

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "id": "12345678-1234-1234-1234-123456789012",
    "name": "电商平台",
    "description": "电商系统需求管理",
    "status": "CREATED",
    "created_at": "2026-01-01T12:00:00Z",
    "next_action": "add_root_requirement"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

### update_project

更新项目的基本信息。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |
| `name` | string | 否 | 新项目名称 |
| `description` | string | 否 | 新项目描述 |

### get_project

获取项目的详细信息。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |

---

## 📝 需求管理 API

### add_requirement

添加需求节点到项目中。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |
| `content` | string | 是 | 需求内容 |
| `parent_id` | string | 否 | 父需求 ID |
| `order_in_parent` | integer | 否 | 在父需求中的顺序 |

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "requirement_id": "87654321-4321-4321-4321-210987654321",
    "content": "用户认证模块",
    "level": 0,
    "status": "DRAFT",
    "needs_decomposition": true,
    "next_action": "decompose_requirement"
  }
}
```

### mark_as_leaf

标记需求为叶子节点，表示该需求不需要进一步分解。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `requirement_id` | string | 是 | 需求 ID |

### add_validation

为叶子节点添加测试用例和验收标准。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `requirement_id` | string | 是 | 需求 ID（必须是叶子节点） |
| `test_cases` | array | 否 | 测试用例列表 |
| `acceptance_criteria` | string | 否 | 验收标准 |

**test_cases 格式:**

```json
[
  {
    "name": "登录测试",
    "steps": ["输入用户名密码", "点击登录"],
    "expected_result": "登录成功"
  }
]
```

---

## 🔗 依赖管理 API

### add_dependency

为需求添加依赖关系。系统会自动检测循环依赖。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `requirement_id` | string | 是 | 需求 ID |
| `dependency_id` | string | 是 | 依赖的需求 ID |

### transfer_dependencies

应用依赖传递映射。当父需求分解为多个子需求时，使用此工具指定每个子需求的依赖关系。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `parent_id` | string | 是 | 父需求 ID |
| `dependency_mapping` | object | 是 | 依赖映射，格式：`{子需求ID: [依赖ID列表]}` |

---

## ⛓️ 链化 API

### trigger_chaining

手动触发链化过程。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |

### get_next_requirement

获取下一个需要执行的需求。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |

### resolve_parallel_order

指定并行节点的执行顺序。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |
| `parallel_nodes` | array | 是 | 并行节点 ID 列表 |
| `sorted_order` | array | 是 | 排序后的节点 ID 列表 |

---

## 💾 状态管理 API

### create_snapshot

创建项目状态快照。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |

### restore_snapshot

从快照恢复项目状态。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `snapshot_id` | string | 是 | 快照 ID |

### list_snapshots

列出项目的所有快照。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |
| `limit` | integer | 否 | 返回数量限制（默认 10） |

---

## 🔒 并发控制 API

### acquire_lock

获取项目锁，防止并发修改冲突。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |
| `session_id` | string | 是 | 会话 ID |

### release_lock

释放项目锁。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |
| `session_id` | string | 是 | 会话 ID |

### is_locked

检查项目是否被锁定。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |

### get_lock_info

获取项目锁的详细信息。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |

---

## 错误处理

### 通用错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

### 常见错误码

| 错误码 | 描述 |
|-------|------|
| `PROJECT_NOT_FOUND` | 项目不存在 |
| `REQUIREMENT_NOT_FOUND` | 需求不存在 |
| `CYCLE_DETECTED` | 检测到循环依赖 |
| `LOCK_CONFLICT` | 锁获取冲突 |
| `INVALID_STATE` | 无效状态 |
| `VALIDATION_ERROR` | 参数验证失败 |

---

**[用户指南](USER_GUIDE.md)** • **[架构设计](ARCHITECTURE.md)** • **[FAQ](FAQ.md)**
