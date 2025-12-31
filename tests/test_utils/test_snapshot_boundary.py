# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""快照管理边界测试"""

import pytest
from src.core.sdk import RequirementSDK
from src.db.database import get_session
from src.db.models import Requirement


def test_snapshot_delete_requirements_after_snapshot():
    """测试快照恢复后删除快照后创建的需求"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建初始需求
    req1 = sdk.add_requirement(project["project_id"], "需求1")
    req2 = sdk.add_requirement(project["project_id"], "需求2")
    sdk.mark_as_leaf(req1["requirement_id"])
    sdk.mark_as_leaf(req2["requirement_id"])
    sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])
    sdk.add_validation(req2["requirement_id"], [{"name": "测试2"}])

    # 创建快照
    snapshot_id = sdk.create_snapshot(project["project_id"])

    # 在快照后创建新需求
    req3 = sdk.add_requirement(project["project_id"], "需求3")
    req4 = sdk.add_requirement(project["project_id"], "需求4")
    sdk.mark_as_leaf(req3["requirement_id"])
    sdk.mark_as_leaf(req4["requirement_id"])
    sdk.add_validation(req3["requirement_id"], [{"name": "测试3"}])
    sdk.add_validation(req4["requirement_id"], [{"name": "测试4"}])

    # 验证快照前有 4 个需求
    with get_session() as session:
        reqs_before = session.query(Requirement).filter_by(
            project_id=project["project_id"]
        ).all()
        assert len(reqs_before) == 4

    # Act: 恢复快照
    result = sdk.restore_snapshot(snapshot_id)

    # Assert
    assert result["restored_count"] > 0

    # 验证恢复后只有快照前的 2 个需求
    with get_session() as session:
        reqs_after = session.query(Requirement).filter_by(
            project_id=project["project_id"]
        ).all()
        assert len(reqs_after) == 2

        # 验证需求 ID 是快照前的
        req_ids_after = {req.id for req in reqs_after}
        assert req1["requirement_id"] in req_ids_after
        assert req2["requirement_id"] in req_ids_after
        assert req3["requirement_id"] not in req_ids_after
        assert req4["requirement_id"] not in req_ids_after


def test_snapshot_with_nested_requirements():
    """测试包含嵌套需求的快照恢复"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建嵌套需求
    parent = sdk.add_requirement(project["project_id"], "父需求")
    child1 = sdk.add_requirement(
        project["project_id"],
        "子需求1",
        parent_id=parent["requirement_id"]
    )
    child2 = sdk.add_requirement(
        project["project_id"],
        "子需求2",
        parent_id=parent["requirement_id"]
    )
    sdk.mark_as_leaf(child1["requirement_id"])
    sdk.mark_as_leaf(child2["requirement_id"])
    sdk.add_validation(child1["requirement_id"], [{"name": "测试1"}])
    sdk.add_validation(child2["requirement_id"], [{"name": "测试2"}])

    # 创建快照
    snapshot_id = sdk.create_snapshot(project["project_id"])

    # 在快照后添加更多子需求
    child3 = sdk.add_requirement(
        project["project_id"],
        "子需求3",
        parent_id=parent["requirement_id"]
    )
    sdk.mark_as_leaf(child3["requirement_id"])
    sdk.add_validation(child3["requirement_id"], [{"name": "测试3"}])

    # Act: 恢复快照
    result = sdk.restore_snapshot(snapshot_id)

    # Assert
    assert result["restored_count"] > 0

    # 验证恢复后只有 3 个需求（父需求 + 2 个子需求）
    with get_session() as session:
        reqs_after = session.query(Requirement).filter_by(
            project_id=project["project_id"]
        ).all()
        assert len(reqs_after) == 3

        # 验证层级关系
        parent_req = session.query(Requirement).filter_by(
            id=parent["requirement_id"]
        ).first()
        children = session.query(Requirement).filter_by(
            parent_id=parent["requirement_id"]
        ).all()
        assert len(children) == 2


def test_snapshot_empty_project():
    """测试空项目的快照恢复"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("空项目")

    # 创建空项目快照
    snapshot_id = sdk.create_snapshot(project["project_id"])

    # 添加需求
    req1 = sdk.add_requirement(project["project_id"], "需求1")

    # Act: 恢复快照
    result = sdk.restore_snapshot(snapshot_id)

    # Assert - 空项目恢复可能返回 0 或其他值
    # 验证恢复后项目为空
    with get_session() as session:
        reqs_after = session.query(Requirement).filter_by(
            project_id=project["project_id"]
        ).all()
        assert len(reqs_after) == 0


def test_snapshot_multiple_restores():
    """测试多次恢复同一个快照"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建需求
    req1 = sdk.add_requirement(project["project_id"], "需求1")
    sdk.mark_as_leaf(req1["requirement_id"])
    sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])

    # 创建快照
    snapshot_id = sdk.create_snapshot(project["project_id"])

    # 第一次恢复
    result1 = sdk.restore_snapshot(snapshot_id)
    assert result1["restored_count"] > 0

    # 添加需求
    req2 = sdk.add_requirement(project["project_id"], "需求2")

    # 第二次恢复（应该恢复到相同的快照状态）
    result2 = sdk.restore_snapshot(snapshot_id)
    assert result2["restored_count"] > 0

    # 验证两次恢复后的状态相同
    with get_session() as session:
        reqs_after = session.query(Requirement).filter_by(
            project_id=project["project_id"]
        ).all()
        assert len(reqs_after) == 1
        assert reqs_after[0].id == req1["requirement_id"]


def test_snapshot_with_dependencies():
    """测试包含依赖关系的快照恢复"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建父需求和子需求
    parent = sdk.add_requirement(project["project_id"], "父需求")
    child1 = sdk.add_requirement(
        project["project_id"],
        "子需求1",
        parent_id=parent["requirement_id"]
    )
    child2 = sdk.add_requirement(
        project["project_id"],
        "子需求2",
        parent_id=parent["requirement_id"]
    )
    sdk.mark_as_leaf(child1["requirement_id"])
    sdk.mark_as_leaf(child2["requirement_id"])
    sdk.add_validation(child1["requirement_id"], [{"name": "测试1"}])
    sdk.add_validation(child2["requirement_id"], [{"name": "测试2"}])

    # 设置依赖关系（从父需求传递给子需求）
    sdk.transfer_dependencies(parent["requirement_id"], {
        child1["requirement_id"]: [],
        child2["requirement_id"]: []
    })

    # 创建快照
    snapshot_id = sdk.create_snapshot(project["project_id"])

    # 在快照后添加新需求
    child3 = sdk.add_requirement(
        project["project_id"],
        "子需求3",
        parent_id=parent["requirement_id"]
    )
    sdk.mark_as_leaf(child3["requirement_id"])
    sdk.add_validation(child3["requirement_id"], [{"name": "测试3"}])

    # Act: 恢复快照
    result = sdk.restore_snapshot(snapshot_id)

    # Assert
    assert result["restored_count"] > 0

    # 验证恢复后只有 3 个需求（父需求 + 2 个子需求）
    with get_session() as session:
        reqs_after = session.query(Requirement).filter_by(
            project_id=project["project_id"]
        ).all()
        assert len(reqs_after) == 3

        # 验证依赖关系存储在需求中
        parent_req = session.query(Requirement).filter_by(
            id=parent["requirement_id"]
        ).first()
        # 父需求应该有子需求
        children = session.query(Requirement).filter_by(
            parent_id=parent["requirement_id"]
        ).all()
        assert len(children) == 2