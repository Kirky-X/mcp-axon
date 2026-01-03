# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""项目锁管理器测试"""

import time

import pytest

from src.db.models import Project
from src.utils.lock_manager import ProjectLockManager


def test_tc016_acquire_project_lock(sync_session):
    """TC-016: 测试获取项目锁"""

    # Arrange
    lock_manager = ProjectLockManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act
    result = lock_manager.acquire_lock(
        sync_session, project_id=project.id, session_id="session1"
    )

    # Assert
    assert result is True
    sync_session.refresh(project)
    assert project.locked_by == "session1"
    assert project.locked_at is not None


def test_tc017_lock_conflict(sync_session):
    """TC-017: 测试锁冲突"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act
    lock_manager.acquire_lock(sync_session, project.id, "session1")
    result = lock_manager.acquire_lock(sync_session, project.id, "session2")

    # Assert
    assert result is False


def test_tc018_lock_timeout(sync_session):
    """TC-018: 测试锁超时"""
    # Arrange
    lock_manager = ProjectLockManager(timeout_minutes=0.001)  # 0.06秒超时
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act
    lock_manager.acquire_lock(sync_session, project.id, "session1")
    time.sleep(0.1)  # 等待超时

    result = lock_manager.acquire_lock(sync_session, project.id, "session2")

    # Assert
    assert result is True
    sync_session.refresh(project)
    assert project.locked_by == "session2"


def test_release_lock(sync_session):
    """测试释放锁"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    lock_manager.acquire_lock(sync_session, project.id, "session1")

    # Act
    result = lock_manager.release_lock(sync_session, project.id, "session1")

    # Assert
    assert result is True
    sync_session.refresh(project)
    assert project.locked_by is None


def test_release_lock_wrong_session(sync_session):
    """测试非锁定会话释放锁（应失败）"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    lock_manager.acquire_lock(sync_session, project.id, "session1")

    # Act
    result = lock_manager.release_lock(sync_session, project.id, "session2")

    # Assert
    assert result is False


def test_is_locked(sync_session):
    """测试检查是否锁定"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act & Assert: 未锁定
    assert lock_manager.is_locked(sync_session, project.id) is False

    # 获取锁
    lock_manager.acquire_lock(sync_session, project.id, "session1")

    # Act & Assert: 已锁定
    assert lock_manager.is_locked(sync_session, project.id) is True


def test_is_locked_expired(sync_session):
    """测试检查过期锁"""
    # Arrange
    lock_manager = ProjectLockManager(timeout_minutes=0.001)  # 0.06秒超时
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    lock_manager.acquire_lock(sync_session, project.id, "session1")
    time.sleep(0.1)  # 等待超时

    # Act
    result = lock_manager.is_locked(sync_session, project.id)

    # Assert
    assert result is False


def test_get_lock_info(sync_session):
    """测试获取锁信息"""
    # Arrange
    lock_manager = ProjectLockManager(timeout_minutes=30)
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    lock_manager.acquire_lock(sync_session, project.id, "session1")

    # Act
    lock_info = lock_manager.get_lock_info(sync_session, project.id)

    # Assert
    assert lock_info is not None
    assert lock_info["project_id"] == project.id
    assert lock_info["locked_by"] == "session1"
    assert lock_info["timeout_minutes"] == 30
    assert "elapsed_seconds" in lock_info
    assert "remaining_seconds" in lock_info


def test_get_lock_info_not_locked(sync_session):
    """测试获取未锁定项目的锁信息"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act
    lock_info = lock_manager.get_lock_info(sync_session, project.id)

    # Assert
    assert lock_info is None


def test_cleanup_expired_locks(sync_session):
    """测试清理过期锁"""
    # Arrange
    lock_manager = ProjectLockManager(timeout_minutes=0.001)  # 0.06秒超时

    project1 = Project(name="项目1")
    project2 = Project(name="项目2")
    sync_session.add_all([project1, project2])
    sync_session.commit()

    # 锁定两个项目
    lock_manager.acquire_lock(sync_session, project1.id, "session1")
    lock_manager.acquire_lock(sync_session, project2.id, "session2")

    # 等待超时
    time.sleep(0.1)

    # Act
    cleaned_count = lock_manager.cleanup_expired_locks(sync_session)

    # Assert
    assert cleaned_count == 2

    # 验证锁已释放
    sync_session.refresh(project1)
    sync_session.refresh(project2)
    assert project1.locked_by is None
    assert project2.locked_by is None


def test_acquire_lock_nonexistent_project(sync_session):
    """测试获取不存在项目的锁"""
    # Arrange
    lock_manager = ProjectLockManager()

    # Act & Assert
    with pytest.raises(ValueError, match="项目不存在"):
        lock_manager.acquire_lock(
            sync_session, project_id="nonexistent-id", session_id="session1"
        )


def test_reacquire_lock_same_session(sync_session):
    """测试同一会话重新获取锁"""
    # Arrange
    lock_manager = ProjectLockManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 第一次获取锁
    lock_manager.acquire_lock(sync_session, project.id, "session1")

    # Act: 同一会话再次获取锁
    result = lock_manager.acquire_lock(sync_session, project.id, "session1")

    # Assert: 应该成功
    assert result is True
