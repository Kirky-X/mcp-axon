# 📖 用户指南

### MCP-Axon 需求链化系统完整使用指南

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

**MCP-Axon** 是一个基于 Model Context Protocol (MCP) 的智能需求链化管理系统，专门用于将复杂的需求分解为可执行的链式结构。

### 核心功能

| 功能 | 说明 |
|-----|------|
| 需求分解 | 智能分解复杂需求为可执行的子需求 |
| 依赖管理 | 自动检测和管理需求间的依赖关系 |
| 链化构建 | 基于依赖关系构建最优执行链 |
| 并行处理 | 识别并行需求，支持自定义执行顺序 |
| 快照回滚 | 支持项目状态快照和回滚功能 |

---

## 快速开始

### 系统要求

- **Python**: 3.12+
- **SQLite**: 3.35+
- **Git**: 2.x+

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/Kirky-X/mcp-axon.git
cd mcp-axon

# 使用 uv 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装项目
uv pip install -e .
```

### 验证安装

```python
from src.core.sdk import RequirementSDK

def main():
    sdk = RequirementSDK()
    
    # 创建测试项目
    project = sdk.create_project(
        name="测试项目",
        description="验证安装是否成功"
    )
    
    print(f"✅ MCP-Axon 安装成功!")
    print(f"项目 ID: {project['id']}")

if __name__ == "__main__":
    main()
```

---

## 核心概念

### 需求链化

将复杂需求按照依赖关系分解为可执行的线性链式结构。

```python
sdk = RequirementSDK()

# 添加需求并建立依赖关系
auth_req = sdk.add_requirement(project_id, "用户认证")
db_req = sdk.add_requirement(project_id, "数据库设计")
ui_req = sdk.add_requirement(project_id, "界面设计")

# 添加依赖关系（A 依赖 B 和 C）
sdk.add_dependency(ui_req["requirement_id"], auth_req["requirement_id"])
sdk.add_dependency(ui_req["requirement_id"], db_req["requirement_id"])

# 触发链化
chain_result = sdk.trigger_chaining(project_id)
```

### 叶子节点

不需要进一步分解的终端需求节点，可以直接添加验证和执行。

```python
req_id = sdk.add_requirement(project_id, "实现登录功能")

# 标记为叶子节点
sdk.mark_as_leaf(req_id["requirement_id"])

# 添加验证
sdk.add_validation(
    requirement_id=req_id["requirement_id"],
    test_cases=[{
        "name": "登录测试",
        "steps": ["输入用户名密码", "点击登录"],
        "expected_result": "登录成功"
    }],
    acceptance_criteria="用户能够成功登录系统"
)
```

### 并行处理

系统自动识别可以并行执行的需求节点。

```python
# 并行节点识别
parallel_nodes = sdk.get_parallel_requirements(project_id)

# 指定执行顺序
sdk.resolve_parallel_order(project_id, ["req1", "req2"])
```

---

## 基本使用

### 初始化

```python
from src.core.sdk import RequirementSDK

# 简单初始化
sdk = RequirementSDK()

# 指定数据库路径
sdk = RequirementSDK(db_path="my_requirements.db")
```

### CRUD 操作

| 操作 | 代码示例 |
|-----|---------|
| 创建项目 | `sdk.create_project(name="项目名", description="描述")` |
| 添加需求 | `sdk.add_requirement(project_id, content, parent_id=None)` |
| 更新需求 | `sdk.update_requirement(requirement_id, content=新内容)` |
| 删除需求 | `sdk.delete_requirement(requirement_id)` |
| 查询项目 | `sdk.get_project(project_id)` |

### 完整示例

```python
from src.core.sdk import RequirementSDK

def main():
    # 初始化 SDK
    sdk = RequirementSDK()
    
    # 创建项目
    project = sdk.create_project(
        name="电商平台",
        description="电商系统的需求管理"
    )
    project_id = project["id"]
    
    # 添加根需求
    user_mgmt = sdk.add_requirement(
        project_id=project_id,
        content="用户管理模块"
    )
    
    # 添加子需求
    auth = sdk.add_requirement(
        project_id=project_id,
        content="用户认证功能",
        parent_id=user_mgmt["requirement_id"]
    )
    
    profile = sdk.add_requirement(
        project_id=project_id,
        content="用户资料管理",
        parent_id=user_mgmt["requirement_id"]
    )
    
    # 标记为叶子节点
    sdk.mark_as_leaf(auth["requirement_id"])
    sdk.mark_as_leaf(profile["requirement_id"])
    
    # 添加验证
    sdk.add_validation(
        requirement_id=auth["requirement_id"],
        test_cases=[{
            "name": "登录测试",
            "steps": ["输入用户名密码", "点击登录"],
            "expected_result": "登录成功"
        }],
        acceptance_criteria="用户能够成功登录系统"
    )
    
    # 触发链化
    chain_result = sdk.trigger_chaining(project_id)
    
    # 获取下一个需求
    next_req = sdk.get_next_requirement(project_id)
    print(f"下一个待执行需求: {next_req}")

if __name__ == "__main__":
    main()
```

---

## 高级使用

### 依赖传递

当子需求需要继承父需求的依赖时使用。

```python
sdk.transfer_dependencies(
    project_id=project_id,
    dependency_mapping={
        "parent_req_id": ["child_req_id1", "child_req_id2"]
    }
)
```

### 并行排序

指定并行节点的执行顺序。

```python
sdk.resolve_parallel_order(
    project_id=project_id,
    ordered_ids=["req_id_1", "req_id_2", "req_id_3"]
)
```

### 快照管理

```python
# 创建快照
snapshot_id = sdk.create_snapshot(project_id, session_id="my_session")

# 列出快照
snapshots = sdk.list_snapshots(project_id)

# 恢复快照
sdk.restore_snapshot(snapshot_id, session_id="my_session")
```

### 并发控制

```python
# 获取锁
sdk.acquire_lock(project_id, session_id="my_session")

# 检查锁状态
is_locked = sdk.is_locked(project_id)

# 获取锁信息
lock_info = sdk.get_lock_info(project_id)

# 释放锁
sdk.release_lock(project_id, session_id="my_session")
```

---

## 最佳实践

### ✅ 推荐做法

```python
# 1. 使用 try-except 处理错误
try:
    sdk.create_project(name="项目")
except Exception as e:
    print(f"错误: {e}")

# 2. 使用会话 ID 进行并发控制
session_id = "user_session_123"
sdk.acquire_lock(project_id, session_id=session_id)
try:
    # 执行操作
    sdk.add_requirement(project_id, "新需求")
finally:
    sdk.release_lock(project_id, session_id=session_id)

# 3. 定期创建快照
sdk.create_snapshot(project_id, session_id="backup")
```

### ❌ 避免做法

```python
# ❌ 避免不使用会话 ID
sdk.add_requirement(project_id, "需求")  # 应该传入 session_id

# ❌ 避免在锁外修改数据
# 应该先 acquire_lock
```

---

## 故障排除

### 常见问题

| 问题 | 解决方案 |
|-----|---------|
| 数据库锁定 | 确保在使用后释放锁 |
| 依赖循环 | 检查需求间的依赖关系 |
| 性能问题 | 使用批量操作，减少数据库查询 |

### 获取帮助

- [查看 FAQ](FAQ.md)
- [创建 Issue](https://github.com/Kirky-X/mcp-axon/issues)
- [API 参考](API_REFERENCE.md)

---

**[API 参考](API_REFERENCE.md)** • **[FAQ](FAQ.md)** • **[架构设计](ARCHITECTURE.md)**
