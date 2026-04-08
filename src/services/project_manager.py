# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""项目管理服务"""

import logging
import uuid
from typing import Any, Dict

import real_ladybug as lb

from src.db.graph_models import ProjectStatus, RequirementStatus, now_utc
from src.db.graph_queries import (
    COUNT_ALL_REQUIREMENTS,
    COUNT_REQUIREMENTS_BY_STATUS,
    CREATE_CHAIN_STATE,
    CREATE_HAS_CHAIN_STATE,
    CREATE_PROJECT,
    GET_CHAIN_STATE_BY_PROJECT,
    GET_PROJECT_BY_UUID,
    UPDATE_PROJECT,
    UPDATE_PROJECT_STATUS,
)
from src.schemas import ProjectUpdate
from src.utils.cache import CacheManager
from src.utils.event_logger import log_event
from src.utils.metrics import performance_monitor

logger = logging.getLogger(__name__)


class ProjectManager:
    """项目管理服务"""

    def __init__(self, cache: CacheManager):
        """
        初始化项目管理器

        Args:
            cache: 缓存管理器实例
        """
        self.cache = cache

    @performance_monitor("create_project")
    def create_project(
        self, conn: lb.Connection, name: str, description: str = ""
    ) -> Dict[str, Any]:
        """
        创建项目

        Args:
            conn: 数据库连接
            name: 项目名称
            description: 项目描述

        Returns:
            项目信息字典
        """
        # 创建项目
        project_uuid = str(uuid.uuid4())
        created_at = now_utc()

        conn.execute(
            CREATE_PROJECT,
            {
                "uuid": project_uuid,
                "name": name,
                "description": description,
                "status": ProjectStatus.CREATED.value,
                "locked_by": "",
                "locked_at": "",
                "created_at": created_at,
                "updated_at": created_at,
            },
        )

        # 创建链化状态
        chain_state_uuid = str(uuid.uuid4())
        conn.execute(
            CREATE_CHAIN_STATE,
            {
                "uuid": chain_state_uuid,
                "project_uuid": project_uuid,
                "status": "IDLE",
                "chain_head_uuid": "",
                "current_node_uuid": "",
                "total_nodes": 0,
                "completed_nodes": 0,
                "progress_percentage": 0,
                "last_chained_at": "",
                "chain_version": 1,
                "created_at": created_at,
                "updated_at": created_at,
            },
        )

        # 创建 HAS_CHAIN_STATE 边
        conn.execute(
            CREATE_HAS_CHAIN_STATE,
            {"project_uuid": project_uuid, "chain_state_uuid": chain_state_uuid},
        )

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "ProjectCreated",
            project_uuid,
            {"name": name, "description": description},
        )

        result = {
            "project_id": project_uuid,
            "name": name,
            "description": description,
            "status": ProjectStatus.CREATED.value,
            "created_at": created_at,
        }

        # 将新创建的项目添加到缓存
        self.cache.set_project(project_uuid, result)

        logger.info(f"项目创建成功: {project_uuid} - {name}")

        return result

    @performance_monitor("update_project")
    def update_project(
        self, conn: lb.Connection, project_uuid: str, update_data: ProjectUpdate
    ) -> Dict[str, Any]:
        """
        更新项目信息

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            update_data: 更新数据

        Returns:
            更新后的项目信息
        """
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(
                f"项目不存在（ID: {project_uuid}）。请检查项目 ID 是否正确，或先创建项目。"
            )

        project = rows[0]
        current_name = project[1]
        current_description = project[2]
        current_status = project[3]

        # 准备更新参数
        new_name = update_data.name if update_data.name is not None else current_name
        new_description = (
            update_data.description
            if update_data.description is not None
            else current_description
        )

        # 更新字段
        if update_data.name is not None:
            old_name = current_name
            log_event(
                conn,
                project_uuid,
                "ProjectNameChanged",
                project_uuid,
                {"old_name": old_name, "new_name": update_data.name},
            )

        # 执行更新
        conn.execute(
            UPDATE_PROJECT,
            {
                "uuid": project_uuid,
                "name": new_name,
                "description": new_description,
                "status": current_status,
                "updated_at": now_utc(),
            },
        )

        # 使项目缓存失效
        self.cache.invalidate_project(project_uuid)

        logger.info(f"项目更新成功: {project_uuid}")

        return {
            "project_id": project_uuid,
            "name": new_name,
            "description": new_description,
            "status": current_status,
            "updated_at": now_utc(),
        }

    @performance_monitor("get_project")
    def get_project(self, conn: lb.Connection, project_uuid: str) -> Dict[str, Any]:
        """
        获取项目信息

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID

        Returns:
            项目信息字典
        """
        # 尝试从缓存获取
        cached_project = self.cache.get_project(project_uuid)
        if cached_project:
            logger.debug(f"从缓存获取项目: {project_uuid}")
            return cached_project

        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"项目不存在: {project_uuid}")

        row = rows[0]
        project_result = {
            "project_id": row[0],
            "name": row[1],
            "description": row[2] if row[2] else None,
            "status": row[3],
            "locked_by": row[4] if row[4] else None,
            "locked_at": row[5] if row[5] else None,
            "created_at": row[6],
            "updated_at": row[7],
        }

        # 将结果存入缓存
        self.cache.set_project(project_uuid, project_result)

        return project_result

    def get_project_state(
        self, conn: lb.Connection, project_uuid: str
    ) -> Dict[str, Any]:
        """
        获取项目状态

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID

        Returns:
            项目状态信息
        """
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"项目不存在: {project_uuid}")

        project = rows[0]

        # 获取链化状态
        chain_result = conn.execute(
            GET_CHAIN_STATE_BY_PROJECT, {"project_uuid": project_uuid}
        )
        chain_rows = list(chain_result)
        chain_state = chain_rows[0] if chain_rows else None

        # 统计各状态需求数量
        total_result = conn.execute(
            COUNT_ALL_REQUIREMENTS, {"project_uuid": project_uuid}
        )
        total_rows = list(total_result)
        total_requirements = total_rows[0][0] if total_rows else 0

        # 按状态统计
        status_result = conn.execute(
            COUNT_REQUIREMENTS_BY_STATUS, {"project_uuid": project_uuid}
        )
        status_counts = {row[0]: row[1] for row in status_result}

        leaf_requirements = status_counts.get(RequirementStatus.LEAF.value, 0)
        validated_requirements = status_counts.get(RequirementStatus.VALIDATED.value, 0)
        chained_requirements = status_counts.get(RequirementStatus.CHAINED.value, 0)

        return {
            "project_id": project[0],
            "name": project[1],
            "status": project[3],
            "total_requirements": total_requirements,
            "leaf_requirements": leaf_requirements,
            "validated_requirements": validated_requirements,
            "chained_requirements": chained_requirements,
            "chain_status": chain_state[2] if chain_state else None,  # status
            "current_node_id": chain_state[4]
            if chain_state
            else None,  # current_node_uuid
            "progress_percentage": chain_state[8]
            if chain_state
            else 0,  # progress_percentage
            "created_at": project[6],
            "updated_at": project[7],
        }

    def update_project_status(
        self, conn: lb.Connection, project_uuid: str, status: ProjectStatus
    ):
        """
        更新项目状态

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            status: 新状态
        """
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"项目不存在: {project_uuid}")

        old_status = rows[0][3]  # status

        conn.execute(
            UPDATE_PROJECT_STATUS,
            {
                "uuid": project_uuid,
                "status": status.value,
                "updated_at": now_utc(),
            },
        )

        # 记录状态变更事件
        log_event(
            conn,
            project_uuid,
            "ProjectStatusChanged",
            project_uuid,
            {"old_status": old_status, "new_status": status.value},
        )

        # 使项目缓存失效
        self.cache.invalidate_project(project_uuid)

        logger.info(f"项目状态变更: {project_uuid} {old_status} -> {status.value}")
