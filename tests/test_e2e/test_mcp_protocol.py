# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 协议端到端测试"""

import pytest
import time
from src.api.mcp_server import list_tools, execute_tool


@pytest.mark.asyncio
async def test_tc032_mcp_tool_registration():
    """TC-032: 测试 MCP 工具注册"""

    # Arrange & Act
    tools = await list_tools()

    # Assert
    tool_names = [tool.name for tool in tools]
    assert "create_project" in tool_names
    assert "add_requirement" in tool_names
    assert "get_next_requirement" in tool_names
    assert len(tool_names) >= 22


@pytest.mark.asyncio
async def test_tc033_mcp_tool_call():
    """TC-033: 测试 MCP 工具调用"""
    # Arrange & Act
    result = await execute_tool(
        "create_project",
        {"name": "测试项目", "description": "描述"}
    )

    # Assert
    assert result is not None
    assert "project_id" in result
    assert "next_action" in result


@pytest.mark.asyncio
async def test_mcp_tool_call_add_requirement():
    """测试 MCP 工具调用 - 添加需求"""
    # Arrange: 先创建项目
    project_result = await execute_tool(
        "create_project",
        {"name": "测试项目"}
    )
    project_id = project_result["project_id"]

    # Act
    result = await execute_tool(
        "add_requirement",
        {
            "project_id": project_id,
            "content": "测试需求"
        }
    )

    # Assert
    assert result is not None
    assert "requirement_id" in result


@pytest.mark.asyncio
async def test_mcp_tool_call_mark_as_leaf():
    """测试 MCP 工具调用 - 标记叶子节点"""
    # Arrange: 创建项目和需求
    project_result = await execute_tool(
        "create_project",
        {"name": "测试项目"}
    )
    project_id = project_result["project_id"]

    req_result = await execute_tool(
        "add_requirement",
        {
            "project_id": project_id,
            "content": "测试需求"
        }
    )
    req_id = req_result["requirement_id"]

    # Act
    result = await execute_tool(
        "mark_as_leaf",
        {"requirement_id": req_id}
    )

    # Assert
    assert result is not None
    assert "status" in result


@pytest.mark.asyncio
async def test_mcp_complete_workflow():
    """测试完整工作流：创建项目 → 添加需求 → 链化 → 执行"""
    # Step 1: 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "完整测试项目", "description": "测试完整流程"}
    )
    project_id = project["project_id"]

    # Step 2: 添加多个需求
    req1 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "需求1"}
    )
    req2 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "需求2"}
    )
    req3 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "需求3"}
    )

    # Step 3: 标记为叶子节点
    await execute_tool("mark_as_leaf", {"requirement_id": req1["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": req2["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": req3["requirement_id"]})

    # Step 4: 添加验证
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req1["requirement_id"],
            "test_cases": [{"name": "测试1"}]
        }
    )
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req2["requirement_id"],
            "test_cases": [{"name": "测试2"}]
        }
    )
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req3["requirement_id"],
            "test_cases": [{"name": "测试3"}]
        }
    )

    # Step 5: 触发链化
    chain_result = await execute_tool("trigger_chaining", {"project_id": project_id})
    assert chain_result["status"] == "completed"

    # Step 6: 获取项目状态
    state = await execute_tool("get_project_state", {"project_id": project_id})
    assert state["chained_requirements"] == 3

    # Step 7: 获取下一个需求
    next_req = await execute_tool("get_next_requirement", {"project_id": project_id})
    assert next_req["requirement_id"] is not None

    # Step 8: 标记完成
    await execute_tool(
        "mark_requirement_completed",
        {
            "project_id": project_id,
            "requirement_id": next_req["requirement_id"]
        }
    )

    # Assert
    assert "project_id" in project
    assert "requirement_id" in req1
    assert chain_result["status"] == "completed"


@pytest.mark.asyncio
async def test_mcp_error_handling():
    """测试错误处理"""
    # Test 1: 添加需求时项目不存在 - 应该抛出异常
    project = await execute_tool(
        "create_project",
        {"name": "测试项目"}
    )
    with pytest.raises(Exception):
        await execute_tool(
            "add_requirement",
            {"project_id": "nonexistent-id", "content": "测试"}
        )

    # Test 2: 获取不存在的项目 - 应该抛出异常
    with pytest.raises(Exception):
        await execute_tool(
            "get_project",
            {"project_id": "invalid-id-12345"}
        )

    # Test 3: 删除不存在的需求 - 应该抛出异常
    with pytest.raises(Exception):
        await execute_tool(
            "delete_requirement",
            {"requirement_id": "nonexistent-id"}
        )


