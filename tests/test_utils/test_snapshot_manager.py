# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""快照管理器测试"""

import pytest
from sqlalchemy.orm.attributes import flag_modified

from src.db.models import (
    ChainState,
    ChainStatus,
    Event,
    Project,
    Requirement,
    RequirementStatus,
)
from src.utils.snapshot_manager import SnapshotManager

# 测试会话 ID
TEST_SESSION_ID = "test-session-123456789"


def test_create_snapshot_with_requirements(sync_session):
    """测试创建包含需求的快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.DRAFT.value
    )
    req2 = Requirement(
        project_id=project.id, content="需求2", status=RequirementStatus.LEAF.value
    )
    sync_session.add_all([req1, req2])
    sync_session.commit()

    # Act
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # Assert
    assert snapshot_id is not None

    # 验证快照事件已创建
    snapshot_event = sync_session.query(Event).filter_by(id=snapshot_id).first()
    assert snapshot_event is not None
    assert snapshot_event.event_type == "SnapshotCreated"
    assert "requirements" in snapshot_event.payload
    assert len(snapshot_event.payload["requirements"]) == 2


def test_create_snapshot_with_chain_state(sync_session):
    """测试创建包含链化状态的快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.VALIDATED.value
    )
    sync_session.add(req)
    sync_session.commit()

    # 创建链化状态
    chain_state = ChainState(
        project_id=project.id,
        status=ChainStatus.COMPLETED.value,
        chain_head_id=req.id,
        current_node_id=req.id,
        total_nodes=1,
        completed_nodes=0,
        progress_percentage=0,
    )
    sync_session.add(chain_state)
    sync_session.commit()

    # Act
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # Assert
    assert snapshot_id is not None

    # 验证快照包含链化状态
    snapshot_event = sync_session.query(Event).filter_by(id=snapshot_id).first()
    assert snapshot_event is not None
    assert "chain_state" in snapshot_event.payload
    assert (
        snapshot_event.payload["chain_state"]["status"] == ChainStatus.COMPLETED.value
    )


def test_create_snapshot_empty_project(sync_session):
    """测试创建空项目的快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="空项目")
    sync_session.add(project)
    sync_session.commit()

    # Act
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # Assert
    assert snapshot_id is not None

    # 验证快照事件已创建
    snapshot_event = sync_session.query(Event).filter_by(id=snapshot_id).first()
    assert snapshot_event is not None
    assert snapshot_event.event_type == "SnapshotCreated"
    assert len(snapshot_event.payload["requirements"]) == 0


def test_restore_snapshot_success(sync_session):
    """测试成功恢复快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.DRAFT.value
    )
    req2 = Requirement(
        project_id=project.id, content="需求2", status=RequirementStatus.LEAF.value
    )
    sync_session.add_all([req1, req2])
    sync_session.commit()

    # 创建快照
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # 修改需求状态
    req1.status = RequirementStatus.CHAINED.value
    req2.status = RequirementStatus.CHAINED.value
    sync_session.commit()

    # Act
    result = manager.restore_snapshot(sync_session, snapshot_id, TEST_SESSION_ID)

    # Assert
    assert result["snapshot_id"] == snapshot_id
    assert result["restored_count"] == 2
    assert "快照恢复成功" in result["message"]

    # 验证需求状态已恢复
    sync_session.refresh(req1)
    sync_session.refresh(req2)
    assert req1.status == RequirementStatus.DRAFT.value
    assert req2.status == RequirementStatus.LEAF.value


def test_restore_snapshot_with_chain_state(sync_session):
    """测试恢复包含链化状态的快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.VALIDATED.value
    )
    sync_session.add(req)
    sync_session.commit()

    # 创建链化状态
    chain_state = ChainState(
        project_id=project.id,
        status=ChainStatus.COMPLETED.value,
        chain_head_id=req.id,
        current_node_id=req.id,
        total_nodes=1,
        completed_nodes=0,
        progress_percentage=0,
    )
    sync_session.add(chain_state)
    sync_session.commit()

    # 创建快照
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # 修改链化状态
    chain_state.completed_nodes = 1
    chain_state.progress_percentage = 100
    sync_session.commit()

    # Act
    result = manager.restore_snapshot(sync_session, snapshot_id, TEST_SESSION_ID)

    # Assert
    assert result["restored_count"] >= 0

    # 验证链化状态已恢复
    sync_session.refresh(chain_state)
    assert chain_state.completed_nodes == 0
    assert chain_state.progress_percentage == 0


def test_restore_snapshot_delete_new_requirements(sync_session):
    """测试恢复快照时删除新创建的需求"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.DRAFT.value
    )
    sync_session.add(req1)
    sync_session.commit()

    # 创建快照
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # 在快照后创建新需求
    req2 = Requirement(
        project_id=project.id, content="需求2", status=RequirementStatus.DRAFT.value
    )
    sync_session.add(req2)
    sync_session.commit()

    # Act
    result = manager.restore_snapshot(sync_session, snapshot_id, TEST_SESSION_ID)

    # Assert
    assert result["restored_count"] == 1

    # 验证 req2 已被删除
    deleted_req = sync_session.query(Requirement).filter_by(id=req2.id).first()
    assert deleted_req is None


def test_restore_snapshot_nonexistent(sync_session):
    """测试恢复不存在的快照"""
    # Arrange
    manager = SnapshotManager()

    # Act & Assert
    with pytest.raises(ValueError, match="快照不存在"):
        manager.restore_snapshot(
            sync_session, "nonexistent-snapshot-id", TEST_SESSION_ID
        )


