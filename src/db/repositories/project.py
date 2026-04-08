# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""项目 Repository - 项目数据访问层"""

import logging
from typing import Any, List, Optional


from src.db.graph_models import ProjectNode, now_utc
from src.db.graph_queries import (
    CREATE_PROJECT,
    DELETE_PROJECT,
    GET_ALL_PROJECTS,
    GET_PROJECT_BY_UUID,
    UPDATE_PROJECT,
    UPDATE_PROJECT_LOCK,
    UPDATE_PROJECT_STATUS,
)
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ProjectRepository(BaseRepository):
    """项目 Repository

    封装所有项目相关的数据库操作。
    """

    def find_by_uuid(self, uuid: str) -> Optional[ProjectNode]:
        """按 UUID 查找项目

        Args:
            uuid: 项目 ID

        Returns:
            ProjectNode 对象，如果不存在返回 None
        """
        row = self.execute_single(GET_PROJECT_BY_UUID, {"uuid": uuid})
        if not row:
            return None
        return self._row_to_project(row)

    def find_all(self) -> List[ProjectNode]:
        """查询所有项目

        Returns:
            项目列表
        """
        rows = self.execute_query(GET_ALL_PROJECTS, {})
        return [self._row_to_project(row) for row in rows]

    def save(self, project: ProjectNode) -> bool:
        """保存项目（创建）

        Args:
            project: 项目对象

        Returns:
            是否成功
        """
        params = project.to_cypher_params()
        result = self.execute_single(CREATE_PROJECT, params)
        return result is not None

    def update(
        self,
        uuid: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        """更新项目

        Args:
            uuid: 项目 ID
            name: 名称
            description: 描述
            status: 状态

        Returns:
            是否成功
        """
        # 获取当前项目信息
        current = self.find_by_uuid(uuid)
        if not current:
            return False

        params = {
            "uuid": uuid,
            "name": name or current.name,
            "description": description
            if description is not None
            else (current.description or ""),
            "status": status or current.status,
            "updated_at": now_utc(),
        }
        return self.execute_write(UPDATE_PROJECT, params)

    def update_status(self, uuid: str, status: str) -> bool:
        """更新项目状态

        Args:
            uuid: 项目 ID
            status: 新状态

        Returns:
            是否成功
        """
        return self.execute_write(
            UPDATE_PROJECT_STATUS,
            {"uuid": uuid, "status": status, "updated_at": now_utc()},
        )

    def update_lock(
        self,
        uuid: str,
        locked_by: Optional[str],
        locked_at: Optional[str] = None,
    ) -> bool:
        """更新项目锁状态

        Args:
            uuid: 项目 ID
            locked_by: 锁定者 ID（None 表示解锁）
            locked_at: 锁定时间

        Returns:
            是否成功
        """
        return self.execute_write(
            UPDATE_PROJECT_LOCK,
            {
                "uuid": uuid,
                "locked_by": locked_by or "",
                "locked_at": locked_at or "",
                "updated_at": now_utc(),
            },
        )

    def delete(self, uuid: str) -> bool:
        """删除项目

        Args:
            uuid: 项目 ID

        Returns:
            是否成功
        """
        return self.execute_write(DELETE_PROJECT, {"uuid": uuid})

    def exists(self, uuid: str) -> bool:
        """检查项目是否存在

        Args:
            uuid: 项目 ID

        Returns:
            是否存在
        """
        return self.find_by_uuid(uuid) is not None

    def _row_to_project(self, row: Any) -> ProjectNode:
        """将查询行转换为 ProjectNode 对象

        Args:
            row: 查询结果行

        Returns:
            ProjectNode 对象
        """
        return ProjectNode(
            uuid=row[0],
            name=row[1],
            description=row[2] if row[2] else None,
            status=row[3],
            locked_by=row[4] if row[4] else None,
            locked_at=row[5] if row[5] else None,
            created_at=row[6],
            updated_at=row[7],
        )