@pytest.mark.asyncio
async def test_mcp_lock_mechanism():
    """测试锁机制"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "锁测试项目"}
    )
    project_id = project["project_id"]

    # 获取锁
    lock_result = await execute_tool(
        "acquire_lock",
        {
            "project_id": project_id,
            "session_id": "session-1"
        }
    )
    assert lock_result["success"] is True

    # 检查锁状态
    is_locked = await execute_tool("is_locked", {"project_id": project_id})
    assert is_locked["locked"] is True

    # 获取锁信息
    lock_info = await execute_tool("get_lock_info", {"project_id": project_id})
    assert lock_info["lock_info"] is not None
    assert lock_info["lock_info"]["locked_by"] == "session-1"

    # 尝试用相同会话再次获取锁（应该成功）
    lock_result2 = await execute_tool(
        "acquire_lock",
        {
            "project_id": project_id,
            "session_id": "session-1"
        }
    )
    assert lock_result2["success"] is True

    # 尝试用不同会话获取锁（应该失败）
    lock_result3 = await execute_tool(
        "acquire_lock",
        {
            "project_id": project_id,
            "session_id": "session-2"
        }
    )
    assert lock_result3["success"] is False

    # 释放锁
    release_result = await execute_tool(
        "release_lock",
        {
            "project_id": project_id,
            "session_id": "session-1"
        }
    )
    assert release_result["success"] is True

    # 验证锁已释放
    is_locked2 = await execute_tool("is_locked", {"project_id": project_id})
    assert is_locked2["locked"] is False


@pytest.mark.asyncio
async def test_mcp_dependency_management():
    """测试依赖关系管理"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "依赖测试项目"}
    )
    project_id = project["project_id"]

    # 创建有依赖关系的需求
    req_a = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "需求A"}
    )
    req_b = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "需求B"}
    )
    req_c = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "需求C"}
    )

    # 标记为叶子节点
    await execute_tool("mark_as_leaf", {"requirement_id": req_a["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": req_b["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": req_c["requirement_id"]})

    # 添加依赖：C 依赖于 A 和 B
    await execute_tool(
        "add_dependency",
        {
            "requirement_id": req_c["requirement_id"],
            "dependency_id": req_a["requirement_id"]
        }
    )
    await execute_tool(
        "add_dependency",
        {
            "requirement_id": req_c["requirement_id"],
            "dependency_id": req_b["requirement_id"]
        }
    )

    # 添加验证
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req_a["requirement_id"],
            "test_cases": [{"name": "测试A"}]
        }
    )
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req_b["requirement_id"],
            "test_cases": [{"name": "测试B"}]
        }
    )
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req_c["requirement_id"],
            "test_cases": [{"name": "测试C"}]
        }
    )

    # 触发链化
    chain_result = await execute_tool("trigger_chaining", {"project_id": project_id})
    assert chain_result["status"] == "completed"

    # 获取项目状态验证依赖关系
    state = await execute_tool("get_project_state", {"project_id": project_id})
    assert state["chained_requirements"] == 3


@pytest.mark.asyncio
async def test_mcp_update_operations():
    """测试更新操作"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "原始名称", "description": "原始描述"}
    )
    project_id = project["project_id"]

    # 更新项目
    updated_project = await execute_tool(
        "update_project",
        {
            "project_id": project_id,
            "name": "更新后的名称",
            "description": "更新后的描述"
        }
    )
    assert updated_project["name"] == "更新后的名称"

    # 添加需求
    req = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "原始需求内容"}
    )

    # 更新需求内容
    updated_req = await execute_tool(
        "update_requirement",
        {
            "requirement_id": req["requirement_id"],
            "content": "更新后的需求内容"
        }
    )
    assert updated_req["content"] == "更新后的需求内容"


@pytest.mark.asyncio
async def test_mcp_snapshot_management():
    """测试快照管理"""
    # 创建项目和需求
    project = await execute_tool(
        "create_project",
        {"name": "快照测试项目"}
    )
    project_id = project["project_id"]

    req = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "测试需求"}
    )

    # 创建快照
    snapshot_result = await execute_tool(
        "create_snapshot",
        {"project_id": project_id}
    )
    snapshot_id = snapshot_result["snapshot_id"]
    assert snapshot_id is not None

    # 列出快照
    snapshots = await execute_tool(
        "list_snapshots",
        {"project_id": project_id, "limit": 10}
    )
    assert len(snapshots["snapshots"]) >= 1
    assert snapshots["snapshots"][0]["snapshot_id"] == snapshot_id

    # 修改需求
    await execute_tool(
        "update_requirement",
        {
            "requirement_id": req["requirement_id"],
            "content": "修改后的内容"
        }
    )

    # 恢复快照
    restore_result = await execute_tool(
        "restore_snapshot",
        {"snapshot_id": snapshot_id}
    )
    assert restore_result["restored_count"] >= 0
    assert restore_result["message"] == "快照恢复成功"


@pytest.mark.asyncio
async def test_mcp_delete_operations():
    """测试删除操作"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "删除测试项目"}
    )
    project_id = project["project_id"]

    # 添加需求
    req = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "待删除的需求"}
    )
    req_id = req["requirement_id"]

    # 删除需求
    delete_result = await execute_tool(
        "delete_requirement",
        {"requirement_id": req_id}
    )
    assert delete_result["deleted"] is True


