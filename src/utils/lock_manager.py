# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""项目锁管理器"""

import logging
from datetime import UTC, datetime, timedelta

import real_ladybug as lb

from src.db.graph_queries import GET_PROJECT_BY_UUID, UPDATE_PROJECT_LOCK
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

    def acquire_lock(
        self, conn: lb.Connection, project_id: str, session_id: str
    ) -> bool:
        """
        获取项目锁（原子操作实现）

        使用 Cypher 的条件更新确保原子性，避免 TOCTOU 竞态条件。

        Args:
            conn: LadybugDB 连接
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            True: 锁获取成功
            False: 锁已被占用
        """
        now = datetime.now(UTC).isoformat()
        timeout_time = (
            datetime.now(UTC) - timedelta(minutes=self.timeout_minutes)
        ).isoformat()

        # 原子操作：只有在锁未被占用或已超时时才更新
        atomic_query = """
        MATCH (p:Project {uuid: $uuid})
        WHERE p.locked_by IS NULL
           OR p.locked_by = $session_id
           OR p.locked_at < $timeout_time
        SET p.locked_by = $session_id,
            p.locked_at = $now,
            p.updated_at = $now
        RETURN p.uuid, p.locked_by
        """

        result = conn.execute(
            atomic_query,
            {
                "uuid": project_id,
                "session_id": session_id,
                "timeout_time": timeout_time,
                "now": now,
            },
        )

        rows = list(result)
        if not rows:
            # 更新失败，说明锁已被其他会话占用且未超时
            # 检查项目是否存在
            check_result = conn.execute(
                "MATCH (p:Project {uuid: $uuid}) RETURN p.uuid",
                {"uuid": project_id},
            )
            if not list(check_result):
                raise ValueError(f"项目不存在: {project_id}")

            logger.warning(f"项目锁已被占用: {project_id}")
            return False

        # 成功获取锁，记录事件
        log_event(
            conn,
            project_id,
            "ProjectLockAcquired",
            project_id,
            {"session_id": session_id, "timeout_minutes": self.timeout_minutes},
        )

        logger.info(f"项目锁获取成功: {project_id} by {session_id}")

        return True

    def release_lock(
        self, conn: lb.Connection, project_id: str, session_id: str
    ) -> bool:
        """
        释放项目锁

        Args:
            conn: LadybugDB 连接
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            True: 释放成功
            False: 锁不属于该会话
        """
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_id})
        rows = list(result)
        if not rows:
            raise ValueError(f"项目不存在: {project_id}")

        project = rows[0]
        locked_by = project[4]  # locked_by 字段

        if locked_by != session_id:
            logger.warning(
                f"尝试释放不属于该会话的锁: {project_id} by {session_id}, locked by {locked_by}"
            )
            return False

        # 释放锁
        now = datetime.now(UTC).isoformat()
        conn.execute(
            UPDATE_PROJECT_LOCK,
            {
                "uuid": project_id,
                "locked_by": None,
                "locked_at": None,
                "updated_at": now,
            },
        )

        # 记录事件
        log_event(
            conn,
            project_id,
            "ProjectLockReleased",
            project_id,
            {"session_id": session_id},
        )

        logger.info(f"项目锁释放成功: {project_id} by {session_id}")

        return True

    def is_locked(self, conn: lb.Connection, project_id: str) -> bool:
        """
        检查项目是否被锁定

        Args:
            conn: LadybugDB 连接
            project_id: 项目 ID

        Returns:
            True: 已锁定
            False: 未锁定
        """
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_id})
        rows = list(result)
        if not rows:
            raise ValueError(f"项目不存在: {project_id}")

        project = rows[0]
        locked_by = project[4]  # locked_by 字段
        locked_at_str = project[5]  # locked_at 字段

        if not locked_by:
            return False

        # 检查锁是否已超时
        locked_at = self._parse_datetime(locked_at_str)
        return not self._is_lock_expired(locked_at)

    def get_lock_info(self, conn: lb.Connection, project_id: str) -> dict | None:
        """
        获取锁信息

        Args:
            conn: LadybugDB 连接
            project_id: 项目 ID

        Returns:
            锁信息字典，如果未锁定则返回 None
        """
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_id})
        rows = list(result)
        if not rows:
            raise ValueError(f"项目不存在: {project_id}")

        project = rows[0]
        locked_by = project[4]  # locked_by 字段
        locked_at_str = project[5]  # locked_at 字段

        if not locked_by:
            return None

        # 检查锁是否已超时
        locked_at = self._parse_datetime(locked_at_str)
        if locked_at is None or self._is_lock_expired(locked_at):
            return None

        # 计算剩余时间
        elapsed = datetime.now(UTC) - locked_at
        remaining = timedelta(minutes=self.timeout_minutes) - elapsed

        return {
            "project_id": project_id,
            "locked_by": locked_by,
            "locked_at": locked_at.isoformat(),
            "elapsed_seconds": int(elapsed.total_seconds()),
            "remaining_seconds": max(0, int(remaining.total_seconds())),
            "timeout_minutes": self.timeout_minutes,
        }

    def cleanup_expired_locks(self, conn: lb.Connection) -> int:
        """
        清理所有过期的锁

        Args:
            conn: LadybugDB 连接

        Returns:
            清理的锁数量
        """
        expired_time = datetime.now(UTC) - timedelta(minutes=self.timeout_minutes)
        expired_time_str = expired_time.isoformat()

        # 查询所有有过期锁的项目
        query = """
        MATCH (p:Project)
        WHERE p.locked_by IS NOT NULL AND p.locked_at < $expired_time
        RETURN p.uuid, p.locked_by
        """
        result = conn.execute(query, {"expired_time": expired_time_str})

        now = datetime.now(UTC).isoformat()
        count = 0
        for row in result:
            project_uuid = row[0]
            locked_by = row[1]
            logger.info(f"清理过期锁: {project_uuid} by {locked_by}")
            conn.execute(
                UPDATE_PROJECT_LOCK,
                {
                    "uuid": project_uuid,
                    "locked_by": None,
                    "locked_at": None,
                    "updated_at": now,
                },
            )
            count += 1

        return count

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """
        解析日期时间字符串

        Args:
            dt_str: 日期时间字符串

        Returns:
            datetime 对象
        """
        if not dt_str:
            return None
        try:
            # ISO 格式解析
            dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            return None

    def _is_lock_expired(self, locked_at: datetime | None) -> bool:
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

        elapsed = datetime.now(UTC) - locked_at
        return elapsed.total_seconds() > (self.timeout_minutes * 60)
