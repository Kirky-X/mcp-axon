# 📘 API 参考

### MCP-Axon 需求链化系统完整 API 文档

---

## 📋 MCP 工具列表

MCP-Axon 提供了 8 个合并后的 MCP 工具来管理需求链化系统。

### 🏗️ 项目管理工具

| 工具名称 | 描述 | 合并功能 |
|----------|------|----------|
| `manage_project` | 项目管理:创建、更新、查询项目 | create_project, update_project, get_project |

### 📝 需求管理工具

| 工具名称 | 描述 | 合并功能 |
|----------|------|----------|
| `manage_requirement` | 需求管理:创建、更新、删除、标记叶子、查询、列表 | add_requirement, update_requirement, delete_requirement, mark_as_leaf, get_requirement, list_requirements |

### 🔗 依赖管理工具

| 工具名称 | 描述 | 合并功能 |
|----------|------|----------|
| `manage_dependency` | 依赖管理:添加依赖、传递依赖 | add_dependency, transfer_dependencies |

### ✅ 验证管理工具

| 工具名称 | 描述 | 合并功能 |
|----------|------|----------|
| `manage_validation` | 验证管理:添加验证、执行验证 | add_validation, run_validation |

### ⛓️ 执行流程工具

| 工具名称 | 描述 | 合并功能 |
|----------|------|----------|
| `manage_execution` | 执行流程:获取下一个需求、标记完成、查询状态、触发链化 | get_next_requirement, mark_requirement_completed, get_project_state, trigger_chaining |

### 💾 快照管理工具

| 工具名称 | 描述 | 合并功能 |
|----------|------|----------|
| `manage_snapshot` | 快照管理:创建、恢复、列出快照 | create_snapshot, restore_snapshot, list_snapshots |

### 🔒 锁管理工具

| 工具名称 | 描述 | 合并功能 |
|----------|------|----------|
| `manage_lock` | 锁管理:获取、释放、检查、查询锁 | acquire_lock, release_lock, is_locked, get_lock_info |

### 🔍 API 版本工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `get_api_version` | 获取 API 版本信息 | 版本查询 |

---

## 🏗️ 项目管理 API

### manage_project

管理项目(创建、更新、查询)。通过 `action` 参数区分操作类型。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `action` | string | 是 | 操作类型: `get`(查询), `create`(创建), `update`(更新) |
| `project_id` | string | 条件 | 项目 ID (get/update 时必填,create 时可选) |
| `name` | string | 条件 | 项目名称 (create 时必填) |
| `description` | string | 否 | 项目描述 |

**创建项目示例:**

```json
{
  "action": "create",
  "name": "电商平台",
  "description": "电商系统需求管理"
}
```

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "project_id": "12345678-1234-1234-1234-123456789012",
    "name": "电商平台",
    "description": "电商系统需求管理",
    "status": "CREATED",
    "created_at": "2026-01-01T12:00:00Z",
    "next_action": "manage_requirement"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

**查询项目:**

```json
{
  "action": "get",
  "project_id": "12345678-1234-1234-1234-123456789012"
}
```

**更新项目:**

```json
{
  "action": "update",
  "project_id": "12345678-1234-1234-1234-123456789012",
  "name": "新项目名称",
  "description": "新项目描述"
}
```

---

## 📝 需求管理 API

### manage_requirement

管理需求(创建、更新、删除、标记叶子、查询、列表)。通过 `action` 参数区分操作类型。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `action` | string | 是 | 操作类型: `get`, `create`, `update`, `delete`, `mark_leaf`, `list` |
| `project_id` | string | 条件 | 项目 ID (create/list 时必填) |
| `requirement_id` | string | 条件 | 需求 ID (get/update/delete/mark_leaf 时必填) |
| `content` | string | 条件 | 需求内容 (create 时必填) |
| `parent_id` | string | 否 | 父需求 ID (create 时可选) |
| `order_in_parent` | integer | 否 | 在父需求中的顺序 (create 时) |
| `status` | string | 否 | 新状态 (update 时可选) |
| `is_leaf` | boolean | 否 | 过滤条件:只返回叶子节点 (list 时可选) |

**创建需求示例:**

```json
{
  "action": "create",
  "project_id": "project_uuid",
  "content": "用户认证模块",
  "parent_id": null,
  "order_in_parent": 0
}
```

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

**标记为叶子节点:**

```json
{
  "action": "mark_leaf",
  "requirement_id": "87654321-4321-4321-4321-210987654321"
}
```

**列出需求:**

```json
{
  "action": "list",
  "project_id": "project_uuid",
  "status": "DRAFT",
  "is_leaf": true
}
```

---

## 🔗 依赖管理 API

### manage_dependency