@pytest.mark.asyncio
async def test_mcp_transfer_dependencies():
    """测试依赖传递"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "依赖传递测试项目"}
    )
    project_id = project["project_id"]

    # 创建父需求
    parent = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "父需求"}
    )
    parent_id = parent["requirement_id"]

    # 创建子需求
    child1 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "子需求1", "parent_id": parent_id}
    )
    child2 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "子需求2", "parent_id": parent_id}
    )

    # 创建依赖需求
    dep1 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "依赖需求1"}
    )
    dep2 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "依赖需求2"}
    )

    # 标记为叶子节点
    await execute_tool("mark_as_leaf", {"requirement_id": dep1["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": dep2["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": child1["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": child2["requirement_id"]})

    # 添加验证
    await execute_tool(
        "add_validation",
        {
            "requirement_id": dep1["requirement_id"],
            "test_cases": [{"name": "测试"}]
        }
    )
    await execute_tool(
        "add_validation",
        {
            "requirement_id": dep2["requirement_id"],
            "test_cases": [{"name": "测试"}]
        }
    )

    # 传递依赖：子需求1依赖于依赖需求1，子需求2依赖于依赖需求2
    transfer_result = await execute_tool(
        "transfer_dependencies",
        {
            "parent_id": parent_id,
            "dependency_mapping": {
                child1["requirement_id"]: [dep1["requirement_id"]],
                child2["requirement_id"]: [dep2["requirement_id"]]
            }
        }
    )
    assert transfer_result["updated_children"]
    assert len(transfer_result["updated_children"]) == 2


@pytest.mark.asyncio
async def test_mcp_resolve_parallel_order():
    """测试并行节点排序"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "并行排序测试项目"}
    )
    project_id = project["project_id"]

    # 创建多个独立需求（并行节点）
    req1 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "并行需求1"}
    )
    req2 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "并行需求2"}
    )
    req3 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "并行需求3"}
    )

    # 标记为叶子节点
    await execute_tool("mark_as_leaf", {"requirement_id": req1["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": req2["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": req3["requirement_id"]})

    # 添加验证
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req1["requirement_id"],
            "test_cases": [{"name": "测试"}]
        }
    )
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req2["requirement_id"],
            "test_cases": [{"name": "测试"}]
        }
    )
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req3["requirement_id"],
            "test_cases": [{"name": "测试"}]
        }
    )

    # 触发链化
    chain_result = await execute_tool("trigger_chaining", {"project_id": project_id})

    # 如果检测到并行节点，需要解决排序
    if chain_result.get("parallel_nodes"):
        resolve_result = await execute_tool(
            "resolve_parallel_order",
            {
                "project_id": project_id,
                "parallel_nodes": chain_result["parallel_nodes"],
                "sorted_order": chain_result["parallel_nodes"]  # 使用默认顺序
            }
        )
        assert resolve_result["status"] == "completed"