def test_restore_snapshot_invalid_type(sync_session):
    """测试恢复非快照类型的事件"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建非快照类型的事件
    event = Event(
        project_id=project.id,
        event_type="RequirementAdded",
        aggregate_id="req-1",
        payload={"content": "测试"},
        sequence=1,
    )
    sync_session.add(event)
    sync_session.commit()

    # Act & Assert
    try:
        manager.restore_snapshot(sync_session, event.id, TEST_SESSION_ID)
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "事件类型不是快照" in str(e)


def test_get_latest_snapshot_exists(sync_session):
    """测试获取存在的最新快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建快照
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # Act
    result = manager.get_latest_snapshot(sync_session, project.id)

    # Assert
    assert result is not None
    assert result["snapshot_id"] == snapshot_id
    assert "data" in result
    assert "created_at" in result


def test_get_latest_snapshot_not_exists(sync_session):
    """测试获取不存在的最新快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act
    result = manager.get_latest_snapshot(sync_session, project.id)

    # Assert
    assert result is None


def test_list_snapshots(sync_session):
    """测试列出快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建多个快照
    snapshot1 = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)
    snapshot2 = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)
    snapshot3 = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # Act
    snapshots = manager.list_snapshots(sync_session, project.id, limit=10)

    # Assert
    assert len(snapshots) == 3
    assert snapshots[0]["snapshot_id"] == snapshot3  # 最新的在前
    assert snapshots[1]["snapshot_id"] == snapshot2
    assert snapshots[2]["snapshot_id"] == snapshot1


def test_list_snapshots_with_limit(sync_session):
    """测试列出快照（带限制）"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建 5 个快照
    for _ in range(5):
        manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # Act
    snapshots = manager.list_snapshots(sync_session, project.id, limit=3)

    # Assert
    assert len(snapshots) == 3


def test_list_snapshots_empty(sync_session):
    """测试列出空项目的快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act
    snapshots = manager.list_snapshots(sync_session, project.id)

    # Assert
    assert len(snapshots) == 0


def test_delete_snapshot_success(sync_session):
    """测试成功删除快照"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建快照
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # Act
    result = manager.delete_snapshot(sync_session, snapshot_id)

    # Assert
    assert result is True

    # 验证快照已删除
    snapshot = sync_session.query(Event).filter_by(id=snapshot_id).first()
    assert snapshot is None


def test_delete_snapshot_nonexistent(sync_session):
    """测试删除不存在的快照"""
    # Arrange
    manager = SnapshotManager()

    # Act
    result = manager.delete_snapshot(sync_session, "nonexistent-snapshot-id")

    # Assert
    assert result is False


def test_delete_snapshot_invalid_type(sync_session):
    """测试删除非快照类型的事件"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建非快照类型的事件
    event = Event(
        project_id=project.id,
        event_type="RequirementAdded",
        aggregate_id="req-1",
        payload={"content": "测试"},
        sequence=1,
    )
    sync_session.add(event)
    sync_session.commit()

    # Act
    result = manager.delete_snapshot(sync_session, event.id)

    # Assert
    assert result is False


def test_snapshot_preserves_dependencies(sync_session):
    """测试快照保留依赖关系"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建有依赖关系的需求
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.VALIDATED.value
    )
    sync_session.add(req1)
    sync_session.flush()

    req2 = Requirement(
        project_id=project.id,
        content="需求2",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[req1.id],
    )
    sync_session.add(req2)
    sync_session.flush()
    flag_modified(req2, "dependencies")
    sync_session.commit()

    # 创建快照
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # 修改依赖关系
    req2.dependencies = []
    sync_session.flush()
    flag_modified(req2, "dependencies")
    sync_session.commit()

    # Act
    result = manager.restore_snapshot(sync_session, snapshot_id, TEST_SESSION_ID)

    # Assert
    assert result["restored_count"] == 2

    # 验证依赖关系已恢复
    sync_session.refresh(req2)
    assert req1.id in req2.dependencies


def test_snapshot_preserves_chain_order(sync_session):
    """测试快照保留链表顺序"""
    # Arrange
    manager = SnapshotManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求并设置链表顺序
    req1 = Requirement(
        project_id=project.id,
        content="需求1",
        status=RequirementStatus.CHAINED.value,
        chain_order=1,
    )
    req2 = Requirement(
        project_id=project.id,
        content="需求2",
        status=RequirementStatus.CHAINED.value,
        chain_order=2,
    )
    sync_session.add_all([req1, req2])
    sync_session.flush()

    req1.next_requirement_id = req2.id
    sync_session.flush()
    flag_modified(req1, "next_requirement_id")
    sync_session.commit()

    # 创建快照
    snapshot_id = manager.create_snapshot(sync_session, project.id, TEST_SESSION_ID)

    # 修改链表顺序
    req1.chain_order = 10
    req1.next_requirement_id = None
    sync_session.flush()
    flag_modified(req1, "chain_order")
    flag_modified(req1, "next_requirement_id")
    sync_session.commit()

    # Act
    result = manager.restore_snapshot(sync_session, snapshot_id, TEST_SESSION_ID)

    # Assert
    assert result["restored_count"] == 2

    # 验证链表顺序已恢复
    sync_session.refresh(req1)
    sync_session.refresh(req2)
    assert req1.chain_order == 1
    assert req1.next_requirement_id == req2.id
    assert req2.chain_order == 2
