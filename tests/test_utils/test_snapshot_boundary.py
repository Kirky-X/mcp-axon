# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""快照管理边界测试"""

from src.core.sdk import RequirementSDK


def test_snapshot_delete_requirements_after_snapshot():
    """测试快照恢复后删除快照后创建的需求"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="测试项目")
    project_id = project["project_id"]

    req1 = sdk.manage_requirement(project_id=project_id, content="需求1")
    req2 = sdk.manage_requirement(project_id=project_id, content="需求2")
    sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])
    sdk.add_validation(req2["requirement_id"], [{"name": "测试2"}])

    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    req3 = sdk.manage_requirement(project_id=project_id, content="需求3")
    req4 = sdk.manage_requirement(project_id=project_id, content="需求4")
    sdk.add_validation(req3["requirement_id"], [{"name": "测试3"}])
    sdk.add_validation(req4["requirement_id"], [{"name": "测试4"}])

    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 4

    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")
    assert result["restored_count"] > 0

    state_after = sdk.get_project_state(project_id)
    assert state_after["total_requirements"] == 2


def test_snapshot_with_nested_requirements():
    """测试包含嵌套需求的快照恢复"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="测试项目")
    project_id = project["project_id"]

    parent = sdk.manage_requirement(project_id=project_id, content="父需求")
    child1 = sdk.manage_requirement(
        project_id=project_id, content="子需求1", parent_id=parent["requirement_id"]
    )
    child2 = sdk.manage_requirement(
        project_id=project_id, content="子需求2", parent_id=parent["requirement_id"]
    )
    sdk.add_validation(child1["requirement_id"], [{"name": "测试1"}])
    sdk.add_validation(child2["requirement_id"], [{"name": "测试2"}])

    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    child3 = sdk.manage_requirement(
        project_id=project_id, content="子需求3", parent_id=parent["requirement_id"]
    )
    sdk.add_validation(child3["requirement_id"], [{"name": "测试3"}])

    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")
    assert result["restored_count"] > 0

    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 3


def test_snapshot_empty_project():
    """测试空项目的快照恢复"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="空项目")
    project_id = project["project_id"]

    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    sdk.manage_requirement(project_id=project_id, content="需求1")

    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")

    assert result["restored_count"] == 0 or result.get("deleted_count", 0) > 0

    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 0


def test_snapshot_multiple_restores():
    """测试多次恢复同一个快照"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="测试项目")
    project_id = project["project_id"]

    req1 = sdk.manage_requirement(project_id=project_id, content="需求1")
    sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])

    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    result1 = sdk.restore_snapshot(snapshot_id, "test-session-123456789")
    assert result1["restored_count"] >= 0

    sdk.manage_requirement(project_id=project_id, content="需求2")

    result2 = sdk.restore_snapshot(snapshot_id, "test-session-123456789")
    assert result2["restored_count"] >= 0

    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 1


def test_snapshot_with_dependencies():
    """测试包含依赖关系的快照恢复"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="测试项目")
    project_id = project["project_id"]

    parent = sdk.manage_requirement(project_id=project_id, content="父需求")
    child1 = sdk.manage_requirement(
        project_id=project_id, content="子需求1", parent_id=parent["requirement_id"]
    )
    child2 = sdk.manage_requirement(
        project_id=project_id, content="子需求2", parent_id=parent["requirement_id"]
    )
    sdk.add_validation(child1["requirement_id"], [{"name": "测试1"}])
    sdk.add_validation(child2["requirement_id"], [{"name": "测试2"}])

    sdk.transfer_dependencies(
        parent["requirement_id"],
        {child1["requirement_id"]: [], child2["requirement_id"]: []},
    )

    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    child3 = sdk.manage_requirement(
        project_id=project_id, content="子需求3", parent_id=parent["requirement_id"]
    )
    sdk.add_validation(child3["requirement_id"], [{"name": "测试3"}])

    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")
    assert result["restored_count"] > 0

    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 3