@pytest.mark.asyncio
async def test_mcp_large_scale_project():
    """测试大规模项目"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "大规模测试项目"}
    )
    project_id = project["project_id"]

    # 创建根需求
    root = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "根需求"}
    )

    # 创建多个子需求
    child_count = 10
    child_ids = []
    for i in range(child_count):
        child = await execute_tool(
            "add_requirement",
            {
                "project_id": project_id,
                "content": f"子需求{i}",
                "parent_id": root["requirement_id"]
            }
        )
        child_ids.append(child["requirement_id"])

    # 标记所有子需求为叶子节点
    for child_id in child_ids:
        await execute_tool("mark_as_leaf", {"requirement_id": child_id})

    # 为所有子需求添加验证
    for child_id in child_ids:
        await execute_tool(
            "add_validation",
            {
                "requirement_id": child_id,
                "test_cases": [{"name": f"测试{i}"}]
            }
        )

    # 触发链化
    chain_result = await execute_tool("trigger_chaining", {"project_id": project_id})
    assert chain_result["status"] == "completed"

    # 获取项目状态
    state = await execute_tool("get_project_state", {"project_id": project_id})
    assert state["total_requirements"] == child_count + 1  # 根需求 + 子需求


@pytest.mark.asyncio
async def test_mcp_concurrent_lock_scenarios():
    """测试并发锁场景"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "并发锁测试项目"}
    )
    project_id = project["project_id"]

    # 会话1获取锁
    lock1 = await execute_tool(
        "acquire_lock",
        {
            "project_id": project_id,
            "session_id": "session-1"
        }
    )
    assert lock1["success"] is True

    # 会话2尝试获取锁（应该失败）
    lock2 = await execute_tool(
        "acquire_lock",
        {
            "project_id": project_id,
            "session_id": "session-2"
        }
    )
    assert lock2["success"] is False

    # 会话1释放锁
    release1 = await execute_tool(
        "release_lock",
        {
            "project_id": project_id,
            "session_id": "session-1"
        }
    )
    assert release1["success"] is True

    # 会话2现在可以获取锁
    lock3 = await execute_tool(
        "acquire_lock",
        {
            "project_id": project_id,
            "session_id": "session-2"
        }
    )
    assert lock3["success"] is True

    # 会话2释放锁
    release2 = await execute_tool(
        "release_lock",
        {
            "project_id": project_id,
            "session_id": "session-2"
        }
    )
    assert release2["success"] is True


@pytest.mark.asyncio
async def test_mcp_nested_requirements():
    """测试嵌套需求结构"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "嵌套需求测试项目"}
    )
    project_id = project["project_id"]

    # 创建多层嵌套需求
    level0 = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "第0层"}
    )

    level1 = await execute_tool(
        "add_requirement",
        {
            "project_id": project_id,
            "content": "第1层",
            "parent_id": level0["requirement_id"]
        }
    )

    level2 = await execute_tool(
        "add_requirement",
        {
            "project_id": project_id,
            "content": "第2层",
            "parent_id": level1["requirement_id"]
        }
    )

    level3 = await execute_tool(
        "add_requirement",
        {
            "project_id": project_id,
            "content": "第3层",
            "parent_id": level2["requirement_id"]
        }
    )

    # 标记最底层为叶子节点
    await execute_tool("mark_as_leaf", {"requirement_id": level3["requirement_id"]})

    # 添加验证
    await execute_tool(
        "add_validation",
        {
            "requirement_id": level3["requirement_id"],
            "test_cases": [{"name": "测试"}]
        }
    )

    # 获取项目状态验证层级
    state = await execute_tool("get_project_state", {"project_id": project_id})
    assert state["total_requirements"] == 4


@pytest.mark.asyncio
async def test_mcp_circular_dependency_prevention():
    """测试循环依赖预防"""
    # 创建项目
    project = await execute_tool(
        "create_project",
        {"name": "循环依赖测试项目"}
    )
    project_id = project["project_id"]

    # 创建需求
    req_a = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "需求A"}
    )
    req_b = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "需求B"}
    )
    req_c = await execute_tool(
        "add_requirement",
        {"project_id": project_id, "content": "需求C"}
    )

    # 标记为叶子节点
    await execute_tool("mark_as_leaf", {"requirement_id": req_a["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": req_b["requirement_id"]})
    await execute_tool("mark_as_leaf", {"requirement_id": req_c["requirement_id"]})

    # 添加验证
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req_a["requirement_id"],
            "test_cases": [{"name": "测试"}]
        }
    )
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req_b["requirement_id"],
            "test_cases": [{"name": "测试"}]
        }
    )
    await execute_tool(
        "add_validation",
        {
            "requirement_id": req_c["requirement_id"],
            "test_cases": [{"name": "测试"}]
        }
    )

    # 创建依赖链：A -> B -> C
    await execute_tool(
        "add_dependency",
        {
            "requirement_id": req_b["requirement_id"],
            "dependency_id": req_a["requirement_id"]
        }
    )
    await execute_tool(
        "add_dependency",
        {
            "requirement_id": req_c["requirement_id"],
            "dependency_id": req_b["requirement_id"]
        }
    )

    # 尝试创建循环依赖：C -> A（应该失败）
    with pytest.raises(Exception):
        await execute_tool(
            "add_dependency",
            {
                "requirement_id": req_a["requirement_id"],
                "dependency_id": req_c["requirement_id"]
            }
        )