# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""快照管理器测试 (LadybugDB 图数据库版本)"""

import pytest

from src.db.graph_models import RequirementStatus, deserialize_json
from src.utils.snapshot_manager import SnapshotManager

# 测试会话 ID
TEST_SESSION_ID = "test-session-123456789"


def _get_event_by_uuid(conn, event_uuid: str) -> dict:
    """通过 UUID 获取事件"""
    result = conn.execute(
        """
        MATCH (e:Event {uuid: $uuid})
        RETURN e.uuid, e.project_uuid, e.event_type, e.aggregate_uuid,
               e.payload, e.event_metadata, e.sequence, e.created_at
        """,
        {"uuid": event_uuid},
    )
    rows = list(result)
    if not rows:
        return None
    payload_raw = rows[0][4]
    metadata_raw = rows[0][5]
    return {
        "uuid": rows[0][0],
        "project_uuid": rows[0][1],
        "event_type": rows[0][2],
        "aggregate_uuid": rows[0][3],
        "payload": deserialize_json(payload_raw) if payload_raw else {},
        "event_metadata": deserialize_json(metadata_raw) if metadata_raw else None,
        "sequence": rows[0][6],
        "created_at": rows[0][7],
    }


def _get_requirement_by_uuid(conn, requirement_uuid: str) -> dict:
    """通过 UUID 获取需求"""
    result = conn.execute(
        """
        MATCH (r:Requirement {uuid: $uuid})
        OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Requirement)
        OPTIONAL MATCH (r)-[:NEXT_IN_CHAIN]->(next:Requirement)
        RETURN r.uuid, r.project_uuid, r.parent_uuid, r.content, r.decompose_reason,
               r.status, r.level, r.order_in_parent, r.chain_order,
               r.created_at, r.updated_at, r.version,
               collect(dep.uuid) as dependencies,
               next.uuid as next_requirement_uuid
        """,
        {"uuid": requirement_uuid},
    )
    rows = list(result)
    if not rows:
        return None
    return {
        "uuid": rows[0][0],
        "project_uuid": rows[0][1],
        "parent_uuid": rows[0][2] if rows[0][2] else None,
        "content": rows[0][3],
        "decompose_reason": rows[0][4] if rows[0][4] else None,
        "status": rows[0][5],
        "level": rows[0][6],
        "order_in_parent": rows[0][7],
        "chain_order": rows[0][8] if rows[0][8] != -1 else None,
        "created_at": rows[0][9],
        "updated_at": rows[0][10],
        "version": rows[0][11] if len(rows[0]) > 11 else 1,
        "dependencies": list(rows[0][12]) if rows[0][12] else [],
        "next_requirement_uuid": rows[0][13]
        if len(rows[0]) > 13 and rows[0][13]
        else None,
    }


def _get_requirements_by_project(conn, project_uuid: str) -> list:
    """获取项目所有需求"""
    result = conn.execute(
        """
        MATCH (r:Requirement {project_uuid: $project_uuid})
        RETURN r.uuid, r.status, r.chain_order, r.content
        ORDER BY r.created_at ASC
        """,
        {"project_uuid": project_uuid},
    )
    requirements = []
    for row in result:
        requirements.append(
            {
                "uuid": row[0],
                "status": row[1],
                "chain_order": row[2] if row[2] != -1 else None,
                "content": row[3],
            }
        )
    return requirements


def _get_chain_state_by_project(conn, project_uuid: str) -> dict:
    """获取项目链化状态"""
    result = conn.execute(
        """
        MATCH (cs:ChainState {project_uuid: $project_uuid})
        RETURN cs.uuid, cs.status, cs.chain_head_uuid, cs.current_node_uuid,
               cs.total_nodes, cs.completed_nodes, cs.progress_percentage
        """,
        {"project_uuid": project_uuid},
    )
    rows = list(result)
    if not rows:
        return None
    return {
        "uuid": rows[0][0],
        "status": rows[0][1],
        "chain_head_uuid": rows[0][2] if rows[0][2] else None,
        "current_node_uuid": rows[0][3] if rows[0][3] else None,
        "total_nodes": rows[0][4],
        "completed_nodes": rows[0][5],
        "progress_percentage": rows[0][6],
    }


