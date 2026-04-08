# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""快照管理边界测试"""

from src.core.sdk import RequirementSDK


def test_snapshot_delete_requirements_after_snapshot():
    """测试快照恢复后删除快照后创建的需求"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    project_id = project["project_id"]

    # 创建初始需求
    req1 = sdk.add_requirement(project_id, "需求1")
    req2 = sdk.add_requirement(project_id, "需求2")
    sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])
    sdk.add_validation(req2["requirement_id"], [{"name": "测试2"}])

    # 创建快照
    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    # 在快照后创建新需求
    req3 = sdk.add_requirement(project_id, "需求3")
    req4 = sdk.add_requirement(project_id, "需求4")
    sdk.add_validation(req3["requirement_id"], [{"name": "测试3"}])
    sdk.add_validation(req4["requirement_id"], [{"name": "测试4"}])

    # 验证快照前有 4 个需求
    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 4

    # Act: 恢复快照
    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")

    # Assert
    assert result["restored_count"] > 0

    # 验证恢复后只有快照前的 2 个需求
    state_after = sdk.get_project_state(project_id)
    assert state_after["total_requirements"] == 2


def test_snapshot_with_nested_requirements():
    """测试包含嵌套需求的快照恢复"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    project_id = project["project_id"]

    # 创建嵌套需求
    parent = sdk.add_requirement(project_id, "父需求")
    child1 = sdk.add_requirement(
        project_id, "子需求1", parent_id=parent["requirement_id"]
    )
    child2 = sdk.add_requirement(
        project_id, "子需求2", parent_id=parent["requirement_id"]
    )
    sdk.add_validation(child1["requirement_id"], [{"name": "测试1"}])
    sdk.add_validation(child2["requirement_id"], [{"name": "测试2"}])

    # 创建快照
    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    # 在快照后添加更多子需求
    child3 = sdk.add_requirement(
        project_id, "子需求3", parent_id=parent["requirement_id"]
    )
    sdk.add_validation(child3["requirement_id"], [{"name": "测试3"}])

    # Act: 恢复快照
    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")

    # Assert
    assert result["restored_count"] > 0

    # 验证恢复后只有 3 个需求（父需求 + 2 个子需求）
    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 3


def test_snapshot_empty_project():
    """测试空项目的快照恢复"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("空项目")
    project_id = project["project_id"]

    # 创建空项目快照
    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    # 添加需求
    sdk.add_requirement(project_id, "需求1")

    # Act: 恢复快照
    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")

    # Assert - 空项目恢复后应该没有需求
    assert result["restored_count"] == 0 or result["deleted_count"] > 0

    # 验证恢复后项目为空
    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 0


def test_snapshot_multiple_restores():
    """测试多次恢复同一个快照"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    project_id = project["project_id"]

    # 创建需求
    req1 = sdk.add_requirement(project_id, "需求1")
    sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])

    # 创建快照
    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    # 第一次恢复
    result1 = sdk.restore_snapshot(snapshot_id, "test-session-123456789")
    assert result1["restored_count"] >= 0

    # 添加需求
    sdk.add_requirement(project_id, "需求2")

    # 第二次恢复（应该恢复到相同的快照状态）
    result2 = sdk.restore_snapshot(snapshot_id, "test-session-123456789")
    assert result2["restored_count"] >= 0

    # 验证两次恢复后的状态相同
    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 1


def test_snapshot_with_dependencies():
    """测试包含依赖关系的快照恢复"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    project_id = project["project_id"]

    # 创建父需求和子需求
    parent = sdk.add_requirement(project_id, "父需求")
    child1 = sdk.add_requirement(
        project_id, "子需求1", parent_id=parent["requirement_id"]
    )
    child2 = sdk.add_requirement(
        project_id, "子需求2", parent_id=parent["requirement_id"]
    )
    sdk.add_validation(child1["requirement_id"], [{"name": "测试1"}])
    sdk.add_validation(child2["requirement_id"], [{"name": "测试2"}])

    # 设置依赖关系（从父需求传递给子需求）
    sdk.transfer_dependencies(
        parent["requirement_id"],
        {child1["requirement_id"]: [], child2["requirement_id"]: []},
    )

    # 创建快照
    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    # 在快照后添加新需求
    child3 = sdk.add_requirement(
        project_id, "子需求3", parent_id=parent["requirement_id"]
    )
    sdk.add_validation(child3["requirement_id"], [{"name": "测试3"}])

    # Act: 恢复快照
    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")

    # Assert
    assert result["restored_count"] > 0

    # 验证恢复后只有 3 个需求（父需求 + 2 个子需求）
    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 3
