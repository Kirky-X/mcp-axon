# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""事件日志工具测试 (LadybugDB 图数据库版本)"""

from src.db.graph_models import deserialize_json
from src.utils.event_logger import log_event


def _get_events_by_project(conn, project_uuid: str) -> list:
    """获取项目事件列表"""
    result = conn.execute(
        """
        MATCH (e:Event {project_uuid: $project_uuid})
        RETURN e.uuid, e.project_uuid, e.event_type, e.aggregate_uuid,
               e.payload, e.event_metadata, e.sequence, e.created_at
        ORDER BY e.sequence ASC
        """,
        {"project_uuid": project_uuid},
    )
    events = []
    for row in result:
        events.append(
            {
                "uuid": row[0],
                "project_uuid": row[1],
                "event_type": row[2],
                "aggregate_uuid": row[3],
                "payload": deserialize_json(row[4]) if row[4] else {},
                "event_metadata": deserialize_json(row[5]) if row[5] else None,
                "sequence": row[6],
                "created_at": row[7],
            }
        )
    return events


def _get_events_by_project_and_type(conn, project_uuid: str, event_type: str) -> list:
    """获取项目特定类型事件列表"""
    result = conn.execute(
        """
        MATCH (e:Event {project_uuid: $project_uuid, event_type: $event_type})
        RETURN e.uuid, e.project_uuid, e.event_type, e.aggregate_uuid,
               e.payload, e.event_metadata, e.sequence, e.created_at
        ORDER BY e.sequence ASC
        """,
        {"project_uuid": project_uuid, "event_type": event_type},
    )
    events = []
    for row in result:
        events.append(
            {
                "uuid": row[0],
                "project_uuid": row[1],
                "event_type": row[2],
                "aggregate_uuid": row[3],
                "payload": deserialize_json(row[4]) if row[4] else {},
                "event_metadata": deserialize_json(row[5]) if row[5] else None,
                "sequence": row[6],
                "created_at": row[7],
            }
        )
    return events


def test_log_event_basic(graph_connection):
    """测试基本事件记录"""

    # Arrange
    project_id = "test_project_id"
    event_type = "RequirementCreated"
    aggregate_id = "test_requirement_id"

    # Act
    log_event(
        graph_connection, project_id, event_type, aggregate_id, {"content": "测试需求"}
    )

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    assert len(events) == 1
    assert events[0]["event_type"] == event_type
    assert events[0]["aggregate_uuid"] == aggregate_id
    assert events[0]["payload"]["content"] == "测试需求"


def test_log_event_with_project_id(graph_connection):
    """测试事件记录（带项目ID）"""

    # Arrange
    project_id = "test_project_123"
    event_type = "ProjectCreated"
    aggregate_id = project_id

    # Act
    log_event(
        graph_connection, project_id, event_type, aggregate_id, {"name": "测试项目"}
    )

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    assert len(events) == 1
    assert events[0]["event_type"] == event_type
    assert events[0]["aggregate_uuid"] == aggregate_id


def test_log_event_multiple_events(graph_connection):
    """测试记录多个事件"""

    # Arrange
    project_id = "test_project_multi"

    # Act
    log_event(graph_connection, project_id, "Event1", "entity1", {"data": 1})
    log_event(graph_connection, project_id, "Event2", "entity2", {"data": 2})
    log_event(graph_connection, project_id, "Event3", "entity3", {"data": 3})

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    assert len(events) == 3


def test_log_event_with_complex_data(graph_connection):
    """测试事件记录（复杂数据）"""

    # Arrange
    project_id = "test_project_complex"
    complex_data = {
        "nested": {"level1": {"level2": "value"}},
        "list": [1, 2, 3],
        "string": "test",
    }

    # Act
    log_event(graph_connection, project_id, "ComplexEvent", "entity_id", complex_data)

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    assert len(events) == 1
    assert events[0]["payload"] == complex_data