def test_create_snapshot_with_requirements(
    graph_connection, project_manager, requirement_manager, snapshot_manager
):
    """测试创建包含需求的快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求
    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")

    # Act
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # Assert
    assert snapshot_id is not None

    # 验证快照事件已创建
    snapshot_event = _get_event_by_uuid(graph_connection, snapshot_id)
    assert snapshot_event is not None
    assert snapshot_event["event_type"] == "SnapshotCreated"
    assert "requirements" in snapshot_event["payload"]
    assert len(snapshot_event["payload"]["requirements"]) == 2


def test_create_snapshot_with_chain_state(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    snapshot_manager,
):
    """测试创建包含链化状态的快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求并验证（add_validation 会自动将状态改为 VALIDATED）
    req = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req_id = req["requirement_id"]
    validation_service.add_validation(graph_connection, req_id, [])

    # Act
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # Assert
    assert snapshot_id is not None

    # 验证快照包含链化状态
    snapshot_event = _get_event_by_uuid(graph_connection, snapshot_id)
    assert snapshot_event is not None
    assert "chain_state" in snapshot_event["payload"]
    # 链化状态初始应该是 IDLE 或空
    chain_state = snapshot_event["payload"]["chain_state"]
    assert chain_state is not None  # 不应该为空，至少有默认值


def test_create_snapshot_empty_project(
    graph_connection, project_manager, snapshot_manager
):
    """测试创建空项目的快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "空项目")
    project_id = project["project_id"]

    # Act
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # Assert
    assert snapshot_id is not None

    # 验证快照事件已创建
    snapshot_event = _get_event_by_uuid(graph_connection, snapshot_id)
    assert snapshot_event is not None
    assert snapshot_event["event_type"] == "SnapshotCreated"
    assert len(snapshot_event["payload"]["requirements"]) == 0


def test_restore_snapshot_success(
    graph_connection, project_manager, requirement_manager, snapshot_manager
):
    """测试成功恢复快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求（默认是 LEAF 状态）
    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")
    req1_id = req1["requirement_id"]
    req2_id = req2["requirement_id"]

    # 创建快照
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # 修改需求状态（通过图查询直接修改）
    graph_connection.execute(
        """
        MATCH (r:Requirement {uuid: $uuid})
        SET r.status = 'CHAINED', r.chain_order = 1
        """,
        {"uuid": req1_id},
    )
    graph_connection.execute(
        """
        MATCH (r:Requirement {uuid: $uuid})
        SET r.status = 'CHAINED', r.chain_order = 2
        """,
        {"uuid": req2_id},
    )

    # Act
    result = snapshot_manager.restore_snapshot(
        graph_connection, snapshot_id, TEST_SESSION_ID
    )

    # Assert
    assert result["snapshot_id"] == snapshot_id
    assert result["restored_count"] == 2
    assert "快照恢复成功" in result["message"]

    # 验证需求状态已恢复（LEAF 状态）
    req1_data = _get_requirement_by_uuid(graph_connection, req1_id)
    req2_data = _get_requirement_by_uuid(graph_connection, req2_id)
    assert req1_data["status"] == RequirementStatus.LEAF.value
    assert req2_data["status"] == RequirementStatus.LEAF.value
    assert req1_data["chain_order"] is None
    assert req2_data["chain_order"] is None


def test_restore_snapshot_with_chain_state(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    snapshot_manager,
):
    """测试恢复包含链化状态的快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求并验证
    req = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req_id = req["requirement_id"]
    validation_service.add_validation(graph_connection, req_id, [])

    # 创建快照
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # 修改链化状态（通过图查询直接修改）
    graph_connection.execute(
        """
        MATCH (cs:ChainState {project_uuid: $project_uuid})
        SET cs.completed_nodes = 1, cs.progress_percentage = 100
        """,
        {"project_uuid": project_id},
    )

    # Act
    result = snapshot_manager.restore_snapshot(
        graph_connection, snapshot_id, TEST_SESSION_ID
    )

    # Assert
    assert result["restored_count"] >= 0

    # 验证链化状态已恢复
    chain_state = _get_chain_state_by_project(graph_connection, project_id)
    assert chain_state["completed_nodes"] == 0
    assert chain_state["progress_percentage"] == 0


def test_restore_snapshot_delete_new_requirements(
    graph_connection, project_manager, requirement_manager, snapshot_manager
):
    """测试恢复快照时删除新创建的需求"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求
    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req1_id = req1["requirement_id"]

    # 创建快照
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # 在快照后创建新需求
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")
    req2_id = req2["requirement_id"]

    # Act
    result = snapshot_manager.restore_snapshot(
        graph_connection, snapshot_id, TEST_SESSION_ID
    )

    # Assert
    assert result["restored_count"] == 1

    # 验证 req2 已被删除
    deleted_req = _get_requirement_by_uuid(graph_connection, req2_id)
    assert deleted_req is None


