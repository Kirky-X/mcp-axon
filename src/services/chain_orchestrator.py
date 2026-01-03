# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""链化编排器服务"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.db.models import (
    ChainState,
    ChainStatus,
    Event,
    Project,
    ProjectStatus,
    Requirement,
)
from src.services.chain_builder import ChainBuilder
from src.utils.snapshot_manager import SnapshotManager

logger = logging.getLogger(__name__)


class ChainOrchestrator:
    """链化编排器"""

    def __init__(self):
        """初始化链化编排器"""
        self.chain_builder = ChainBuilder()
        self.snapshot_manager = SnapshotManager()

    def should_trigger_chaining(self, session: Session, project_id: str) -> bool:
        """
        检查是否应该触发链化

        触发条件:
        1. 项目状态为 DECOMPOSING
        2. 所有叶子节点（没有子节点的需求）都已添加验证

        Args:
            session: 数据库会话
            project_id: 项目 ID

        Returns:
            是否应该触发链化
        """
        # 获取项目
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        # 检查项目状态
        if project.status != ProjectStatus.DECOMPOSING.value:
            return False

        # 获取所有需求
        all_requirements = (
            session.query(Requirement).filter_by(project_id=project_id).all()
        )

        if not all_requirements:
            return False

        # 找出所有叶子节点（没有子节点的需求）
        # 使用单一查询统计所有父需求，避免 N+1 问题
        from sqlalchemy import func

        parent_counts = (
            session.query(Requirement.parent_id, func.count(Requirement.id))
            .filter(
                Requirement.project_id == project_id, Requirement.parent_id.isnot(None)
            )
            .group_by(Requirement.parent_id)
            .all()
        )
        parent_count_dict = {pid: count for pid, count in parent_counts}

        leaf_requirements = [
            req for req in all_requirements if req.id not in parent_count_dict
        ]

        if not leaf_requirements:
            return False

        # 检查是否有叶子节点已添加验证（放宽条件）
        from src.db.models import ValidationNode

        for leaf in leaf_requirements:
            validation = (
                session.query(ValidationNode).filter_by(requirement_id=leaf.id).first()
            )

            if validation:
                return True  # 至少有一个叶子节点已验证

        return False

    def trigger_chaining(
        self, session: Session, project_id: str, session_id: str
    ) -> Dict[str, Any]:
        """
        触发链化

        Args:
            session: 数据库会话
            project_id: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            链化结果
        """
        logger.info(f"触发链化: {project_id}")

        # 检查是否应该触发链化
        if not self.should_trigger_chaining(session, project_id):
            return {"status": "not_ready", "message": "项目未准备好链化"}

        # 更新项目状态
        project = session.query(Project).filter_by(id=project_id).first()
        if project is None:
            raise ValueError(f"项目不存在: {project_id}")
        project.status = ProjectStatus.CHAINING.value

        # 创建快照（用于回滚）
        snapshot_id = self.snapshot_manager.create_snapshot(
            session, project_id, session_id
        )

        try:
            # 构建链
            result = self.chain_builder.build_chain(session, project_id)

            # 如果链化完成，更新项目状态
            if result["status"] == "completed":
                project.status = ProjectStatus.READY.value

            # 记录事件
            self._log_event(
                session,
                project_id,
                "ChainingTriggered",
                project_id,
                {"snapshot_id": snapshot_id, "result": result},
            )

            session.commit()

            logger.info(f"链化触发成功: {project_id}")

            return result

        except Exception as e:
            # 链化失败，回滚到快照
            logger.error(f"链化失败，回滚到快照: {e}")
            self.snapshot_manager.restore_snapshot(session, snapshot_id, session_id)

            # 更新项目状态
            project.status = ProjectStatus.DECOMPOSING.value

            session.commit()

            raise

    def resolve_parallel_order(
        self,
        session: Session,
        project_id: str,
        parallel_nodes: list,
        sorted_order: list,
    ) -> Dict[str, Any]:
        """
        应用并行节点排序

        Args:
            session: 数据库会话
            project_id: 项目 ID
            parallel_nodes: 并行节点列表
            sorted_order: 排序后的节点列表

        Returns:
            链化结果
        """
        logger.info(f"应用并行节点排序: {project_id}")

        # 验证排序一致性
        if set(parallel_nodes) != set(sorted_order):
            raise ValueError("排序后的节点必须与并行节点一致")

        # 使用指定顺序构建链
        result = self.chain_builder.build_chain_with_order(
            session, project_id, sorted_order
        )

        # 如果链化完成，更新项目状态
        if result["status"] == "completed":
            project = session.query(Project).filter_by(id=project_id).first()
            if project is not None:
                project.status = ProjectStatus.READY.value

        # 记录事件
        self._log_event(
            session,
            project_id,
            "ParallelOrderResolved",
            project_id,
            {"parallel_nodes": parallel_nodes, "sorted_order": sorted_order},
        )

        session.commit()

        logger.info(f"并行节点排序应用成功: {project_id}")

        return result

    def get_next_requirement(
        self, session: Session, project_id: str, session_id: str
    ) -> Dict[str, Any]:
        """
        获取下一个需求

        Args:
            session: 数据库会话
            project_id: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            下一个需求信息
        """
        # 获取链化状态
        chain_state = session.query(ChainState).filter_by(project_id=project_id).first()

        if chain_state is None:
            # 链化状态未初始化，尝试触发链化
            if self.should_trigger_chaining(session, project_id):
                chain_result = self.trigger_chaining(session, project_id, session_id)
                # 如果链化完成，重新获取链化状态
                if chain_result.get("status") == "completed":
                    chain_state = (
                        session.query(ChainState)
                        .filter_by(project_id=project_id)
                        .first()
                    )
                    if chain_state is None:
                        raise ValueError("链化状态获取失败")
                else:
                    return chain_result
            else:
                raise ValueError(
                    "项目未准备好链化。请确保至少有一个叶子节点已添加验证。"
                )

        # 检查链化是否完成
        if chain_state.status == ChainStatus.IDLE.value:
            # 链化未开始，尝试触发链化
            if self.should_trigger_chaining(session, project_id):
                chain_result = self.trigger_chaining(session, project_id, session_id)
                if chain_result.get("status") == "completed":
                    # 重新获取链化状态
                    session.refresh(chain_state)
                else:
                    return chain_result
            else:
                raise ValueError(
                    "项目未准备好链化。请确保至少有一个叶子节点已添加验证。"
                )

        if chain_state.status != ChainStatus.COMPLETED.value:
            raise ValueError(f"链化未完成: {chain_state.status}")

        # 获取当前节点
        current_node_id = chain_state.current_node_id

        if not current_node_id:
            # 链已完成
            return {
                "requirement_id": None,
                "content": None,
                "status": None,
                "chain_order": None,
                "is_last": True,
                "progress_percentage": 100,
                "message": "所有需求已完成",
            }

        # 获取当前需求
        current_req = session.query(Requirement).filter_by(id=current_node_id).first()

        if not current_req:
            raise ValueError(f"当前需求不存在: {current_node_id}")

        # 获取项目
        project = session.query(Project).filter_by(id=project_id).first()

        # 更新项目状态为 EXECUTING
        if project is not None and project.status == ProjectStatus.READY.value:
            project.status = ProjectStatus.EXECUTING.value

        # 计算进度
        progress = (
            int((chain_state.completed_nodes / chain_state.total_nodes) * 100)
            if chain_state.total_nodes > 0
            else 0
        )

        # 检查是否为最后一个节点
        is_last = current_req.next_requirement_id is None

        result = {
            "requirement_id": current_req.id,
            "content": current_req.content,
            "status": current_req.status,
            "chain_order": current_req.chain_order,
            "is_last": is_last,
            "progress_percentage": progress,
            "message": None,
        }

        # 记录事件
        self._log_event(
            session,
            project_id,
            "NextRequirementRetrieved",
            project_id,
            {
                "requirement_id": current_node_id,
                "chain_order": current_req.chain_order,
                "is_last": is_last,
            },
        )

        session.commit()

        return result

    def mark_requirement_completed(
        self, session: Session, project_id: str, requirement_id: str
    ) -> Dict[str, Any]:
        """
        标记需求为已完成

        Args:
            session: 数据库会话
            project_id: 项目 ID
            requirement_id: 需求 ID

        Returns:
            操作结果
        """
        # 获取需求
        requirement = (
            session.query(Requirement)
            .filter_by(id=requirement_id, project_id=project_id)
            .first()
        )

        if not requirement:
            raise ValueError(f"需求不存在: {requirement_id}")

        # 获取链化状态
        chain_state = session.query(ChainState).filter_by(project_id=project_id).first()

        if not chain_state:
            raise ValueError(f"项目未链化: {project_id}")

        # 获取下一个需求 ID
        next_req_id = requirement.next_requirement_id

        # 更新链化状态
        chain_state.current_node_id = next_req_id
        chain_state.completed_nodes += 1
        chain_state.progress_percentage = (
            int((chain_state.completed_nodes / chain_state.total_nodes) * 100)
            if chain_state.total_nodes > 0
            else 100
        )

        # 检查是否所有需求都已完成
        if next_req_id is None:
            # 所有需求完成
            project = session.query(Project).filter_by(id=project_id).first()
            if project is not None:
                project.status = ProjectStatus.COMPLETED.value

                # 记录事件
                self._log_event(
                    session,
                    project_id,
                    "ProjectCompleted",
                    project_id,
                    {
                        "total_nodes": chain_state.total_nodes,
                        "completed_nodes": chain_state.completed_nodes,
                    },
                )

            message = "项目已完成"
        else:
            message = f"需求已完成，下一个需求: {next_req_id}"

        # 记录事件
        self._log_event(
            session,
            project_id,
            "RequirementCompleted",
            requirement_id,
            {
                "requirement_id": requirement_id,
                "next_requirement_id": next_req_id,
                "completed_nodes": chain_state.completed_nodes,
                "total_nodes": chain_state.total_nodes,
            },
        )

        session.commit()

        logger.info(f"需求完成: {requirement_id}, 下一个: {next_req_id}")

        return {
            "requirement_id": requirement_id,
            "next_requirement_id": next_req_id,
            "completed_nodes": chain_state.completed_nodes,
            "total_nodes": chain_state.total_nodes,
            "progress_percentage": chain_state.progress_percentage,
            "message": message,
        }

    def _log_event(
        self,
        session: Session,
        project_id: str,
        event_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        记录事件

        Args:
            session: 数据库会话
            project_id: 项目 ID
            event_type: 事件类型
            aggregate_id: 聚合根 ID
            payload: 事件负载
            metadata: 元数据
        """
        # 获取当前序列号
        last_event = (
            session.query(Event)
            .filter_by(project_id=project_id)
            .order_by(Event.sequence.desc())
            .first()
        )

        sequence = (last_event.sequence + 1) if last_event else 1

        event = Event(
            project_id=project_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=payload,
            event_metadata=metadata,
            sequence=sequence,
        )
        session.add(event)
