# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""项目锁管理器"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.db.models import Project
from src.utils.event_logger import log_event

logger = logging.getLogger(__name__)


class ProjectLockManager:
    """项目锁管理器"""

    def __init__(self, timeout_minutes: int = 30):
        """
        初始化锁管理器

        Args:
            timeout_minutes: 锁超时时间（分钟）
        """
        self.timeout_minutes = timeout_minutes

    def acquire_lock(self, session: Session, project_id: str, session_id: str) -> bool:
        """
        获取项目锁

        Args:
            session: 数据库会话
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            True: 锁获取成功
            False: 锁已被占用
        """
        # 使用 SELECT ... FOR UPDATE 来锁定行，防止竞态条件
        project = (
            session.query(Project).filter_by(id=project_id).with_for_update().first()
        )

        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        # 检查锁是否已超时
        if project.locked_by:
            if self._is_lock_expired(project.locked_at):
                # 锁已超时，自动释放
                logger.info(f"项目锁已超时，自动释放: {project_id}")
                project.locked_by = None
                project.locked_at = None
            else:
                # 锁仍有效，检查是否是当前会话
                if project.locked_by != session_id:
                    logger.warning(
                        f"项目锁已被占用: {project_id} by {project.locked_by}"
                    )
                    session.rollback()
                    return False

        # 获取锁
        project.locked_by = session_id
        project.locked_at = datetime.now(timezone.utc)

        # 记录事件
        log_event(
            session,
            project_id,
            "ProjectLockAcquired",
            project_id,
            {"session_id": session_id, "timeout_minutes": self.timeout_minutes},
        )

        session.commit()

        logger.info(f"项目锁获取成功: {project_id} by {session_id}")

        return True

    def release_lock(self, session: Session, project_id: str, session_id: str) -> bool:
        """
        释放项目锁

        Args:
            session: 数据库会话
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            True: 释放成功
            False: 锁不属于该会话
        """
        project = session.query(Project).filter_by(id=project_id).first()

        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        if project.locked_by != session_id:
            logger.warning(
                f"尝试释放不属于该会话的锁: {project_id} by {session_id}, locked by {project.locked_by}"
            )
            return False

        # 释放锁
        project.locked_by = None
        project.locked_at = None

        # 记录事件
        log_event(
            session,
            project_id,
            "ProjectLockReleased",
            project_id,
            {"session_id": session_id},
        )

        session.commit()

        logger.info(f"项目锁释放成功: {project_id} by {session_id}")

        return True

    def is_locked(self, session: Session, project_id: str) -> bool:
        """
        检查项目是否被锁定

        Args:
            session: 数据库会话
            project_id: 项目 ID

        Returns:
            True: 已锁定
            False: 未锁定
        """
        project = session.query(Project).filter_by(id=project_id).first()

        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        if not project.locked_by:
            return False

        # 检查锁是否已超时
        if self._is_lock_expired(project.locked_at):
            return False

        return True

    def get_lock_info(self, session: Session, project_id: str) -> Optional[dict]:
        """
        获取锁信息

        Args:
            session: 数据库会话
            project_id: 项目 ID

        Returns:
            锁信息字典，如果未锁定则返回 None
        """
        project = session.query(Project).filter_by(id=project_id).first()

        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        if not project.locked_by:
            return None

        # 检查锁是否已超时
        if project.locked_at is None or self._is_lock_expired(project.locked_at):
            return None

        # 确保 locked_at 是 timezone-aware datetime
        locked_at = project.locked_at
        if locked_at.tzinfo is None:
            locked_at = locked_at.replace(tzinfo=timezone.utc)

        # 计算剩余时间
        elapsed = datetime.now(timezone.utc) - locked_at
        remaining = timedelta(minutes=self.timeout_minutes) - elapsed

        return {
            "project_id": project_id,
            "locked_by": project.locked_by,
            "locked_at": locked_at.isoformat(),
            "elapsed_seconds": int(elapsed.total_seconds()),
            "remaining_seconds": max(0, int(remaining.total_seconds())),
            "timeout_minutes": self.timeout_minutes,
        }

    def cleanup_expired_locks(self, session: Session) -> int:
        """
        清理所有过期的锁

        Args:
            session: 数据库会话

        Returns:
            清理的锁数量
        """
        expired_time = datetime.now(timezone.utc) - timedelta(
            minutes=self.timeout_minutes
        )

        expired_projects = (
            session.query(Project)
            .filter(Project.locked_by.isnot(None), Project.locked_at < expired_time)
            .all()
        )

        count = 0
        for project in expired_projects:
            logger.info(f"清理过期锁: {project.id} by {project.locked_by}")
            project.locked_by = None
            project.locked_at = None
            count += 1

        if count > 0:
            session.commit()

        return count

    def _is_lock_expired(self, locked_at: Optional[datetime]) -> bool:
        """
        检查锁是否超时

        Args:
            locked_at: 锁定时间

        Returns:
            True: 已超时
            False: 未超时
        """
        if not locked_at:
            return True

        # 确保 locked_at 是 timezone-aware datetime
        if locked_at.tzinfo is None:
            locked_at = locked_at.replace(tzinfo=timezone.utc)

        elapsed = datetime.now(timezone.utc) - locked_at
        return elapsed.total_seconds() > (self.timeout_minutes * 60)