def test_restore_snapshot_nonexistent(graph_connection):
    """测试恢复不存在的快照"""
    # Arrange
    manager = SnapshotManager()

    # Act & Assert
    with pytest.raises(ValueError, match="快照不存在"):
        manager.restore_snapshot(
            graph_connection, "nonexistent-snapshot-id", TEST_SESSION_ID
        )


def test_restore_snapshot_invalid_type(graph_connection, project_manager):
    """测试恢复非快照类型的事件"""
    # Arrange
    manager = SnapshotManager()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建非快照类型的事件（通过直接插入）
    from src.db.graph_models import serialize_json, now_utc
    import uuid

    event_uuid = str(uuid.uuid4())
    graph_connection.execute(
        """
        CREATE (e:Event {
            uuid: $uuid,
            project_uuid: $project_uuid,
            event_type: 'RequirementAdded',
            aggregate_uuid: 'req-1',
            payload: $payload,
            event_metadata: '',
            sequence: 1,
            created_at: $created_at
        })
        """,
        {
            "uuid": event_uuid,
            "project_uuid": project_id,
            "payload": serialize_json({"content": "测试"}),
            "created_at": now_utc(),
        },
    )

    # Act & Assert
    with pytest.raises(ValueError, match="事件类型不是快照"):
        manager.restore_snapshot(graph_connection, event_uuid, TEST_SESSION_ID)


def test_get_latest_snapshot_exists(
    graph_connection, project_manager, snapshot_manager
):
    """测试获取存在的最新快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建快照
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # Act
    result = snapshot_manager.get_latest_snapshot(graph_connection, project_id)

    # Assert
    assert result is not None
    assert result["snapshot_id"] == snapshot_id
    assert "data" in result
    assert "created_at" in result


def test_get_latest_snapshot_not_exists(
    graph_connection, project_manager, snapshot_manager
):
    """测试获取不存在的最新快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    result = snapshot_manager.get_latest_snapshot(graph_connection, project_id)

    # Assert
    assert result is None


def test_list_snapshots(graph_connection, project_manager, snapshot_manager):
    """测试列出快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建多个快照
    snapshot1 = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )
    snapshot2 = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )
    snapshot3 = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # Act
    snapshots = snapshot_manager.list_snapshots(graph_connection, project_id, limit=10)

    # Assert
    assert len(snapshots) == 3
    assert snapshots[0]["snapshot_id"] == snapshot3  # 最新的在前
    assert snapshots[1]["snapshot_id"] == snapshot2
    assert snapshots[2]["snapshot_id"] == snapshot1


def test_list_snapshots_with_limit(graph_connection, project_manager, snapshot_manager):
    """测试列出快照（带限制）"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建 5 个快照
    for _ in range(5):
        snapshot_manager.create_snapshot(graph_connection, project_id, TEST_SESSION_ID)

    # Act
    snapshots = snapshot_manager.list_snapshots(graph_connection, project_id, limit=3)

    # Assert
    assert len(snapshots) == 3


def test_list_snapshots_empty(graph_connection, project_manager, snapshot_manager):
    """测试列出空项目的快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    snapshots = snapshot_manager.list_snapshots(graph_connection, project_id)

    # Assert
    assert len(snapshots) == 0


def test_delete_snapshot_success(graph_connection, project_manager, snapshot_manager):
    """测试成功删除快照"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建快照
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # Act
    result = snapshot_manager.delete_snapshot(graph_connection, snapshot_id)

    # Assert
    assert result is True

    # 验证快照已删除
    snapshot = _get_event_by_uuid(graph_connection, snapshot_id)
    assert snapshot is None


