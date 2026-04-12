# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""链化编排器服务"""

import logging
from typing import Any

import real_ladybug as lb

from src.constants import Chain
from src.db.graph_models import ChainStatus, ProjectStatus, RequirementStatus, now_utc
from src.db.graph_queries import (
    GET_CHAIN_STATE_BY_PROJECT,
    GET_NEXT_IN_CHAIN,
    GET_PROJECT_BY_UUID,
    GET_REQUIREMENT_BY_UUID,
    GET_REQUIREMENTS_BY_PROJECT,
    GET_REQUIREMENTS_BY_STATUS,
    UPDATE_CHAIN_STATE_PROGRESS,
    UPDATE_PROJECT_STATUS,
    UPDATE_REQUIREMENT_STATUS_COMPLETED,
)
from src.services.chain_builder import ChainBuilder
from src.utils.event_logger import log_event
from src.utils.snapshot_manager import SnapshotManager

logger = logging.getLogger(__name__)


# 可重试的异常类型
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


class ChainOrchestrator:
    """链化编排器"""

    def __init__(self, chain_builder: ChainBuilder, snapshot_manager: SnapshotManager):
        """
        初始化链化编排器

        Args:
            chain_builder: 链化构建器实例
            snapshot_manager: 快照管理器实例
        """
        self.chain_builder = chain_builder
        self.snapshot_manager = snapshot_manager

    def should_trigger_chaining(self, conn: lb.Connection, project_uuid: str) -> bool:
        """
        检查是否应该触发链化

        触发条件:
        1. 项目状态为 DECOMPOSING
        2. 所有叶子节点（没有子节点的需求）都已添加验证

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID

        Returns:
            是否应该触发链化
        """
        # 获取项目
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_uuid})
        project_rows = list(result)
        if not project_rows:
            raise ValueError(f"项目不存在: {project_uuid}")

        project = project_rows[0]
        project_status = project[3]  # status

        # 检查项目状态
        if project_status != ProjectStatus.DECOMPOSING.value:
            return False

        # 获取所有需求
        result = conn.execute(
            GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_uuid}
        )
        all_requirements = list(result)

        if not all_requirements:
            return False

        # 获取已验证的需求数量
        result = conn.execute(
            GET_REQUIREMENTS_BY_STATUS,
            {"project_uuid": project_uuid, "status": RequirementStatus.VALIDATED.value},
        )
        validated_requirements = list(result)

        # 至少有一个已验证的需求
        return len(validated_requirements) > 0

    def trigger_chaining(
        self, conn: lb.Connection, project_uuid: str, session_id: str
    ) -> dict[str, Any]:
        """
        触发链化

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            链化结果
        """
        logger.info(f"触发链化: {project_uuid}")

        # 检查是否应该触发链化
        if not self.should_trigger_chaining(conn, project_uuid):
            return {"status": "not_ready", "message": "项目未准备好链化"}

        # 更新项目状态
        conn.execute(
            UPDATE_PROJECT_STATUS,
            {
                "uuid": project_uuid,
                "status": ProjectStatus.CHAINING.value,
                "updated_at": now_utc(),
            },
        )

        # 创建快照（用于回滚）
        snapshot_id = self.snapshot_manager.create_snapshot(
            conn, project_uuid, session_id
        )

        try:
            # 构建链
            result = self.chain_builder.build_chain(conn, project_uuid)

            # 如果链化完成，更新项目状态
            if result["status"] == "completed":
                conn.execute(
                    UPDATE_PROJECT_STATUS,
                    {
                        "uuid": project_uuid,
                        "status": ProjectStatus.READY.value,
                        "updated_at": now_utc(),
                    },
                )

            # 记录事件
            log_event(
                conn,
                project_uuid,
                "ChainingTriggered",
                project_uuid,
                {"snapshot_id": snapshot_id, "result": result},
            )

            logger.info(f"链化触发成功: {project_uuid}")

            return result

        except Exception as e:
            # 链化失败，回滚到快照
            logger.error(f"链化失败，回滚到快照: {e}")
            self.snapshot_manager.restore_snapshot(conn, snapshot_id, session_id)

            # 更新项目状态
            conn.execute(
                UPDATE_PROJECT_STATUS,
                {
                    "uuid": project_uuid,
                    "status": ProjectStatus.DECOMPOSING.value,
                    "updated_at": now_utc(),
                },
            )

            raise

    def resolve_parallel_order(
        self,
        conn: lb.Connection,
        project_uuid: str,
        parallel_nodes: list,
        sorted_order: list,
    ) -> dict[str, Any]:
        """
        应用并行节点排序

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            parallel_nodes: 并行节点列表
            sorted_order: 排序后的节点列表

        Returns:
            链化结果
        """
        logger.info(f"应用并行节点排序: {project_uuid}")

        # 验证排序一致性
        if set(parallel_nodes) != set(sorted_order):
            raise ValueError("排序后的节点必须与并行节点一致")

        # 使用指定顺序构建链
        result = self.chain_builder.build_chain_with_order(
            conn, project_uuid, sorted_order
        )

        # 如果链化完成，更新项目状态
        if result["status"] == "completed":
            conn.execute(
                UPDATE_PROJECT_STATUS,
                {
                    "uuid": project_uuid,
                    "status": ProjectStatus.READY.value,
                    "updated_at": now_utc(),
                },
            )

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "ParallelOrderResolved",
            project_uuid,
            {"parallel_nodes": parallel_nodes, "sorted_order": sorted_order},
        )

        logger.info(f"并行节点排序应用成功: {project_uuid}")

        return result

    def get_next_requirement(
        self, conn: lb.Connection, project_uuid: str, session_id: str
    ) -> dict[str, Any]:
        """
        获取下一个需求

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            下一个需求信息
        """
        # 获取链化状态
        result = conn.execute(
            GET_CHAIN_STATE_BY_PROJECT, {"project_uuid": project_uuid}
        )
        chain_state_rows = list(result)

        if not chain_state_rows:
            # 链化状态未初始化，尝试触发链化
            if self.should_trigger_chaining(conn, project_uuid):
                chain_result = self.trigger_chaining(conn, project_uuid, session_id)
                if chain_result.get("status") == "completed":
                    result = conn.execute(
                        GET_CHAIN_STATE_BY_PROJECT, {"project_uuid": project_uuid}
                    )
                    chain_state_rows = list(result)
                    if not chain_state_rows:
                        raise ValueError("链化状态获取失败")
                else:
                    return chain_result
            else:
                raise ValueError(
                    "项目未准备好链化。请确保至少有一个叶子节点已添加验证。"
                )

        chain_state = chain_state_rows[0]
        chain_status = chain_state[2]  # status

        # 检查链化是否完成
        if chain_status == ChainStatus.IDLE.value:
            # 链化未开始，尝试触发链化
            if self.should_trigger_chaining(conn, project_uuid):
                chain_result = self.trigger_chaining(conn, project_uuid, session_id)
                if chain_result.get("status") == "completed":
                    result = conn.execute(
                        GET_CHAIN_STATE_BY_PROJECT, {"project_uuid": project_uuid}
                    )
                    chain_state_rows = list(result)
                    chain_state = chain_state_rows[0]
                else:
                    return chain_result
            else:
                raise ValueError(
                    "项目未准备好链化。请确保至少有一个叶子节点已添加验证。"
                )

        if chain_state[2] != ChainStatus.COMPLETED.value:
            raise ValueError(f"链化未完成: {chain_state[2]}")

        # 获取当前节点
        current_node_uuid = chain_state[4]  # current_node_uuid

        if not current_node_uuid:
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
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": current_node_uuid})
        req_rows = list(result)
        if not req_rows:
            raise ValueError(f"当前需求不存在: {current_node_uuid}")

        current_req = req_rows[0]

        # 更新项目状态为 EXECUTING
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_uuid})
        project_rows = list(result)
        if project_rows and project_rows[0][3] == ProjectStatus.READY.value:
            conn.execute(
                UPDATE_PROJECT_STATUS,
                {
                    "uuid": project_uuid,
                    "status": ProjectStatus.EXECUTING.value,
                    "updated_at": now_utc(),
                },
            )

        # 计算进度
        total_nodes = chain_state[5]  # total_nodes
        completed_nodes = chain_state[6]  # completed_nodes
        progress = int((completed_nodes / total_nodes) * 100) if total_nodes > 0 else 0

        # 获取下一个节点（通过 NEXT_IN_CHAIN 边）
        next_result = conn.execute(GET_NEXT_IN_CHAIN, {"uuid": current_node_uuid})
        next_rows = list(next_result)
        is_last = len(next_rows) == 0

        # 计算 can_parallel：下一个需求的 parallel_group 与当前相同
        can_parallel = False
        current_parallel_group = current_req[9] if current_req[9] is not None else None
        if next_rows and current_parallel_group is not None:
            # 获取下一个需求的 parallel_group
            next_req_uuid = next_rows[0][0]
            next_req_result = conn.execute(
                GET_REQUIREMENT_BY_UUID, {"uuid": next_req_uuid}
            )
            next_req_rows = list(next_req_result)
            if next_req_rows:
                next_parallel_group = (
                    next_req_rows[0][9] if len(next_req_rows[0]) > 9 else None
                )
                can_parallel = next_parallel_group == current_parallel_group

        result_data = {
            "requirement_id": current_req[0],
            "content": current_req[3],
            "status": current_req[5],
            "chain_order": current_req[8],
            "parallel_group": current_parallel_group,
            "is_last": is_last,
            "can_parallel": can_parallel,
            "progress_percentage": progress,
            "message": None,
        }

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "NextRequirementRetrieved",
            project_uuid,
            {
                "requirement_id": current_node_uuid,
                "chain_order": current_req[8],
                "is_last": is_last,
            },
        )

        return result_data

    def mark_requirement_completed(
        self, conn: lb.Connection, project_uuid: str, requirement_uuid: str
    ) -> dict[str, Any]:
        """
        标记需求为已完成

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            requirement_uuid: 需求 ID

        Returns:
            操作结果
        """
        # 获取需求
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        req_rows = list(result)
        if not req_rows:
            raise ValueError(f"需求不存在: {requirement_uuid}")

        requirement = req_rows[0]
        req_project_uuid = requirement[1]  # project_uuid
        if req_project_uuid != project_uuid:
            raise ValueError(f"需求不属于该项目: {requirement_uuid}")

        # 获取链化状态
        result = conn.execute(
            GET_CHAIN_STATE_BY_PROJECT, {"project_uuid": project_uuid}
        )
        chain_state_rows = list(result)
        if not chain_state_rows:
            raise ValueError(f"项目未链化: {project_uuid}")

        chain_state = chain_state_rows[0]
        chain_state_uuid = chain_state[0]  # uuid
        total_nodes = chain_state[5]  # total_nodes
        completed_nodes = chain_state[6]  # completed_nodes

        # 幂等检查：需求已完成则直接返回
        current_status = requirement[5]  # status
        if current_status == RequirementStatus.COMPLETED.value:
            logger.info(f"需求已完成，跳过重复标记: {requirement_uuid}")
            return {
                "requirement_id": requirement_uuid,
                "next_requirement_id": None,
                "completed_nodes": completed_nodes,
                "total_nodes": total_nodes,
                "progress_percentage": int((completed_nodes / total_nodes) * 100)
                if total_nodes > 0
                else 100,
                "message": "需求已完成",
            }

        # 获取下一个需求 ID（通过 NEXT_IN_CHAIN 边）
        next_result = conn.execute(GET_NEXT_IN_CHAIN, {"uuid": requirement_uuid})
        next_rows = list(next_result)
        next_req_uuid = next_rows[0][0] if next_rows else None

        # 计算新的进度
        new_completed = completed_nodes + 1
        new_progress = (
            int((new_completed / total_nodes) * 100) if total_nodes > 0 else 100
        )

        # 更新链化状态
        conn.execute(
            UPDATE_CHAIN_STATE_PROGRESS,
            {
                "uuid": chain_state_uuid,
                "current_node_uuid": next_req_uuid or "",
                "progress_percentage": new_progress,
                "updated_at": now_utc(),
            },
        )

        # 更新需求状态为 COMPLETED
        conn.execute(
            UPDATE_REQUIREMENT_STATUS_COMPLETED,
            {
                "uuid": requirement_uuid,
                "status": RequirementStatus.COMPLETED.value,
                "updated_at": now_utc(),
            },
        )

        # 使需求缓存失效
        self.chain_builder._cache.invalidate_requirement(requirement_uuid)

        # 检查是否所有需求都已完成
        if next_req_uuid is None:
            # 所有需求完成
            conn.execute(
                UPDATE_PROJECT_STATUS,
                {
                    "uuid": project_uuid,
                    "status": ProjectStatus.COMPLETED.value,
                    "updated_at": now_utc(),
                },
            )

            # 记录事件
            log_event(
                conn,
                project_uuid,
                "ProjectCompleted",
                project_uuid,
                {
                    "total_nodes": total_nodes,
                    "completed_nodes": new_completed,
                },
            )

            message = "项目已完成"
        else:
            message = f"需求已完成，下一个需求: {next_req_uuid}"

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "RequirementCompleted",
            requirement_uuid,
            {
                "requirement_id": requirement_uuid,
                "next_requirement_id": next_req_uuid,
                "completed_nodes": new_completed,
                "total_nodes": total_nodes,
            },
        )

        logger.info(f"需求完成: {requirement_uuid}, 下一个: {next_req_uuid}")

        return {
            "requirement_id": requirement_uuid,
            "next_requirement_id": next_req_uuid,
            "completed_nodes": new_completed,
            "total_nodes": total_nodes,
            "progress_percentage": new_progress,
            "message": message,
        }

    # ============ 重试机制（使用 tenacity）============

    def mark_requirement_failed(
        self,
        conn: lb.Connection,
        project_uuid: str,
        requirement_uuid: str,
        reason: str,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """
        标记需求执行失败

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            requirement_uuid: 需求 ID
            reason: 失败原因
            retry_count: 重试次数

        Returns:
            操作结果
        """
        # 获取需求
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        req_rows = list(result)
        if not req_rows:
            raise ValueError(f"需求不存在: {requirement_uuid}")

        # 记录失败事件
        log_event(
            conn,
            project_uuid,
            "RequirementFailed",
            requirement_uuid,
            {
                "reason": reason,
                "retry_count": retry_count,
                "max_retries": Chain.MAX_RETRIES,
            },
        )

        logger.warning(
            f"需求执行失败: {requirement_uuid}, 原因: {reason}, 重试次数: {retry_count}/{Chain.MAX_RETRIES}"
        )

        return {
            "requirement_id": requirement_uuid,
            "status": "FAILED",
            "reason": reason,
            "retry_count": retry_count,
            "can_retry": retry_count < Chain.MAX_RETRIES,
        }
