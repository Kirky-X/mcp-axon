# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""链化构建器服务"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from src.db.models import ChainState, ChainStatus, Requirement, RequirementStatus
from src.utils.cache import cache_manager
from src.utils.event_logger import log_event
from src.utils.graph import GraphAlgorithms
from src.utils.metrics import performance_monitor

logger = logging.getLogger(__name__)


class ChainBuilder:
    """链化构建器"""

    def __init__(self):
        """初始化链化构建器"""
        self.graph_algos = GraphAlgorithms()

    @performance_monitor("build_chain")
    def build_chain(self, session: Session, project_id: str) -> Dict[str, Any]:
        """
        构建需求链

        Args:
            session: 数据库会话
            project_id: 项目 ID

        Returns:
            链化结果
        """
        logger.info(f"开始构建链: {project_id}")

        # 检查缓存
        cached_result = cache_manager.get_chain_result(project_id)
        if cached_result:
            logger.info(f"使用缓存的链化结果: {project_id}")
            return cached_result

        # 获取所有已验证的需求
        requirements = (
            session.query(Requirement)
            .filter_by(project_id=project_id, status=RequirementStatus.VALIDATED.value)
            .all()
        )

        if not requirements:
            result = {
                "status": "no_requirements",
                "message": "没有已验证的需求需要链化",
            }
            cache_manager.set_chain_result(project_id, result)
            return result

        # 构建依赖图
        graph = self._build_dependency_graph(requirements)

        # 检测循环依赖
        cycle = self.graph_algos.detect_cycle_dfs(graph)
        if cycle:
            error_result = {
                "status": "error",
                "message": f"检测到循环依赖: {' -> '.join(cycle)}",
            }
            cache_manager.set_chain_result(project_id, error_result)
            cycle_str = " -> ".join(cycle)
            raise ValueError(
                f"检测到循环依赖: {cycle_str}。"
                f"循环依赖会导致需求无法按顺序执行。"
                f"请检查依赖关系，移除形成环路的依赖。"
            )

        # 拓扑排序
        layers = self.graph_algos.topological_sort(graph)

        # 检查是否有并行节点
        parallel_nodes = self.graph_algos.get_parallel_nodes(layers)

        if parallel_nodes:
            # 有并行节点，使用默认顺序（按创建时间或ID排序）
            logger.info(f"检测到 {len(parallel_nodes)} 组并行节点，使用默认顺序")

            # 展平分层结果
            sorted_ids = self.graph_algos.flatten_layers(layers)

            # 构建需求 ID 到需求的映射
            req_map = {req.id: req for req in requirements}

            # 使用默认顺序构建链表
            result = self._link_requirements(session, project_id, sorted_ids, req_map)
        else:
            # 没有并行节点，直接构建链表
            result = self._build_chain_from_sorted(
                session, project_id, layers, requirements
            )

        # 缓存结果
        cache_manager.set_chain_result(project_id, result)
        return result

    @performance_monitor("build_chain_with_order")
    def build_chain_with_order(
        self, session: Session, project_id: str, sorted_order: List[str]
    ) -> Dict[str, Any]:
        """
        使用指定的顺序构建链

        Args:
            session: 数据库会话
            project_id: 项目 ID
            sorted_order: 排序后的节点 ID 列表

        Returns:
            链化结果
        """
        logger.info(f"使用指定顺序构建链: {project_id}")

        # 清除旧的缓存结果
        cache_manager.invalidate_project(project_id)

        # 获取所有已验证的需求
        requirements = (
            session.query(Requirement)
            .filter_by(project_id=project_id, status=RequirementStatus.VALIDATED.value)
            .all()
        )

        # 构建需求 ID 到需求的映射
        req_map = {req.id: req for req in requirements}

        # 验证排序顺序
        req_ids = set(req.id for req in requirements)
        sorted_ids = set(sorted_order)

        if req_ids != sorted_ids:
            missing = req_ids - sorted_ids
            extra = sorted_ids - req_ids
            error_result = {
                "status": "error",
                "message": f"排序顺序不匹配。缺失: {missing}, 多余: {extra}",
            }
            cache_manager.set_chain_result(project_id, error_result)
            raise ValueError(f"排序顺序不匹配。缺失: {missing}, 多余: {extra}")

        # 按排序顺序构建链表
        result = self._link_requirements(session, project_id, sorted_order, req_map)

        # 缓存结果
        cache_manager.set_chain_result(project_id, result)
        return result

    def _build_dependency_graph(
        self, requirements: List[Requirement]
    ) -> Dict[str, List[str]]:
        """
        构建依赖图

        边方向：依赖 -> 节点（表示"节点依赖于依赖"）

        Args:
            requirements: 需求列表

        Returns:
            依赖图 {node_id: [dependent_node_ids]}
        """
        return self.graph_algos.build_dependency_graph(
            requirements,
            get_id_func=lambda req: req.id,
            get_deps_func=lambda req: req.dependencies,
        )

    def _build_chain_from_sorted(
        self,
        session: Session,
        project_id: str,
        layers: List[List[str]],
        requirements: List[Requirement],
    ) -> Dict[str, Any]:
        """
        从分层排序结果构建链

        Args:
            session: 数据库会话
            project_id: 项目 ID
            layers: 分层排序结果
            requirements: 需求列表

        Returns:
            链化结果
        """
        # 展平分层结果
        sorted_ids = self.graph_algos.flatten_layers(layers)

        # 构建需求 ID 到需求的映射
        req_map = {req.id: req for req in requirements}

        return self._link_requirements(session, project_id, sorted_ids, req_map)

    def _link_requirements(
        self,
        session: Session,
        project_id: str,
        sorted_ids: List[str],
        req_map: Dict[str, Requirement],
    ) -> Dict[str, Any]:
        """
        构建链表结构

        Args:
            session: 数据库会话
            project_id: 项目 ID
            sorted_ids: 排序后的需求 ID 列表
            req_map: 需求映射

        Returns:
            链化结果
        """
        if not sorted_ids:
            result = {"status": "completed", "chain_head": None, "total_nodes": 0}
            cache_manager.set_chain_result(project_id, result)
            return result

        # 获取或创建链化状态
        chain_state = session.query(ChainState).filter_by(project_id=project_id).first()

        if not chain_state:
            chain_state = ChainState(
                project_id=project_id, status=ChainStatus.BUILDING.value
            )
            session.add(chain_state)

        # 设置链表指针
        chain_head_id = sorted_ids[0]
        prev_req_id = None

        for i, req_id in enumerate(sorted_ids):
            req = req_map.get(req_id)
            if not req:
                logger.warning(f"需求不存在: {req_id}")
                continue

            # 设置链表顺序
            req.chain_order = i + 1
            req.status = RequirementStatus.CHAINED.value

            # 设置前驱节点的 next 指针
            if prev_req_id:
                prev_req = req_map.get(prev_req_id)
                if prev_req:
                    prev_req.next_requirement_id = req_id

            prev_req_id = req_id

        # 更新链化状态
        chain_state.status = ChainStatus.COMPLETED.value
        chain_state.chain_head_id = chain_head_id
        chain_state.current_node_id = chain_head_id
        chain_state.total_nodes = len(sorted_ids)
        chain_state.completed_nodes = 0
        chain_state.progress_percentage = 0

        chain_state.last_chained_at = datetime.now(timezone.utc)

        # 记录事件
        log_event(
            session,
            project_id,
            "ChainBuilt",
            project_id,
            {
                "chain_head_id": chain_head_id,
                "total_nodes": len(sorted_ids),
                "chain_order": sorted_ids,
            },
        )

        session.commit()

        result = {
            "status": "completed",
            "chain_head": chain_head_id,
            "total_nodes": len(sorted_ids),
            "message": "链化构建完成",
        }

        # 缓存结果
        cache_manager.set_chain_result(project_id, result)

        logger.info(
            f"链构建完成: {project_id}, 头节点: {chain_head_id}, 节点数: {len(sorted_ids)}"
        )

        return result

    @performance_monitor("reset_chain")
    def reset_chain(self, session: Session, project_id: str) -> Dict[str, Any]:
        """
        重置链化状态

        Args:
            session: 数据库会话
            project_id: 项目 ID

        Returns:
            重置结果
        """
        # 获取所有已链化的需求
        requirements = (
            session.query(Requirement)
            .filter_by(project_id=project_id, status=RequirementStatus.CHAINED.value)
            .all()
        )

        # 重置需求状态
        for req in requirements:
            req.status = RequirementStatus.VALIDATED.value
            req.chain_order = None
            req.next_requirement_id = None

        # 重置链化状态
        chain_state = session.query(ChainState).filter_by(project_id=project_id).first()

        if chain_state:
            chain_state.status = ChainStatus.IDLE.value
            chain_state.chain_head_id = None
            chain_state.current_node_id = None
            chain_state.total_nodes = 0
            chain_state.completed_nodes = 0
            chain_state.progress_percentage = 0

        # 记录事件
        log_event(
            session,
            project_id,
            "ChainReset",
            project_id,
            {"reset_count": len(requirements)},
        )

        session.commit()

        # 使缓存失效
        cache_manager.invalidate_project(project_id)

        logger.info(f"链化状态重置: {project_id}")

        return {
            "status": "reset",
            "reset_count": len(requirements),
            "message": "链化状态已重置",
        }