def test_delete_snapshot_nonexistent(graph_connection):
    """测试删除不存在的快照"""
    # Arrange
    manager = SnapshotManager()

    # Act
    result = manager.delete_snapshot(graph_connection, "nonexistent-snapshot-id")

    # Assert
    assert result is False


def test_delete_snapshot_invalid_type(graph_connection, project_manager):
    """测试删除非快照类型的事件"""
    # Arrange
    manager = SnapshotManager()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建非快照类型的事件
    from src.db.graph_models import serialize_json, now_utc
    import uuid

    event_uuid = str(uuid.uuid4())
    graph_connection.execute(
        """
        CREATE (e:Event {
            uuid: $uuid,
            project_uuid: $project_uuid,
            event_type: 'RequirementAdded',
            aggregate_uuid: 'req-1',
            payload: $payload,
            event_metadata: '',
            sequence: 1,
            created_at: $created_at
        })
        """,
        {
            "uuid": event_uuid,
            "project_uuid": project_id,
            "payload": serialize_json({"content": "测试"}),
            "created_at": now_utc(),
        },
    )

    # Act
    result = manager.delete_snapshot(graph_connection, event_uuid)

    # Assert
    assert result is False


def test_snapshot_preserves_dependencies(
    graph_connection,
    project_manager,
    requirement_manager,
    dependency_service,
    snapshot_manager,
):
    """测试快照保留依赖关系"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建有依赖关系的需求
    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req1_id = req1["requirement_id"]

    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")
    req2_id = req2["requirement_id"]

    # 添加依赖关系
    dependency_service.add_dependency(graph_connection, req2_id, req1_id)

    # 创建快照
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # 修改依赖关系（删除依赖）
    dependency_service.remove_dependency(graph_connection, req2_id, req1_id)

    # Act
    result = snapshot_manager.restore_snapshot(
        graph_connection, snapshot_id, TEST_SESSION_ID
    )

    # Assert
    assert result["restored_count"] == 2

    # 验证依赖关系已恢复
    req2_data = _get_requirement_by_uuid(graph_connection, req2_id)
    assert req1_id in req2_data["dependencies"]


def test_snapshot_preserves_chain_order(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    chain_builder,
    snapshot_manager,
):
    """测试快照保留链表顺序"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求并验证
    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")
    req1_id = req1["requirement_id"]
    req2_id = req2["requirement_id"]

    # 创建验证节点（add_validation 会自动将状态改为 VALIDATED）
    validation_service.add_validation(graph_connection, req1_id, [])
    validation_service.add_validation(graph_connection, req2_id, [])

    # 构建链
    chain_builder.build_chain(graph_connection, project_id)

    # 获取链信息
    req1_before = _get_requirement_by_uuid(graph_connection, req1_id)
    req2_before = _get_requirement_by_uuid(graph_connection, req2_id)

    # 创建快照
    snapshot_id = snapshot_manager.create_snapshot(
        graph_connection, project_id, TEST_SESSION_ID
    )

    # 修改链表顺序（重置）
    graph_connection.execute(
        """
        MATCH (r:Requirement {project_uuid: $project_uuid})
        SET r.chain_order = -1, r.status = 'VALIDATED'
        """,
        {"project_uuid": project_id},
    )
    graph_connection.execute(
        """
        MATCH (r:Requirement {project_uuid: $project_uuid})-[e:NEXT_IN_CHAIN]->()
        DELETE e
        """,
        {"project_uuid": project_id},
    )

    # Act
    result = snapshot_manager.restore_snapshot(
        graph_connection, snapshot_id, TEST_SESSION_ID
    )

    # Assert
    assert result["restored_count"] == 2

    # 验证链表顺序已恢复
    req1_after = _get_requirement_by_uuid(graph_connection, req1_id)
    req2_after = _get_requirement_by_uuid(graph_connection, req2_id)

    # 检查 chain_order 是否恢复（快照保存的是 -1 表示 None）
    if req1_before["chain_order"] is not None:
        assert req1_after["chain_order"] == req1_before["chain_order"]
    if req2_before["chain_order"] is not None:
        assert req2_after["chain_order"] == req2_before["chain_order"]

    # 检查 NEXT_IN_CHAIN 关系是否恢复
    if req1_before["next_requirement_uuid"] is not None:
        assert (
            req1_after["next_requirement_uuid"] == req1_before["next_requirement_uuid"]
        )
