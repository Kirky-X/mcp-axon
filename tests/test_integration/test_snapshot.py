# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""快照测试"""

from src.core.sdk import RequirementSDK


def test_tc023_snapshot_restore():
    """TC-023: 测试快照恢复"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建需求
    req1 = sdk.add_requirement(project["project_id"], "需求1")
    # 需求默认是叶子节点(req1["requirement_id"])
    sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])

    # 创建快照
    snapshot_id = sdk.create_snapshot(project["project_id"], "test-session-123456789")

    # 修改状态
    sdk.add_requirement(project["project_id"], "需求2")

    # Act: 恢复快照
    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")

    # Assert
    assert result["restored_count"] > 0

    # 验证恢复后的状态
    from src.db.database import get_session

    with get_session() as session:
        from src.db.models import Requirement

        reqs = (
            session.query(Requirement).filter_by(project_id=project["project_id"]).all()
        )
        # 应该只有 req1，没有 req2
        assert len(reqs) == 1


def test_list_snapshots():
    """测试列出快照"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建多个快照
    snapshot1 = sdk.create_snapshot(project["project_id"], "test-session-123456789")
    snapshot2 = sdk.create_snapshot(project["project_id"], "test-session-123456789")
    snapshot3 = sdk.create_snapshot(project["project_id"], "test-session-123456789")

    # Act
    snapshots = sdk.list_snapshots(project["project_id"], limit=10)

    # Assert
    assert len(snapshots) == 3
    assert any(s["snapshot_id"] == snapshot1 for s in snapshots)
    assert any(s["snapshot_id"] == snapshot2 for s in snapshots)
    assert any(s["snapshot_id"] == snapshot3 for s in snapshots)


def test_list_snapshots_limit():
    """测试列出快照（带限制）"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建多个快照
    for _ in range(5):
        sdk.create_snapshot(project["project_id"], "test-session-123456789")

    # Act
    snapshots = sdk.list_snapshots(project["project_id"], limit=3)

    # Assert
    assert len(snapshots) == 3
