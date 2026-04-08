# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""项目锁管理器测试 (LadybugDB 图数据库版本)"""

import time

import pytest

from src.utils.lock_manager import ProjectLockManager


def _get_project_lock_info(conn, project_uuid: str) -> dict:
    """获取项目锁信息"""
    result = conn.execute(
        """
        MATCH (p:Project {uuid: $uuid})
        RETURN p.uuid, p.locked_by, p.locked_at
        """,
        {"uuid": project_uuid},
    )
    rows = list(result)
    if not rows:
        return None
    return {
        "uuid": rows[0][0],
        "locked_by": rows[0][1] if rows[0][1] else None,
        "locked_at": rows[0][2] if rows[0][2] else None,
    }


def test_tc016_acquire_project_lock(graph_connection, project_manager):
    """TC-016: 测试获取项目锁"""

    # Arrange
    lock_manager = ProjectLockManager()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    result = lock_manager.acquire_lock(
        graph_connection, project_id=project_id, session_id="session1"
    )

    # Assert
    assert result is True
    lock_info = _get_project_lock_info(graph_connection, project_id)
    assert lock_info["locked_by"] == "session1"
    assert lock_info["locked_at"] is not None


def test_tc017_lock_conflict(graph_connection, project_manager):
    """TC-017: 测试锁冲突"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    lock_manager.acquire_lock(graph_connection, project_id, "session1")
    result = lock_manager.acquire_lock(graph_connection, project_id, "session2")

    # Assert
    assert result is False


def test_tc018_lock_timeout(graph_connection, project_manager):
    """TC-018: 测试锁超时"""
    # Arrange
    lock_manager = ProjectLockManager(timeout_minutes=0.001)  # 0.06秒超时
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    lock_manager.acquire_lock(graph_connection, project_id, "session1")
    time.sleep(0.1)  # 等待超时

    result = lock_manager.acquire_lock(graph_connection, project_id, "session2")

    # Assert
    assert result is True
    lock_info = _get_project_lock_info(graph_connection, project_id)
    assert lock_info["locked_by"] == "session2"


def test_release_lock(graph_connection, project_manager):
    """测试释放锁"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    lock_manager.acquire_lock(graph_connection, project_id, "session1")

    # Act
    result = lock_manager.release_lock(graph_connection, project_id, "session1")

    # Assert
    assert result is True
    lock_info = _get_project_lock_info(graph_connection, project_id)
    assert lock_info["locked_by"] is None


def test_release_lock_wrong_session(graph_connection, project_manager):
    """测试非锁定会话释放锁（应失败）"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    lock_manager.acquire_lock(graph_connection, project_id, "session1")

    # Act
    result = lock_manager.release_lock(graph_connection, project_id, "session2")

    # Assert
    assert result is False


def test_is_locked(graph_connection, project_manager):
    """测试检查是否锁定"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act & Assert: 未锁定
    assert lock_manager.is_locked(graph_connection, project_id) is False

    # 获取锁
    lock_manager.acquire_lock(graph_connection, project_id, "session1")

    # Act & Assert: 已锁定
    assert lock_manager.is_locked(graph_connection, project_id) is True


def test_is_locked_expired(graph_connection, project_manager):
    """测试检查过期锁"""
    # Arrange
    lock_manager = ProjectLockManager(timeout_minutes=0.001)  # 0.06秒超时
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    lock_manager.acquire_lock(graph_connection, project_id, "session1")
    time.sleep(0.1)  # 等待超时

    # Act
    result = lock_manager.is_locked(graph_connection, project_id)

    # Assert
    assert result is False


def test_get_lock_info(graph_connection, project_manager):
    """测试获取锁信息"""
    # Arrange
    lock_manager = ProjectLockManager(timeout_minutes=30)
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    lock_manager.acquire_lock(graph_connection, project_id, "session1")

    # Act
    lock_info = lock_manager.get_lock_info(graph_connection, project_id)

    # Assert
    assert lock_info is not None
    assert lock_info["project_id"] == project_id
    assert lock_info["locked_by"] == "session1"
    assert lock_info["timeout_minutes"] == 30
    assert "elapsed_seconds" in lock_info
    assert "remaining_seconds" in lock_info


def test_get_lock_info_not_locked(graph_connection, project_manager):
    """测试获取未锁定项目的锁信息"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    lock_info = lock_manager.get_lock_info(graph_connection, project_id)

    # Assert
    assert lock_info is None


def test_cleanup_expired_locks(graph_connection, project_manager):
    """测试清理过期锁"""
    # Arrange
    lock_manager = ProjectLockManager(timeout_minutes=0.001)  # 0.06秒超时

    project1 = project_manager.create_project(graph_connection, "项目1")
    project2 = project_manager.create_project(graph_connection, "项目2")
    project1_id = project1["project_id"]
    project2_id = project2["project_id"]

    # 锁定两个项目
    lock_manager.acquire_lock(graph_connection, project1_id, "session1")
    lock_manager.acquire_lock(graph_connection, project2_id, "session2")

    # 等待超时
    time.sleep(0.1)

    # Act
    cleaned_count = lock_manager.cleanup_expired_locks(graph_connection)

    # Assert
    assert cleaned_count == 2

    # 验证锁已释放
    lock_info1 = _get_project_lock_info(graph_connection, project1_id)
    lock_info2 = _get_project_lock_info(graph_connection, project2_id)
    assert lock_info1["locked_by"] is None
    assert lock_info2["locked_by"] is None


def test_acquire_lock_nonexistent_project(graph_connection):
    """测试获取不存在项目的锁"""
    # Arrange
    lock_manager = ProjectLockManager()

    # Act & Assert
    with pytest.raises(ValueError, match="项目不存在"):
        lock_manager.acquire_lock(
            graph_connection, project_id="nonexistent-id", session_id="session1"
        )


def test_reacquire_lock_same_session(graph_connection, project_manager):
    """测试同一会话重新获取锁"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 第一次获取锁
    lock_manager.acquire_lock(graph_connection, project_id, "session1")

    # Act: 同一会话再次获取锁
    result = lock_manager.acquire_lock(graph_connection, project_id, "session1")

    # Assert: 应该成功
    assert result is True
