# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求链化 SDK - 核心类"""

import logging
from typing import Any, Dict, List, Optional

from src.db.database import get_session
from src.db.models import Requirement
from src.services.chain_builder import ChainBuilder
from src.services.chain_orchestrator import ChainOrchestrator
from src.services.dependency_service import DependencyService
from src.services.project_manager import ProjectManager
from src.services.requirement_manager import RequirementManager
from src.services.validation_service import ValidationService
from src.utils.lock_manager import ProjectLockManager
from src.utils.snapshot_manager import SnapshotManager

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
        import os
        self.db_path = os.getenv("MCP_AXON_DB_PATH", db_path or "requirements.db")

        try:
            # 初始化数据库
            from src.db.database import init_sync_db

            init_sync_db(db_path, echo=False)
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise RuntimeError(f"无法初始化数据库: {e}")

        try:
            # 初始化服务
            self.project_manager = ProjectManager()
            self.requirement_manager = RequirementManager()
            self.dependency_service = DependencyService()
            self.validation_service = ValidationService()
            self.chain_builder = ChainBuilder()
            self.chain_orchestrator = ChainOrchestrator()
            self.lock_manager = ProjectLockManager()
            self.snapshot_manager = SnapshotManager()

            logger.info(f"SDK 初始化完成: {db_path}")
        except Exception as e:
            logger.error(f"服务初始化失败: {e}")
            raise RuntimeError(f"无法初始化服务: {e}")

    def _get_session(self):
        """
        获取数据库会话（内部方法，供测试使用）

        Returns:
            数据库会话上下文管理器
        """
        return get_session()

    def create_project(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        创建项目

        Args:
            name: 项目名称
            description: 项目描述

        Returns:
            项目信息
        """
        with get_session() as session:
            result = self.project_manager.create_project(session, name, description)

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

        with get_session() as session:
            update_data = ProjectUpdate(name=name, description=description)

            return self.project_manager.update_project(session, project_id, update_data)

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目信息

        Args:
            project_id: 项目 ID

        Returns:
            项目信息
        """
        with get_session() as session:
            return self.project_manager.get_project(session, project_id)

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
        with get_session() as session:
            result = self.requirement_manager.add_requirement(
                session, project_id, content, parent_id, order_in_parent
            )

            # 添加下一步操作提示
            if result["needs_decomposition"]:
                result["next_action"] = "decompose_requirement"
            elif result["level"] == 0:
                result["next_action"] = "add_child_requirement"
            else:
                result["next_action"] = "mark_as_leaf"

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

        with get_session() as session:
            update_data = RequirementUpdate(content=content, status=status)

            return self.requirement_manager.update_requirement(
                session, requirement_id, update_data
            )

    def mark_as_leaf(self, requirement_id: str) -> Dict[str, Any]:
        """
        标记需求为叶子节点

        Args:
            requirement_id: 需求 ID

        Returns:
            需求信息
        """
        with get_session() as session:
            result = self.requirement_manager.mark_as_leaf(session, requirement_id)
            result["next_action"] = "add_validation"
            return result

    def delete_requirement(self, requirement_id: str) -> Dict[str, Any]:
        """
        删除需求

        Args:
            requirement_id: 需求 ID

        Returns:
            删除结果
        """
        with get_session() as session:
            return self.requirement_manager.delete_requirement(session, requirement_id)

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
        with get_session() as session:
            result = self.validation_service.add_validation(
                session, requirement_id, test_cases, acceptance_criteria
            )

            # 检查是否应该触发链化
            req = session.query(Requirement).filter_by(id=requirement_id).first()

            if req and self.chain_orchestrator.should_trigger_chaining(
                session, req.project_id
            ):
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
        with get_session() as session:
            return self.dependency_service.transfer_dependencies(
                session, parent_id, dependency_mapping
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
        with get_session() as session:
            return self.dependency_service.add_dependency(
                session, requirement_id, dependency_id
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
        with get_session() as session:
            return self.chain_orchestrator.resolve_parallel_order(
                session, project_id, parallel_nodes, sorted_order
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
        with get_session() as session:
            return self.chain_orchestrator.get_next_requirement(
                session, project_id, session_id
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
        with get_session() as session:
            return self.chain_orchestrator.mark_requirement_completed(
                session, project_id, requirement_id
            )

    def get_project_state(self, project_id: str) -> Dict[str, Any]:
        """
        查询项目状态

        Args:
            project_id: 项目 ID

        Returns:
            项目状态信息
        """
        with get_session() as session:
            return self.project_manager.get_project_state(session, project_id)

    def trigger_chaining(self, project_id: str, session_id: str) -> Dict[str, Any]:
        """
        触发链化

        Args:
            project_id: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            链化结果
        """
        with get_session() as session:
            return self.chain_orchestrator.trigger_chaining(
                session, project_id, session_id
            )

    def create_snapshot(self, project_id: str, session_id: str) -> str:
        """
        创建快照

        Args:
            project_id: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            快照 ID
        """
        with get_session() as session:
            return self.snapshot_manager.create_snapshot(
                session, project_id, session_id
            )

    def restore_snapshot(self, snapshot_id: str, session_id: str) -> Dict[str, Any]:
        """
        恢复快照

        Args:
            snapshot_id: 快照 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            恢复结果
        """
        with get_session() as session:
            return self.snapshot_manager.restore_snapshot(
                session, snapshot_id, session_id
            )

    def list_snapshots(self, project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        列出快照

        Args:
            project_id: 项目 ID
            limit: 返回数量限制

        Returns:
            快照列表
        """
        with get_session() as session:
            return self.snapshot_manager.list_snapshots(session, project_id, limit)

    def acquire_lock(self, project_id: str, session_id: str) -> bool:
        """
        获取项目锁

        Args:
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            是否获取成功
        """
        with get_session() as session:
            return self.lock_manager.acquire_lock(session, project_id, session_id)

    def release_lock(self, project_id: str, session_id: str) -> bool:
        """
        释放项目锁

        Args:
            project_id: 项目 ID
            session_id: 会话 ID

        Returns:
            是否释放成功
        """
        with get_session() as session:
            return self.lock_manager.release_lock(session, project_id, session_id)

    def is_locked(self, project_id: str) -> bool:
        """
        检查项目是否被锁定

        Args:
            project_id: 项目 ID

        Returns:
            是否被锁定
        """
        with get_session() as session:
            return self.lock_manager.is_locked(session, project_id)

    def get_lock_info(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取锁信息

        Args:
            project_id: 项目 ID

        Returns:
            锁信息
        """
        with get_session() as session:
            return self.lock_manager.get_lock_info(session, project_id)