def test_log_event_empty_data(graph_connection):
    """测试事件记录（空数据）"""

    # Arrange
    project_id = "test_project_empty"

    # Act
    log_event(graph_connection, project_id, "EmptyEvent", "entity_id", {})

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    assert len(events) == 1
    assert events[0]["payload"] == {}


def test_log_event_sequence_order(graph_connection):
    """测试事件记录序列号顺序"""

    # Arrange
    project_id = "test_project_sequence"

    # Act
    log_event(graph_connection, project_id, "Event1", "entity1", {"order": 1})
    log_event(graph_connection, project_id, "Event2", "entity2", {"order": 2})
    log_event(graph_connection, project_id, "Event3", "entity3", {"order": 3})

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    # 按 sequence 排序（查询已排序）
    assert len(events) == 3
    assert events[0]["sequence"] == 1
    assert events[1]["sequence"] == 2
    assert events[2]["sequence"] == 3


def test_log_event_different_projects(graph_connection):
    """测试不同项目的事件记录"""

    # Arrange
    project1_id = "project1"
    project2_id = "project2"

    # Act
    log_event(graph_connection, project1_id, "Event1", "entity1", {})
    log_event(graph_connection, project2_id, "Event2", "entity2", {})
    log_event(graph_connection, project1_id, "Event3", "entity3", {})

    # Assert
    events1 = _get_events_by_project(graph_connection, project1_id)
    events2 = _get_events_by_project(graph_connection, project2_id)
    assert len(events1) == 2
    assert len(events2) == 1


def test_log_event_with_metadata(graph_connection):
    """测试事件记录（带元数据）"""

    # Arrange
    project_id = "test_project_metadata"
    metadata = {"user": "test_user", "ip": "127.0.0.1"}

    # Act
    log_event(
        graph_connection,
        project_id,
        "MetadataEvent",
        "entity_id",
        {"message": "Test"},
        metadata=metadata,
    )

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    assert len(events) == 1
    assert events[0]["event_metadata"] == metadata


def test_log_event_with_unicode(graph_connection):
    """测试事件记录（Unicode字符）"""

    # Arrange
    project_id = "test_project_unicode"
    unicode_data = {
        "chinese": "中文测试",
        "emoji": "🎉🚀",
        "special": "特殊字符: @#$%^&*()",
    }

    # Act
    log_event(graph_connection, project_id, "UnicodeEvent", "entity_id", unicode_data)

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    assert len(events) == 1
    assert events[0]["payload"] == unicode_data


def test_log_event_large_data(graph_connection):
    """测试事件记录（大数据量）"""

    # Arrange
    project_id = "test_project_large"
    large_data = {"item_" + str(i): i for i in range(100)}

    # Act
    log_event(graph_connection, project_id, "LargeEvent", "entity_id", large_data)

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    assert len(events) == 1
    assert events[0]["payload"] == large_data


def test_log_event_query_by_event_type(graph_connection):
    """测试按事件类型查询"""

    # Arrange
    project_id = "test_project_query"
    log_event(graph_connection, project_id, "TypeA", "entity1", {})
    log_event(graph_connection, project_id, "TypeB", "entity2", {})
    log_event(graph_connection, project_id, "TypeA", "entity3", {})

    # Act
    events_a = _get_events_by_project_and_type(graph_connection, project_id, "TypeA")
    events_b = _get_events_by_project_and_type(graph_connection, project_id, "TypeB")

    # Assert
    assert len(events_a) == 2
    assert len(events_b) == 1


def test_log_event_order_by_created_at(graph_connection):
    """测试按创建时间排序"""

    # Arrange
    project_id = "test_project_order"

    # Act
    log_event(graph_connection, project_id, "Event1", "entity1", {"order": 1})
    log_event(graph_connection, project_id, "Event2", "entity2", {"order": 2})
    log_event(graph_connection, project_id, "Event3", "entity3", {"order": 3})

    # Assert
    events = _get_events_by_project(graph_connection, project_id)
    assert len(events) == 3
    assert events[0]["payload"]["order"] == 1
    assert events[1]["payload"]["order"] == 2
    assert events[2]["payload"]["order"] == 3
