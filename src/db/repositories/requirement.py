# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求 Repository - 需求数据访问层"""

import logging
from typing import Any, Dict, List, Optional

from src.db.graph_models import RequirementNode
from src.db.graph_queries import (
    CREATE_HAS_CHILD,
    CREATE_HAS_REQUIREMENT,
    CREATE_REQUIREMENT,
    DELETE_REQUIREMENT,
    GET_CHILDREN,
    GET_INCOMING_DEPENDENCIES_DETAILS,
    GET_REQUIREMENT_BY_UUID,
    GET_REQUIREMENT_CHAIN_INFO,
    GET_REQUIREMENTS_BY_PARENT,
    GET_REQUIREMENTS_BY_PROJECT,
    GET_REQUIREMENTS_BY_STATUS,
    GET_ROOT_REQUIREMENTS,
    UPDATE_REQUIREMENT,
    UPDATE_REQUIREMENT_STATUS,
)
from src.db.repositories.base import BaseRepository
from src.db.graph_models import now_utc

logger = logging.getLogger(__name__)


class RequirementRepository(BaseRepository):
    """需求 Repository

    封装所有需求相关的数据库操作。
    """

    # 查询结果列名映射
    REQUIREMENT_COLUMNS = [
        "uuid",
        "project_uuid",
        "parent_uuid",
        "content",
        "decompose_reason",
        "status",
        "level",
        "order_in_parent",
        "chain_order",
        "created_at",
        "updated_at",
        "version",
        "dependencies",
    ]

    def find_by_uuid(self, uuid: str) -> Optional[RequirementNode]:
        """按 UUID 查找需求

        Args:
            uuid: 需求 ID

        Returns:
            RequirementNode 对象，如果不存在返回 None
        """
        row = self.execute_single(GET_REQUIREMENT_BY_UUID, {"uuid": uuid})
        if not row:
            return None
        return self._row_to_requirement(row)

    def find_by_project(
        self,
        project_uuid: str,
        status: Optional[str] = None,
        parent_uuid: Optional[str] = None,
    ) -> List[RequirementNode]:
        """查询项目需求列表

        Args:
            project_uuid: 项目 ID
            status: 状态过滤（可选）
            parent_uuid: 父需求 ID 过滤（可选）

        Returns:
            需求列表
        """
        if parent_uuid:
            rows = self.execute_query(
                GET_REQUIREMENTS_BY_PARENT, {"parent_uuid": parent_uuid}
            )
        elif status:
            rows = self.execute_query(
                GET_REQUIREMENTS_BY_STATUS,
                {"project_uuid": project_uuid, "status": status},
            )
        else:
            rows = self.execute_query(
                GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_uuid}
            )
        return [self._row_to_requirement(row) for row in rows]

    def find_children(self, parent_uuid: str) -> List[RequirementNode]:
        """查询子需求

        Args:
            parent_uuid: 父需求 ID

        Returns:
            子需求列表
        """
        rows = self.execute_query(GET_CHILDREN, {"parent_uuid": parent_uuid})
        return [self._row_to_requirement(row) for row in rows]

    def find_root_requirements(self, project_uuid: str) -> List[RequirementNode]:
        """查询根需求

        Args:
            project_uuid: 项目 ID

        Returns:
            根需求列表
        """
        rows = self.execute_query(GET_ROOT_REQUIREMENTS, {"project_uuid": project_uuid})
        return [self._row_to_requirement(row) for row in rows]

    def save(self, requirement: RequirementNode, create_edges: bool = True) -> bool:
        """保存需求（创建）

        Args:
            requirement: 需求对象
            create_edges: 是否创建关系边

        Returns:
            是否成功
        """
        # 创建节点
        params = requirement.to_cypher_params()
        result = self.execute_single(CREATE_REQUIREMENT, params)
        if not result:
            return False

        # 创建边
        if create_edges:
            self.execute_write(
                CREATE_HAS_REQUIREMENT,
                {
                    "project_uuid": requirement.project_uuid,
                    "requirement_uuid": requirement.uuid,
                },
            )
            if requirement.parent_uuid:
                self.execute_write(
                    CREATE_HAS_CHILD,
                    {
                        "parent_uuid": requirement.parent_uuid,
                        "child_uuid": requirement.uuid,
                        "order": requirement.order_in_parent,
                    },
                )

        return True

    def update(
        self,
        uuid: str,
        content: Optional[str] = None,
        decompose_reason: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        """更新需求

        Args:
            uuid: 需求 ID
            content: 内容
            decompose_reason: 分解原因
            status: 状态

        Returns:
            是否成功
        """
        params = {
            "uuid": uuid,
            "content": content or "",
            "decompose_reason": decompose_reason or "",
            "status": status or "",
            "updated_at": now_utc(),
        }
        return self.execute_write(UPDATE_REQUIREMENT, params)

    def update_status(self, uuid: str, status: str) -> bool:
        """更新需求状态

        Args:
            uuid: 需求 ID
            status: 新状态

        Returns:
            是否成功
        """
        return self.execute_write(
            UPDATE_REQUIREMENT_STATUS,
            {"uuid": uuid, "status": status, "updated_at": now_utc()},
        )

    def delete(self, uuid: str) -> bool:
        """删除需求（硬删除）

        Args:
            uuid: 需求 ID

        Returns:
            是否成功
        """
        return self.execute_write(DELETE_REQUIREMENT, {"uuid": uuid})

    def check_incoming_dependencies(self, uuid: str) -> List[Dict[str, str]]:
        """检查入边依赖

        Args:
            uuid: 需求 ID

        Returns:
            依赖此需求的需求数据列表
        """
        rows = self.execute_query(
            GET_INCOMING_DEPENDENCIES_DETAILS, {"requirement_uuid": uuid}
        )
        return [{"uuid": row[0], "content": row[1], "status": row[2]} for row in rows]  # type: ignore[index]

    def check_chain_position(self, uuid: str) -> Optional[Dict[str, Any]]:
        """检查需求是否在执行链中

        Args:
            uuid: 需求 ID

        Returns:
            链信息字典，不在链中时返回 None
        """
        row = self.execute_single(
            GET_REQUIREMENT_CHAIN_INFO, {"requirement_uuid": uuid}
        )
        if not row:
            return None

        chain_order = row[0]  # type: ignore[index]
        prev_uuid = row[1]  # type: ignore[index]
        next_uuid = row[2]  # type: ignore[index]

        if chain_order is not None and chain_order >= 0:
            return {
                "chain_order": chain_order,
                "prev_uuid": prev_uuid,
                "next_uuid": next_uuid,
            }

        if prev_uuid or next_uuid:
            return {
                "chain_order": chain_order,
                "prev_uuid": prev_uuid,
                "next_uuid": next_uuid,
            }

        return None

    def count_children(self, parent_uuid: str) -> int:
        """统计子需求数量

        Args:
            parent_uuid: 父需求 ID

        Returns:
            子需求数量
        """
        rows = self.execute_query(GET_CHILDREN, {"parent_uuid": parent_uuid})
        return len(rows)

    def _row_to_requirement(self, row: Any) -> RequirementNode:
        """将查询行转换为 RequirementNode 对象

        Args:
            row: 查询结果行

        Returns:
            RequirementNode 对象
        """
        # 处理依赖列表
        dependencies = row[12] if len(row) > 12 and row[12] else []

        return RequirementNode(
            uuid=row[0],
            project_uuid=row[1],
            parent_uuid=row[2] if row[2] else None,
            content=row[3],
            decompose_reason=row[4] if row[4] else None,
            status=row[5],
            level=row[6],
            order_in_parent=row[7],
            chain_order=row[8] if row[8] != -1 else None,
            created_at=row[9],
            updated_at=row[10],
            version=row[11] if len(row) > 11 else 1,
            dependencies=dependencies,
        )