管理依赖关系(添加单个依赖或批量传递依赖)。通过参数类型自动区分操作。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `requirement_id` | string | 条件 | 需求 ID (添加单个依赖时必填) |
| `dependency_id` | string | 条件 | 依赖的需求 ID (添加单个依赖时必填) |
| `parent_id` | string | 条件 | 父需求 ID (批量传递依赖时必填) |
| `dependency_mapping` | object | 条件 | 依赖映射 (批量传递时使用),格式:`{子需求ID: [依赖ID列表]}` |

**添加单个依赖:**

```json
{
  "requirement_id": "req_a",
  "dependency_id": "req_b"
}
```

**批量传递依赖:**

```json
{
  "parent_id": "parent_req",
  "dependency_mapping": {
    "child_req_1": ["dep_1", "dep_2"],
    "child_req_2": ["dep_3"]
  }
}
```

---

## ✅ 验证管理 API

### manage_validation

管理验证(添加验证或执行验证)。有 `execution_result` 表示执行验证,否则为添加验证。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `requirement_id` | string | 是 | 需求 ID (必须是叶子节点) |
| `test_cases` | array | 否 | 测试用例列表 (添加验证时) |
| `acceptance_criteria` | string | 否 | 验收标准 (添加验证时) |
| `execution_result` | string | 条件 | 执行结果 (执行验证时必填) |

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

**添加验证示例:**

```json
{
  "requirement_id": "req_uuid",
  "test_cases": [
    {
      "name": "登录测试",
      "steps": ["输入用户名密码", "点击登录"],
      "expected_result": "登录成功"
    }
  ],
  "acceptance_criteria": "用户能够成功登录系统"
}
```

---

## ⛓️ 执行流程 API

### manage_execution

管理执行流程(获取下一个需求、标记完成、查询状态、触发链化)。通过 `action` 参数区分操作。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |
| `action` | string | 是 | 操作类型: `next`(获取下一个), `complete`(标记完成), `state`(查询状态), `trigger`(触发链化) |
| `requirement_id` | string | 条件 | 需求 ID (complete 时必填) |

**获取下一个需求:**

```json
{
  "project_id": "project_uuid",
  "action": "next"
}
```

**标记需求完成:**

```json
{
  "project_id": "project_uuid",
  "action": "complete",
  "requirement_id": "req_uuid"
}
```

**查询项目状态:**

```json
{
  "project_id": "project_uuid",
  "action": "state"
}
```

**触发链化:**

```json
{
  "project_id": "project_uuid",
  "action": "trigger"
}
```

---

## 💾 快照管理 API

### manage_snapshot

管理快照(创建、恢复、列出快照)。通过 `action` 参数区分操作。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `action` | string | 是 | 操作类型: `create`(创建), `restore`(恢复), `list`(列出) |
| `project_id` | string | 条件 | 项目 ID (create/list 时必填) |
| `snapshot_id` | string | 条件 | 快照 ID (restore 时必填) |
| `limit` | integer | 否 | 返回数量限制 (list 时可选,默认 10) |

**创建快照:**

```json
{
  "action": "create",
  "project_id": "project_uuid"
}
```

**恢复快照:**

```json
{
  "action": "restore",
  "snapshot_id": "snapshot_uuid"
}
```

**列出快照:**

```json
{
  "action": "list",
  "project_id": "project_uuid",
  "limit": 10
}
```

---

## 🔒 锁管理 API

### manage_lock

管理锁(获取、释放、检查、查询锁信息)。通过 `action` 参数区分操作。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| `project_id` | string | 是 | 项目 ID |
| `action` | string | 是 | 操作类型: `acquire`(获取锁), `release`(释放锁), `check`(检查锁定), `info`(查询信息) |
| `session_id` | string | 条件 | 会话 ID (acquire/release 时必填) |

**获取锁:**

```json
{
  "project_id": "project_uuid",
  "action": "acquire",
  "session_id": "session_123"
}
```

**释放锁:**

```json
{
  "project_id": "project_uuid",
  "action": "release",
  "session_id": "session_123"
}
```

**检查锁定状态:**

```json
{
  "project_id": "project_uuid",
  "action": "check"
}
```

**查询锁信息:**

```json
{
  "project_id": "project_uuid",
  "action": "info"
}
```

---

## 🔍 API 版本 API

### get_api_version

获取 API 版本信息。

**参数:** 无

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "current_version": "1.0.0",
    "supported_versions": ["1.0.0"]
  }
}
```

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
| `RateLimitExceeded` | 请求限流 |

---

**[用户指南](USER_GUIDE.md)** • **[架构设计](ARCHITECTURE.md)** • **[FAQ](FAQ.md)**
