# 📘 API 参考

### Axon 需求链化系统完整 API 文档

> **文档版本**: 与代码 v1.0.0 保持一致  
> **最后更新**: 2026-04-13  
> **工具数量**: 8 个 MCP 工具

---

## 📋 MCP 工具列表

Axon 提供了 8 个合并后的 MCP 工具来管理需求链化系统。

### 🏗️ 项目管理工具

| 工具名称         | 描述                          | 合并功能                                    |
| ---------------- | ----------------------------- | ------------------------------------------- |
| `manage_project` | 项目管理:创建、更新、查询项目 | create_project, update_project, get_project |

### 📝 需求管理工具

| 工具名称             | 描述                                            | 合并功能                                                                                                  |
| -------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `manage_requirement` | 需求管理:创建、更新、删除、标记叶子、查询、列表 | add_requirement, update_requirement, delete_requirement, mark_as_leaf, get_requirement, list_requirements |

### 🔗 依赖管理工具

| 工具名称            | 描述                        | 合并功能                              |
| ------------------- | --------------------------- | ------------------------------------- |
| `manage_dependency` | 依赖管理:添加依赖、传递依赖 | add_dependency, transfer_dependencies |

### ✅ 验证管理工具

| 工具名称            | 描述                        | 合并功能                       |
| ------------------- | --------------------------- | ------------------------------ |
| `manage_validation` | 验证管理:添加验证、执行验证 | add_validation, run_validation |

### ⛓️ 执行流程工具

| 工具名称           | 描述                                                  | 合并功能                                                                              |
| ------------------ | ----------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `manage_execution` | 执行流程:获取下一个需求、标记完成、查询状态、触发链化 | get_next_requirement, mark_requirement_completed, get_project_state, trigger_chaining |

### 💾 快照管理工具

| 工具名称          | 描述                          | 合并功能                                          |
| ----------------- | ----------------------------- | ------------------------------------------------- |
| `manage_snapshot` | 快照管理:创建、恢复、列出快照 | create_snapshot, restore_snapshot, list_snapshots |

### 🔒 锁管理工具

| 工具名称      | 描述                            | 合并功能                                             |
| ------------- | ------------------------------- | ---------------------------------------------------- |
| `manage_lock` | 锁管理:获取、释放、检查、查询锁 | acquire_lock, release_lock, is_locked, get_lock_info |

### 🔍 API 版本工具

| 工具名称          | 描述              | 用途     |
| ----------------- | ----------------- | -------- |
| `get_api_version` | 获取 API 版本信息 | 版本查询 |

---

## 🏗️ 项目管理 API

### manage_project

管理项目(创建、更新、查询)。通过 `action` 参数区分操作类型。

| 参数          | 类型   | 必填 | 描述                                                  |
| ------------- | ------ | ---- | ----------------------------------------------------- |
| `action`      | string | 是   | 操作类型: `get`(查询), `create`(创建), `update`(更新) |
| `project_id`  | string | 条件 | 项目 ID (get/update 时必填,create 时可选)             |
| `name`        | string | 条件 | 项目名称 (create 时必填)                              |
| `description` | string | 否   | 项目描述                                              |

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
    "status": "CREATED"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

注: 如果返回数据中包含 `next_action` 字段(如创建项目后可能返回 `"next_action": "manage_requirement"`)，该字段会被提升到响应顶层。

**查询项目:**

```json
{
  "action": "get",
  "project_id": "12345678-1234-1234-1234-123456789012"
}
```

**返回值示例(查询):**

