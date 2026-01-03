# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""事件日志工具测试"""

from src.db.models import Event
from src.utils.event_logger import log_event


def test_log_event_basic(sync_session):
    """测试基本事件记录"""

    # Arrange
    project_id = "test_project_id"
    event_type = "RequirementCreated"
    aggregate_id = "test_requirement_id"

    # Act
    log_event(
        sync_session, project_id, event_type, aggregate_id, {"content": "测试需求"}
    )

    # Assert
    events = sync_session.query(Event).filter_by(project_id=project_id).all()
    assert len(events) == 1
    assert events[0].event_type == event_type
    assert events[0].aggregate_id == aggregate_id
    assert events[0].payload["content"] == "测试需求"


def test_log_event_with_project_id(sync_session):
    """测试事件记录（带项目ID）"""

    # Arrange
    project_id = "test_project_123"
    event_type = "ProjectCreated"
    aggregate_id = project_id

    # Act
    log_event(sync_session, project_id, event_type, aggregate_id, {"name": "测试项目"})

    # Assert
    events = sync_session.query(Event).filter_by(project_id=project_id).all()
    assert len(events) == 1
    assert events[0].event_type == event_type
    assert events[0].aggregate_id == aggregate_id


def test_log_event_multiple_events(sync_session):
    """测试记录多个事件"""

    # Arrange
    project_id = "test_project_multi"

    # Act
    log_event(sync_session, project_id, "Event1", "entity1", {"data": 1})
    log_event(sync_session, project_id, "Event2", "entity2", {"data": 2})
    log_event(sync_session, project_id, "Event3", "entity3", {"data": 3})

    # Assert
    events = sync_session.query(Event).filter_by(project_id=project_id).all()
    assert len(events) == 3


def test_log_event_with_complex_data(sync_session):
    """测试事件记录（复杂数据）"""

    # Arrange
    project_id = "test_project_complex"
    complex_data = {
        "nested": {"level1": {"level2": "value"}},
        "list": [1, 2, 3],
        "string": "test",
    }

    # Act
    log_event(sync_session, project_id, "ComplexEvent", "entity_id", complex_data)

    # Assert
    events = sync_session.query(Event).filter_by(project_id=project_id).all()
    assert len(events) == 1
    assert events[0].payload == complex_data


def test_log_event_empty_data(sync_session):
    """测试事件记录（空数据）"""

    # Arrange
    project_id = "test_project_empty"

    # Act
    log_event(sync_session, project_id, "EmptyEvent", "entity_id", {})

    # Assert
    events = sync_session.query(Event).filter_by(project_id=project_id).all()
    assert len(events) == 1
    assert events[0].payload == {}


def test_log_event_sequence_order(sync_session):
    """测试事件记录序列号顺序"""

    # Arrange
    project_id = "test_project_sequence"

    # Act
    log_event(sync_session, project_id, "Event1", "entity1", {"order": 1})
    log_event(sync_session, project_id, "Event2", "entity2", {"order": 2})
    log_event(sync_session, project_id, "Event3", "entity3", {"order": 3})

    # Assert
    events = (
        sync_session.query(Event)
        .filter_by(project_id=project_id)
        .order_by(Event.sequence)
        .all()
    )
    assert len(events) == 3
    assert events[0].sequence == 1
    assert events[1].sequence == 2
    assert events[2].sequence == 3


def test_log_event_different_projects(sync_session):
    """测试不同项目的事件记录"""

    # Arrange
    project1_id = "project1"
    project2_id = "project2"

    # Act
    log_event(sync_session, project1_id, "Event1", "entity1", {})
    log_event(sync_session, project2_id, "Event2", "entity2", {})
    log_event(sync_session, project1_id, "Event3", "entity3", {})

    # Assert
    events1 = sync_session.query(Event).filter_by(project_id=project1_id).all()
    events2 = sync_session.query(Event).filter_by(project_id=project2_id).all()
    assert len(events1) == 2
    assert len(events2) == 1


def test_log_event_with_metadata(sync_session):
    """测试事件记录（带元数据）"""

    # Arrange
    project_id = "test_project_metadata"
    metadata = {"user": "test_user", "ip": "127.0.0.1"}

    # Act
    log_event(
        sync_session,
        project_id,
        "MetadataEvent",
        "entity_id",
        {"message": "Test"},
        metadata=metadata,
    )

    # Assert
    events = sync_session.query(Event).filter_by(project_id=project_id).all()
    assert len(events) == 1
    assert events[0].event_metadata == metadata


def test_log_event_with_unicode(sync_session):
    """测试事件记录（Unicode字符）"""

    # Arrange
    project_id = "test_project_unicode"
    unicode_data = {
        "chinese": "中文测试",
        "emoji": "🎉🚀",
        "special": "特殊字符: @#$%^&*()",
    }

    # Act
    log_event(sync_session, project_id, "UnicodeEvent", "entity_id", unicode_data)

    # Assert
    events = sync_session.query(Event).filter_by(project_id=project_id).all()
    assert len(events) == 1
    assert events[0].payload == unicode_data


def test_log_event_large_data(sync_session):
    """测试事件记录（大数据量）"""

    # Arrange
    project_id = "test_project_large"
    large_data = {"item_" + str(i): i for i in range(100)}

    # Act
    log_event(sync_session, project_id, "LargeEvent", "entity_id", large_data)

    # Assert
    events = sync_session.query(Event).filter_by(project_id=project_id).all()
    assert len(events) == 1
    assert events[0].payload == large_data


def test_log_event_query_by_event_type(sync_session):
    """测试按事件类型查询"""

    # Arrange
    project_id = "test_project_query"
    log_event(sync_session, project_id, "TypeA", "entity1", {})
    log_event(sync_session, project_id, "TypeB", "entity2", {})
    log_event(sync_session, project_id, "TypeA", "entity3", {})

    # Act
    events_a = (
        sync_session.query(Event)
        .filter_by(project_id=project_id, event_type="TypeA")
        .all()
    )
    events_b = (
        sync_session.query(Event)
        .filter_by(project_id=project_id, event_type="TypeB")
        .all()
    )

    # Assert
    assert len(events_a) == 2
    assert len(events_b) == 1


def test_log_event_order_by_created_at(sync_session):
    """测试按创建时间排序"""

    # Arrange
    project_id = "test_project_order"

    # Act
    log_event(sync_session, project_id, "Event1", "entity1", {"order": 1})
    log_event(sync_session, project_id, "Event2", "entity2", {"order": 2})
    log_event(sync_session, project_id, "Event3", "entity3", {"order": 3})

    # Assert
    events = (
        sync_session.query(Event)
        .filter_by(project_id=project_id)
        .order_by(Event.created_at)
        .all()
    )
    assert len(events) == 3
    assert events[0].payload["order"] == 1
    assert events[1].payload["order"] == 2
    assert events[2].payload["order"] == 3
