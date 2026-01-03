# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""状态快照管理器"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.db.models import ChainState, Event, Requirement

logger = logging.getLogger(__name__)


class SnapshotManager:
    """状态快照管理器"""

    def create_snapshot(
        self, session: Session, project_id: str, session_id: str
    ) -> str:
        """
        创建状态快照

        Args:
            session: 数据库会话
            project_id: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            快照 ID（事件 ID）
        """
        logger.info(f"创建快照: {project_id}")

        # 获取所有需求
        requirements = session.query(Requirement).filter_by(project_id=project_id).all()

        # 获取链化状态
        chain_state = session.query(ChainState).filter_by(project_id=project_id).first()

        # 构建快照数据
        snapshot_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requirements": {
                req.id: {
                    "status": req.status,
                    "chain_order": req.chain_order,
                    "next_requirement_id": req.next_requirement_id,
                    "dependencies": req.dependencies,
                }
                for req in requirements
            },
            "chain_state": (
                {
                    "status": chain_state.status if chain_state else None,
                    "chain_head_id": chain_state.chain_head_id if chain_state else None,
                    "current_node_id": chain_state.current_node_id
                    if chain_state
                    else None,
                    "total_nodes": chain_state.total_nodes if chain_state else 0,
                    "completed_nodes": chain_state.completed_nodes
                    if chain_state
                    else 0,
                    "progress_percentage": chain_state.progress_percentage
                    if chain_state
                    else 0,
                }
                if chain_state
                else None
            ),
        }

        # 保存快照到事件表
        self._log_event(
            session,
            project_id,
            "SnapshotCreated",
            project_id,
            snapshot_data,
            session_id=session_id,
        )

        # 获取刚创建的事件
        event = (
            session.query(Event)
            .filter_by(project_id=project_id, event_type="SnapshotCreated")
            .order_by(Event.created_at.desc())
            .first()
        )

        if event is None:
            raise RuntimeError("Failed to create snapshot event")

        logger.info(f"快照创建成功: {event.id}")

        return event.id

    def restore_snapshot(
        self, session: Session, snapshot_id: str, session_id: str
    ) -> Dict[str, Any]:
        """
        从快照恢复

        Args:
            session: 数据库会话
            snapshot_id: 快照 ID（事件 ID）
            session_id: 会话 ID（用于权限验证）

        Returns:
            恢复结果
        """
        logger.info(f"从快照恢复: {snapshot_id}")

        # 获取快照事件
        snapshot_event = session.query(Event).filter_by(id=snapshot_id).first()

        if not snapshot_event:
            raise ValueError(f"快照不存在: {snapshot_id}")

        if snapshot_event.event_type != "SnapshotCreated":
            raise ValueError(f"事件类型不是快照: {snapshot_event.event_type}")

        # 验证权限：快照必须属于当前会话创建的
        if (
            snapshot_event.event_metadata
            and "session_id" in snapshot_event.event_metadata
        ):
            snapshot_session_id = snapshot_event.event_metadata["session_id"]
            if snapshot_session_id != session_id:
                logger.warning(
                    f"权限拒绝: 会话 {session_id} 尝试恢复会话 {snapshot_session_id} 创建的快照"
                )
                raise ValueError("无权恢复此快照")

        snapshot_data = snapshot_event.payload
        project_id = snapshot_event.project_id

        # 获取快照中的需求 ID 集合
        snapshot_req_ids = set(snapshot_data.get("requirements", {}).keys())

        # 获取当前所有需求
        current_requirements = (
            session.query(Requirement).filter_by(project_id=project_id).all()
        )

        # 删除快照后创建的需求（不在快照中的需求）
        deleted_count = 0
        for current_req in current_requirements:
            if current_req.id not in snapshot_req_ids:
                logger.info(f"删除快照后创建的需求: {current_req.id}")
                session.delete(current_req)
                deleted_count += 1

        # 恢复需求状态（使用批量查询优化）
        req_data = snapshot_data.get("requirements", {})
        restored_count = 0
        missing_count = 0

        # 分批处理需求恢复
        req_ids = list(req_data.keys())
        batch_size = 100  # 每批处理 100 个需求

        for i in range(0, len(req_ids), batch_size):
            batch_ids = req_ids[i : i + batch_size]

            # 批量查询需求
            batch_reqs = (
                session.query(Requirement).filter(Requirement.id.in_(batch_ids)).all()
            )

            # 构建需求映射
            req_map = {req.id: req for req in batch_reqs}

            # 更新需求状态
            for req_id in batch_ids:
                state = req_data[req_id]
                req = req_map.get(req_id)
                if req is not None:
                    req.status = state["status"]
                    req.chain_order = state.get("chain_order")
                    req.next_requirement_id = state.get("next_requirement_id")
                    req.dependencies = state.get("dependencies", [])
                    restored_count += 1
                else:
                    missing_count += 1
                    logger.warning(f"快照中的需求在数据库中不存在: {req_id}")

            # 每批提交一次
            session.commit()

        if missing_count > 0:
            logger.warning(f"快照恢复警告: {missing_count} 个需求在数据库中不存在")

        # 恢复链化状态
        chain_data = snapshot_data.get("chain_state")
        if chain_data:
            chain_state = (
                session.query(ChainState).filter_by(project_id=project_id).first()
            )

            if chain_state is not None:
                chain_state.status = chain_data["status"]
                chain_state.chain_head_id = chain_data.get("chain_head_id")
                chain_state.current_node_id = chain_data.get("current_node_id")
                chain_state.total_nodes = chain_data.get("total_nodes", 0)
                chain_state.completed_nodes = chain_data.get("completed_nodes", 0)
                chain_state.progress_percentage = chain_data.get(
                    "progress_percentage", 0
                )
                # 递增链版本以确保一致性
                chain_state.chain_version = (chain_state.chain_version or 0) + 1
            else:
                logger.warning(f"项目中不存在链化状态: {project_id}")

        # 记录恢复事件
        self._log_event(
            session,
            project_id,
            "SnapshotRestored",
            project_id,
            {
                "snapshot_id": snapshot_id,
                "restored_count": restored_count,
                "deleted_count": deleted_count,
                "missing_count": missing_count,
            },
        )

        session.commit()

        logger.info(
            f"快照恢复成功: {snapshot_id}, 恢复 {restored_count} 个需求, 删除 {deleted_count} 个"
        )

        return {
            "snapshot_id": snapshot_id,
            "restored_count": restored_count,
            "deleted_count": deleted_count,
            "missing_count": missing_count,
            "message": "快照恢复成功",
        }

    def get_latest_snapshot(
        self, session: Session, project_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新的快照

        Args:
            session: 数据库会话
            project_id: 项目 ID

        Returns:
            快照数据，如果没有快照则返回 None
        """
        snapshot_event = (
            session.query(Event)
            .filter_by(project_id=project_id, event_type="SnapshotCreated")
            .order_by(Event.created_at.desc())
            .first()
        )

        if not snapshot_event:
            return None

        return {
            "snapshot_id": snapshot_event.id,
            "created_at": snapshot_event.created_at.isoformat(),
            "data": snapshot_event.payload,
        }

    def list_snapshots(
        self, session: Session, project_id: str, limit: int = 10
    ) -> list:
        """
        列出项目的所有快照

        Args:
            session: 数据库会话
            project_id: 项目 ID
            limit: 返回数量限制

        Returns:
            快照列表
        """
        snapshots = (
            session.query(Event)
            .filter_by(project_id=project_id, event_type="SnapshotCreated")
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "snapshot_id": s.id,
                "created_at": s.created_at.isoformat(),
                "sequence": s.sequence,
            }
            for s in snapshots
        ]

    def delete_snapshot(self, session: Session, snapshot_id: str) -> bool:
        """
        删除快照

        Args:
            session: 数据库会话
            snapshot_id: 快照 ID

        Returns:
            是否删除成功
        """
        snapshot_event = (
            session.query(Event)
            .filter_by(id=snapshot_id, event_type="SnapshotCreated")
            .first()
        )

        if not snapshot_event:
            return False

        session.delete(snapshot_event)
        session.commit()

        logger.info(f"快照删除成功: {snapshot_id}")

        return True

    def _log_event(
        self,
        session: Session,
        project_id: str,
        event_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
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
            session_id: 会话 ID（用于审计追踪）
        """
        # 获取当前序列号
        last_event = (
            session.query(Event)
            .filter_by(project_id=project_id)
            .order_by(Event.sequence.desc())
            .first()
        )

        sequence = (last_event.sequence + 1) if last_event else 1

        # 增强元数据
        enhanced_metadata = metadata or {}
        if session_id:
            enhanced_metadata["session_id"] = session_id

        event = Event(
            project_id=project_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=payload,
            event_metadata=enhanced_metadata,
            sequence=sequence,
        )
        session.add(event)