```json
{
  "success": true,
  "data": {
    "project_id": "12345678-1234-1234-1234-123456789012",
    "name": "电商平台",
    "description": "电商系统需求管理",
    "status": "CREATED"
  },
  "timestamp": "2026-01-01T12:00:00Z"
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

**返回值示例(更新):**

```json
{
  "success": true,
  "data": {
    "project_id": "12345678-1234-1234-1234-123456789012",
    "name": "新项目名称",
    "description": "新项目描述",
    "status": "UPDATED"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

---

## 📝 需求管理 API

### manage_requirement

管理需求(创建、更新、删除、标记叶子、查询、列表)。通过 `action` 参数区分操作类型。

| 参数              | 类型    | 必填 | 描述                                                               |
| ----------------- | ------- | ---- | ------------------------------------------------------------------ |
| `action`          | string  | 是   | 操作类型: `get`, `create`, `update`, `delete`, `mark_leaf`, `list` |
| `project_id`      | string  | 条件 | 项目 ID (create/list 时必填)                                       |
| `requirement_id`  | string  | 条件 | 需求 ID (get/update/delete/mark_leaf 时必填)                       |
| `content`         | string  | 条件 | 需求内容 (create 时必填)                                           |
| `parent_id`       | string  | 否   | 父需求 ID (create 时可选)                                          |
| `order_in_parent` | integer | 否   | 在父需求中的顺序 (create 时)                                       |
| `status`          | string  | 否   | 新状态 (update 时可选)                                             |
| `is_leaf`         | boolean | 否   | 过滤条件:只返回叶子节点 (list 时可选)                              |

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
    "needs_decomposition": true
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

**标记为叶子节点:**

```json
{
  "action": "mark_leaf",
  "requirement_id": "87654321-4321-4321-4321-210987654321"
}
```

**返回值示例(标记叶子):**

```json
{
  "success": true,
  "data": {
    "requirement_id": "87654321-4321-4321-4321-210987654321",
    "is_leaf": true,
    "message": "已标记为叶子节点"
  },
  "timestamp": "2026-01-01T12:00:00Z"
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

**返回值示例(列表):**

```json
{
  "success": true,
  "data": {
    "requirements": [
      {
        "requirement_id": "req_uuid_1",
        "content": "需求1",
        "level": 1,
        "status": "DRAFT",
        "is_leaf": true
      }
    ],
    "count": 1
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

---

## 🔗 依赖管理 API

### manage_dependency

管理依赖关系(添加单个依赖或批量传递依赖)。通过参数类型自动区分操作。

| 参数                 | 类型   | 必填 | 描述                                                      |
| -------------------- | ------ | ---- | --------------------------------------------------------- |
| `requirement_id`     | string | 条件 | 需求 ID (添加单个依赖时必填)                              |
| `dependency_id`      | string | 条件 | 依赖的需求 ID (添加单个依赖时必填)                        |
| `parent_id`          | string | 条件 | 父需求 ID (批量传递依赖时必填)                            |
| `dependency_mapping` | object | 条件 | 依赖映射 (批量传递时使用),格式:`{子需求ID: [依赖ID列表]}` |

**添加单个依赖:**

```json
{
  "requirement_id": "req_a",
  "dependency_id": "req_b"
}
```

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "message": "依赖添加成功",
    "requirement_id": "req_a",
    "dependency_id": "req_b"
  },
  "timestamp": "2026-01-01T12:00:00Z"
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

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "message": "依赖传递成功",
    "transferred_count": 3
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

---

## ✅ 验证管理 API

### manage_validation

管理验证(添加验证或执行验证)。有 `execution_result` 表示执行验证,否则为添加验证。

| 参数                  | 类型   | 必填 | 描述                      |
| --------------------- | ------ | ---- | ------------------------- |
| `requirement_id`      | string | 是   | 需求 ID                   |
| `test_cases`          | array  | 否   | 测试用例列表 (添加验证时) |
| `acceptance_criteria` | string | 否   | 验收标准 (添加验证时)     |
| `execution_result`    | string | 条件 | 执行结果 (执行验证时必填) |

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

**返回值示例(添加验证):**

```json
{
  "success": true,
  "data": {
    "requirement_id": "req_uuid",
    "message": "验证添加成功"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

**执行验证示例:**

```json
{
  "requirement_id": "req_uuid",
  "execution_result": "所有测试用例通过，功能符合预期"
}
```

**返回值示例(执行验证):**

```json
{
  "success": true,
  "data": {
    "requirement_id": "req_uuid",
    "message": "验证执行成功",
    "execution_result": "所有测试用例通过，功能符合预期"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

---

## ⛓️ 执行流程 API

### manage_execution

管理执行流程(获取下一个需求、标记完成、查询状态、触发链化)。通过 `action` 参数区分操作。

| 参数             | 类型   | 必填 | 描述                                                                                       |
| ---------------- | ------ | ---- | ------------------------------------------------------------------------------------------ |
| `project_id`     | string | 是   | 项目 ID                                                                                    |
| `action`         | string | 是   | 操作类型: `next`(获取下一个), `complete`(标记完成), `state`(查询状态), `trigger`(触发链化) |
| `requirement_id` | string | 条件 | 需求 ID (complete 时必填)                                                                  |

**获取下一个需求:**

```json
{
  "project_id": "project_uuid",
  "action": "next"
}
```

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "requirement_id": "req_uuid",
    "content": "需求内容",
    "level": 1,
    "status": "DRAFT"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

注: 如果没有可执行的需求,可能返回 `"data": null` 或空结果。

**标记需求完成:**

```json
{
  "project_id": "project_uuid",
  "action": "complete",
  "requirement_id": "req_uuid"
}
```

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "requirement_id": "req_uuid",
    "status": "COMPLETED",
    "message": "需求标记完成成功"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

**查询项目状态:**

```json
{
  "project_id": "project_uuid",
  "action": "state"
}
```

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "project_id": "project_uuid",
    "total_requirements": 10,
    "completed_requirements": 5,
    "pending_requirements": 5,
    "status": "IN_PROGRESS"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

**触发链化:**

```json
{
  "project_id": "project_uuid",
  "action": "trigger"
}
```

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "message": "链化触发成功",
    "chained_count": 3
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

---

## 💾 快照管理 API

### manage_snapshot

管理快照(创建、恢复、列出快照)。通过 `action` 参数区分操作。

| 参数          | 类型    | 必填 | 描述                                                    |
| ------------- | ------- | ---- | ------------------------------------------------------- |
| `action`      | string  | 是   | 操作类型: `create`(创建), `restore`(恢复), `list`(列出) |
| `project_id`  | string  | 条件 | 项目 ID (create/list 时必填)                            |
| `snapshot_id` | string  | 条件 | 快照 ID (restore 时必填)                                |
| `limit`       | integer | 否   | 返回数量限制 (list 时可选,默认 10)                      |

**创建快照:**

```json
{
  "action": "create",
  "project_id": "project_uuid"
}
```

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "snapshot_id": "snapshot_uuid",
    "project_id": "project_uuid",
    "created_at": "2026-01-01T12:00:00Z",
    "message": "快照创建成功"
  },
  "timestamp": "2026-01-01T12:00:00Z"
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

**列出快照返回值示例:**

```json
{
  "success": true,
  "data": {
    "snapshots": [
      {
        "snapshot_id": "snapshot_uuid_1",
        "project_id": "project_uuid",
        "created_at": "2026-01-01T12:00:00Z"
      }
    ],
    "count": 1
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

---

## 🔒 锁管理 API

### manage_lock

管理锁(获取、释放、检查、查询锁信息)。通过 `action` 参数区分操作。

| 参数         | 类型   | 必填 | 描述                                                                                |
| ------------ | ------ | ---- | ----------------------------------------------------------------------------------- |
| `project_id` | string | 是   | 项目 ID                                                                             |
| `action`     | string | 是   | 操作类型: `acquire`(获取锁), `release`(释放锁), `check`(检查锁定), `info`(查询信息) |
| `session_id` | string | 条件 | 会话 ID (acquire/release 时必填)                                                    |

**获取锁:**

```json
{
  "project_id": "project_uuid",
  "action": "acquire",
  "session_id": "session_123"
}
```

**返回值示例(成功):**

```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "锁获取成功"
  },
  "timestamp": "2026-01-01T12:00:00Z"
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

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "locked": true,
    "message": "项目已被锁定"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

**查询锁信息:**

```json
{
  "project_id": "project_uuid",
  "action": "info"
}
```

**返回值示例:**

```json
{
  "success": true,
  "data": {
    "lock_info": {
      "session_id": "session_123",
      "acquired_at": "2026-01-01T12:00:00Z"
    },
    "message": "锁信息"
  },
  "timestamp": "2026-01-01T12:00:00Z"
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
    "supported_versions": ["1.0.0"],
    "min_supported_version": "1.0.0",
    "version_history": {
      "1.0.0": "初始版本，合并为8个核心接口"
    }
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

---

## 响应格式

### 成功响应

所有工具调用成功时返回统一的响应格式:

```json
{
  "success": true,
  "data": {
    // 工具返回的具体数据
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

如果返回数据中包含 `next_action` 字段，该字段会被提升到响应顶层:

```json
{
  "success": true,
  "data": {
    // 工具返回的具体数据
  },
  "next_action": "下一个建议的操作",
  "timestamp": "2026-01-01T12:00:00Z"
}
```

### 错误响应

## 错误处理

### 错误响应格式

所有工具调用失败时返回统一的错误响应格式:

```json
{
  "success": false,
  "error": "错误描述信息",
  "error_type": "错误类型"
}
```

### 错误类型说明

`error_type` 字段标识错误类型,可能的值包括:

| error_type | 描述 | 来源 |
| ---------- | ---- | ---- |
| `RateLimitExceeded` | 请求过于频繁 | 限流检查 |
| `ValidationError` | 参数验证错误或业务逻辑错误 | ValueError 异常 |
| 其他异常类名 | 内部服务器错误 | 其他 Exception 异常 |

### 安全错误消息

系统会对错误消息进行安全过滤,仅返回业务相关的错误信息,防止泄露内部实现细节。已知的业务错误前缀包括:

- 项目相关: "项目不存在", "项目已", "项目未"
- 需求相关: "需求不存在", "需求", "内容"
- 验证相关: "验证节点不存在"
- 依赖相关: "依赖"
- 锁相关: "锁"
- 快照相关: "快照"
- 操作相关: "创建", "更新", "删除", "链化"
- 参数相关: "参数", "无效", "格式"
- 权限相关: "无权"
- 其他: "无法", "不能", "必须", "找不到"

非业务错误统一返回: "操作失败,请稍后重试"

### 请求限流

当触发限流时返回:

```json
{
  "success": false,
  "error": "请求过于频繁,请稍后再试。当前限制: X 次/Y秒,剩余次数: Z",
  "error_type": "RateLimitExceeded"
}
```

### 参数验证错误

当参数不符合要求时返回:

```json
{
  "success": false,
  "error": "具体的参数错误描述",
  "error_type": "ValidationError"
}
```

**常见验证错误:**
- `action` 参数缺失或枚举值不匹配
- 条件必填参数未提供(如 create 时缺少 name)
- 资源不存在(如 project_id 或 requirement_id 无效)
- 状态不符合操作要求(如删除非叶子节点)
- 依赖关系冲突(如循环依赖)

---

**[用户指南](USER_GUIDE.md)** • **[架构设计](ARCHITECTURE.md)** • **[FAQ](FAQ.md)**
