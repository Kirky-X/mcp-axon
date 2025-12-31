# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""项目管理服务"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.db.models import Project, ProjectStatus, Event, ChainState
from src.schemas import ProjectCreate, ProjectUpdate
from src.utils.cache import cache_manager
from src.utils.metrics import performance_monitor
from src.utils.event_logger import log_event

logger = logging.getLogger(__name__)


class ProjectManager:
    """项目管理服务"""

    def __init__(self):
        """初始化项目管理器"""
        self.cache = cache_manager

    @performance_monitor("create_project")
    def create_project(
        self,
        session: Session,
        name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建项目

        Args:
            session: 数据库会话
            name: 项目名称
            description: 项目描述

        Returns:
            项目信息字典
        """
        # 创建项目
        project = Project(
            name=name,
            description=description,
            status=ProjectStatus.CREATED.value
        )
        session.add(project)
        session.flush()

        # 创建链化状态
        chain_state = ChainState(
            project_id=project.id,
            status="IDLE"
        )
        session.add(chain_state)

        # 记录事件
        log_event(
            session,
            project.id,
            "ProjectCreated",
            project.id,
            {
                "name": name,
                "description": description
            }
        )

        session.commit()

        result = {
            "project_id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at.isoformat()
        }
        
        # 将新创建的项目添加到缓存
        self.cache.set_project(project.id, result)

        logger.info(f"项目创建成功: {project.id} - {name}")

        return result

    @performance_monitor("update_project")
    def update_project(
        self,
        session: Session,
        project_id: str,
        update_data: ProjectUpdate
    ) -> Dict[str, Any]:
        """
        更新项目信息

        Args:
            session: 数据库会话
            project_id: 项目 ID
            update_data: 更新数据

        Returns:
            更新后的项目信息
        """
        project = session.query(Project).filter_by(id=project_id).first()

        if not project:
            raise ValueError(f"项目不存在（ID: {project_id}）。请检查项目 ID 是否正确，或先创建项目。")

        # 更新字段
        if update_data.name is not None:
            old_name = project.name
            project.name = update_data.name
            log_event(
                session,
                project_id,
                "ProjectNameChanged",
                project_id,
                {"old_name": old_name, "new_name": update_data.name}
            )

        if update_data.description is not None:
            project.description = update_data.description

        project.updated_at = datetime.now(timezone.utc)
        session.commit()

        # 使项目缓存失效
        self.cache.invalidate_project(project_id)

        logger.info(f"项目更新成功: {project_id}")

        return {
            "project_id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "updated_at": project.updated_at.isoformat()
        }

    @performance_monitor("get_project")
    def get_project(
        self,
        session: Session,
        project_id: str
    ) -> Dict[str, Any]:
        """
        获取项目信息

        Args:
            session: 数据库会话
            project_id: 项目 ID

        Returns:
            项目信息字典
        """
        # 尝试从缓存获取
        cached_project = self.cache.get_project(project_id)
        if cached_project:
            logger.debug(f"从缓存获取项目: {project_id}")
            return cached_project

        project = session.query(Project).filter_by(id=project_id).first()

        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        result = {
            "project_id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "locked_by": project.locked_by,
            "locked_at": project.locked_at.isoformat() if project.locked_at else None,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        }
        
        # 将结果存入缓存
        self.cache.set_project(project_id, result)

        return result

    def get_project_state(
        self,
        session: Session,
        project_id: str
    ) -> Dict[str, Any]:
        """
        获取项目状态

        Args:
            session: 数据库会话
            project_id: 项目 ID

        Returns:
            项目状态信息
        """
        from src.db.models import Requirement, RequirementStatus

        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        chain_state = session.query(ChainState).filter_by(project_id=project_id).first()

        # 使用单次查询统计所有状态的需求数量
        from sqlalchemy import func, case
        
        stats = session.query(
            func.count(Requirement.id).label('total'),
            func.sum(case((Requirement.status == RequirementStatus.LEAF.value, 1), else_=0)).label('leaf'),
            func.sum(case((Requirement.status == RequirementStatus.VALIDATED.value, 1), else_=0)).label('validated'),
            func.sum(case((Requirement.status == RequirementStatus.CHAINED.value, 1), else_=0)).label('chained')
        ).filter(Requirement.project_id == project_id).first()
        
        total_requirements = stats.total or 0
        leaf_requirements = stats.leaf or 0
        validated_requirements = stats.validated or 0
        chained_requirements = stats.chained or 0

        return {
            "project_id": project.id,
            "name": project.name,
            "status": project.status,
            "total_requirements": total_requirements,
            "leaf_requirements": leaf_requirements,
            "validated_requirements": validated_requirements,
            "chained_requirements": chained_requirements,
            "chain_status": chain_state.status if chain_state else None,
            "current_node_id": chain_state.current_node_id if chain_state else None,
            "progress_percentage": chain_state.progress_percentage if chain_state else 0,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        }

    def update_project_status(
        self,
        session: Session,
        project_id: str,
        status: ProjectStatus
    ):
        """
        更新项目状态

        Args:
            session: 数据库会话
            project_id: 项目 ID
            status: 新状态
        """
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        old_status = project.status
        project.status = status.value
        project.updated_at = datetime.now(timezone.utc)

        # 记录状态变更事件
        log_event(
            session,
            project_id,
            "ProjectStatusChanged",
            project_id,
            {
                "old_status": old_status,
                "new_status": status.value
            }
        )

        session.commit()
        
        # 使项目缓存失效
        self.cache.invalidate_project(project_id)

        logger.info(f"项目状态变更: {project_id} {old_status} -> {status.value}")