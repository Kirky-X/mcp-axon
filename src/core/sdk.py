# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求链化 SDK - 核心类"""

import logging
import os
from typing import Any, Dict, List, Optional

import real_ladybug as lb

from src.core.containers import (
    get_container,
    get_connection,
    init_container,
    init_database,
)
from src.db.graph_queries import GET_REQUIREMENT_BY_UUID

logger = logging.getLogger(__name__)


class RequirementSDK:
    """需求链化 SDK - 主入口"""

    def __init__(self, db_path: str = None):
        """
        初始化 SDK

        Args:
            db_path: 数据库文件路径 (默认从环境变量 MCP_AXON_DB_PATH 获取)
        """
        # 优先使用环境变量，其次使用参数，最后使用默认值
        self.db_path = os.getenv("MCP_AXON_DB_PATH", db_path or "mcp_axon.lbug")

        try:
            # 初始化容器和数据库
            init_container(db_path=self.db_path)
            init_database()
        except Exception as e:
            logger.error(f"图数据库初始化失败: {e}")
            raise RuntimeError(f"无法初始化图数据库: {e}")

        try:
            # 从容器获取服务
            container = get_container()
            self._container = container

            self.project_manager = container.project_manager()
            self.requirement_manager = container.requirement_manager()
            self.dependency_service = container.dependency_service()
            self.validation_service = container.validation_service()
            self.chain_builder = container.chain_builder()
            self.chain_orchestrator = container.chain_orchestrator()
            self.lock_manager = container.lock_manager()
            self.snapshot_manager = container.snapshot_manager()

            logger.info(f"SDK 初始化完成: {self.db_path}")
        except Exception as e:
            logger.error(f"服务初始化失败: {e}")
            raise RuntimeError(f"无法初始化服务: {e}")

    def _get_conn(self) -> lb.Connection:
        """
        获取数据库连接（内部方法）

        Returns:
            数据库连接
        """
        return get_connection()

    def create_project(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        创建项目

        Args:
            name: 项目名称
            description: 项目描述

        Returns:
            项目信息
        """
        conn = self._get_conn()
        result = self.project_manager.create_project(conn, name, description)
        result["next_action"] = "add_root_requirement"
        return result

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新项目信息

        Args:
            project_id: 项目 ID
            name: 新名称
            description: 新描述

        Returns:
            更新后的项目信息
        """
        from src.schemas import ProjectUpdate

        conn = self._get_conn()
        update_data = ProjectUpdate(name=name, description=description)
        return self.project_manager.update_project(conn, project_id, update_data)

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目信息

        Args:
            project_id: 项目 ID

        Returns:
            项目信息
        """
        conn = self._get_conn()
        return self.project_manager.get_project(conn, project_id)

    def add_requirement(
        self,
        project_id: str,
        content: str,
        parent_id: Optional[str] = None,
        order_in_parent: int = 0,
    ) -> Dict[str, Any]:
        """
        添加需求节点

        Args:
            project_id: 项目 ID
            content: 需求内容
            parent_id: 父需求 ID（可选）
            order_in_parent: 在父需求中的顺序

        Returns:
            需求信息
        """
        conn = self._get_conn()
        result = self.requirement_manager.add_requirement(
            conn, project_id, content, parent_id, order_in_parent
        )

        # 添加下一步操作提示
        if result["needs_decomposition"]:
            result["next_action"] = "decompose_requirement"
        elif result["level"] == 0:
            result["next_action"] = "add_child_requirement"
        else:
            result["next_action"] = "add_validation"

        return result

    def update_requirement(
        self,
        requirement_id: str,
        content: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新需求

        Args:
            requirement_id: 需求 ID
            content: 新内容
            status: 新状态

        Returns:
            更新后的需求信息
        """
        from src.schemas import RequirementUpdate

        conn = self._get_conn()
        update_data = RequirementUpdate(content=content, status=status)
        return self.requirement_manager.update_requirement(
            conn, requirement_id, update_data
        )

    def delete_requirement(self, requirement_id: str) -> Dict[str, Any]:
        """
        删除需求

        Args:
            requirement_id: 需求 ID

        Returns:
            删除结果
        """
        conn = self._get_conn()
        return self.requirement_manager.delete_requirement(conn, requirement_id)

    def list_requirements(
        self,
        project_id: str,
        status: Optional[str] = None,
        is_leaf: Optional[bool] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        列出项目的所有需求

        Args:
            project_id: 项目 ID
            status: 按状态过滤（可选）
            is_leaf: 是否只返回叶子节点（可选）
            parent_id: 父需求 ID（可选）

        Returns:
            需求列表
        """
        conn = self._get_conn()
        return self.requirement_manager.list_requirements(
            conn, project_id, status, is_leaf, parent_id
        )

    def get_requirement(self, requirement_id: str) -> Dict[str, Any]:
        """
        获取单个需求

        Args:
            requirement_id: 需求 ID

        Returns:
            需求信息
        """
        conn = self._get_conn()
        return self.requirement_manager.get_requirement(conn, requirement_id)

    def add_validation(
        self,
        requirement_id: str,
        test_cases: List[Dict[str, Any]],
        acceptance_criteria: str = "",
    ) -> Dict[str, Any]:
        """
        添加验证节点

        Args:
            requirement_id: 需求 ID
            test_cases: 测试用例列表
            acceptance_criteria: 验收标准

        Returns:
            验证节点信息
        """
        conn = self._get_conn()
        result = self.validation_service.add_validation(
            conn, requirement_id, test_cases, acceptance_criteria
        )

        # 获取项目 ID 并检查是否应该触发链化
        req_result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_id})
        req_rows = list(req_result)
        if req_rows:
            project_id = req_rows[0][1]
            if self.chain_orchestrator.should_trigger_chaining(conn, project_id):
                result["next_action"] = "trigger_chaining"
            else:
                result["next_action"] = "continue_decomposition"

        return result

    def transfer_dependencies(
        self, parent_id: str, dependency_mapping: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        应用依赖传递映射

        Args:
            parent_id: 父需求 ID
            dependency_mapping: 依赖映射

        Returns:
            操作结果
        """
        conn = self._get_conn()
        return self.dependency_service.transfer_dependencies(
            conn, parent_id, dependency_mapping
        )

    def add_dependency(self, requirement_id: str, dependency_id: str) -> Dict[str, Any]:
        """
        添加依赖关系

        Args:
            requirement_id: 需求 ID
            dependency_id: 依赖的需求 ID

        Returns:
            操作结果
        """
        conn = self._get_conn()
        return self.dependency_service.add_dependency(
            conn, requirement_id, dependency_id
        )

    def resolve_parallel_order(
        self, project_id: str, parallel_nodes: List[str], sorted_order: List[str]
    ) -> Dict[str, Any]:
        """
        应用并行节点排序

        Args:
            project_id: 项目 ID
            parallel_nodes: 并行节点列表
            sorted_order: 排序后的节点列表

        Returns:
            链化结果
        """
        conn = self._get_conn()
        return self.chain_orchestrator.resolve_parallel_order(
            conn, project_id, parallel_nodes, sorted_order
        )

    def get_next_requirement(self, project_id: str, session_id: str) -> Dict[str, Any]:
        """
        获取下一个需求

        Args:
            project_id: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            下一个需求信息
        """
        conn = self._get_conn()
        return self.chain_orchestrator.get_next_requirement(
            conn, project_id, session_id
        )

    def mark_requirement_completed(
        self, project_id: str, requirement_id: str
    ) -> Dict[str, Any]:
        """
        标记需求为已完成

        Args:
            project_id: 项目 ID
            requirement_id: 需求 ID

        Returns:
            操作结果
        """
        conn = self._get_conn()
        return self.chain_orchestrator.mark_requirement_completed(
            conn, project_id, requirement_id
        )

    def get_project_state(self, project_id: str) -> Dict[str, Any]:
        """
        查询项目状态

        Args:
            project_id: 项目 ID

        Returns:
            项目状态信息
        """
        conn = self._get_conn()
        return self.project_manager.get_project_state(conn, project_id)

    def trigger_chaining(self, project_id: str, session_id: str) -> Dict[str, Any]:
        """
        触发链化

        Args:
            project_id: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            链化结果
        """
        conn = self._get_conn()
        return self.chain_orchestrator.trigger_chaining(conn, project_id, session_id)

    def create_snapshot(self, project_id: str, session_id: str) -> str:
        """
        创建快照

        Args:
            project_id: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            快照 ID
        """
        conn = self._get_conn()
        return self.snapshot_manager.create_snapshot(conn, project_id, session_id)

    def restore_snapshot(self, snapshot_id: str, session_id: str) -> Dict[str, Any]:
        """
        恢复快照

        Args:
            snapshot_id: 快照 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            恢复结果
        """
        conn = self._get_conn()
        return self.snapshot_manager.restore_snapshot(conn, snapshot_id, session_id)

    def list_snapshots(self, project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        列出快照

        Args:
            project_id: 项目 ID
            limit: 返回数量限制

        Returns:
            快照列表
        """
        conn = self._get_conn()
        return self.snapshot_manager.list_snapshots(conn, project_id, limit)

    def acquire_lock(self, project_id: str, session_id: str) -> bool:
        """
        获取项目锁

        Args:
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            是否获取成功
        """
        conn = self._get_conn()
        return self.lock_manager.acquire_lock(conn, project_id, session_id)

    def release_lock(self, project_id: str, session_id: str) -> bool:
        """
        释放项目锁

        Args:
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            是否释放成功
        """
        conn = self._get_conn()
        return self.lock_manager.release_lock(conn, project_id, session_id)

    def is_locked(self, project_id: str) -> bool:
        """
        检查项目是否被锁定

        Args:
            project_id: 项目 ID

        Returns:
            是否被锁定
        """
        conn = self._get_conn()
        return self.lock_manager.is_locked(conn, project_id)

    def get_lock_info(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取锁信息

        Args:
            project_id: 项目 ID

        Returns:
            锁信息
        """
        conn = self._get_conn()
        return self.lock_manager.get_lock_info(conn, project_id)

    def mark_as_leaf(self, requirement_id: str) -> Dict[str, Any]:
        """
        将需求标记为叶子节点

        Args:
            requirement_id: 需求 ID

        Returns:
            操作结果，包含 requirement_id、status、next_action
        """
        conn = self._get_conn()
        return self.requirement_manager.mark_as_leaf(conn, requirement_id)
